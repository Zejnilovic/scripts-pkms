# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/lines.sh: the line scanner. One awk pass over the vault yields every line that carries a marker, every entry
# whose time is a range, and every task, as a record that tasks, upcoming, close and check filter. A line in code or frontmatter, a struck line, a heading,
# and a box in a note of type: list are never records. Sourced by bin/pkm. Defines functions only.

# awk_markers: the awk functions that read a record's markers (field 5: the text inside each pair of parentheses whose
# first word is a marker key, in the order written, separated by tabs). mval(m, key) is the value of the first
# "(key …)" ("" when there is none), mhas(m, key) is 1 when one is written with a value or a space, and mflag(m, key) is 1
# when "(key)" is written alone. line_markers(s) is the markers field of a line's text: (at …) and (@ …) count only with a
# value after them (at_value), and (@ …) is recorded as (at …); (for …) only with a link or a writer's name (for_value);
# a duration, (1h30), (1h) or (40m), is recorded as written (duration_value). spent(kind, m, t) is the time a record
# says was spent, in minutes: its first duration, else the range its text starts with (range_minutes), and 0 for an event.
awk_markers() {
  cat <<'AWK'
function mval(m, key,   n, a, i) {
  n = split(m, a, "\t")
  for (i = 1; i <= n; i++) if (substr(a[i], 1, length(key) + 1) == key " ") return substr(a[i], length(key) + 2)
  return ""
}
function mhas(m, key,   n, a, i) {
  n = split(m, a, "\t")
  for (i = 1; i <= n; i++) if (substr(a[i], 1, length(key) + 1) == key " ") return 1
  return 0
}
function mflag(m, key,   n, a, i) {
  n = split(m, a, "\t")
  for (i = 1; i <= n; i++) if (a[i] == key) return 1
  return 0
}
function line_markers(s,   out, i, rest, j, c, key, sp) {
  out = ""; rest = s
  while ((i = index(rest, "(")) > 0) {
    rest = substr(rest, i + 1); j = index(rest, ")"); if (j == 0) break
    c = substr(rest, 1, j - 1); sp = index(c, " ")
    key = sp ? substr(c, 1, sp - 1) : c
    if (key == "@") { c = "at" substr(c, 2); key = "at" }
    if (key == "at" && !at_value(substr(c, 4))) continue
    if (key == "for" && !for_value(substr(c, 5))) continue
    if (key ~ /^(due|start|waiting|someday|high|low|done|dropped|recall|at|every|until|skip|for)$/ || \
        (key == c && duration_value(c) != "")) out = out (out == "" ? "" : "\t") c
  }
  return out
}
# duration_value(c): the minutes of a duration, <h>h, <h>h<mm> (mm two digits, below 60) or <m>m, or "" for anything else.
function duration_value(c) {
  if (c ~ /^[0-9]+m$/) return substr(c, 1, length(c) - 1) + 0
  if (c ~ /^[0-9]+h$/) return substr(c, 1, length(c) - 1) * 60
  if (c ~ /^[0-9]+h[0-5][0-9]$/) return substr(c, 1, index(c, "h") - 1) * 60 + substr(c, index(c, "h") + 1)
  return ""
}
# range_minutes(t): the minutes of the range a line's text starts with, after its list mark and box, as in
# "- 09:00-11:30 Workshop" (the dash may be an en dash); a range that ends before it starts ends the next day. 0 when
# the line starts with none, or its start and end are the same.
function range_minutes(t,   b, s, r, dash, e, d) {
  b = t; sub(/^[-*+] (\[.\] )?/, "", b)
  if (b !~ /^([01][0-9]|2[0-3]):[0-5][0-9]/) return 0
  s = substr(b, 1, 5); r = substr(b, 6); dash = "\342\200\223"
  if (substr(r, 1, 1) == "-") r = substr(r, 2)
  else if (index(r, dash) == 1) r = substr(r, length(dash) + 1)
  else return 0
  e = substr(r, 1, 5)
  if (e !~ /^([01][0-9]|2[0-3]):[0-5][0-9]$/ || (length(r) > 5 && substr(r, 6, 1) != " ")) return 0
  d = (substr(e, 1, 2) * 60 + substr(e, 4, 2)) - (substr(s, 1, 2) * 60 + substr(s, 4, 2))
  if (d < 0) d += 1440
  return d
}
function spent(kind, m, t,   n, a, i, v) {
  if (kind == "event") return 0
  n = split(m, a, "\t")
  for (i = 1; i <= n; i++) if ((v = duration_value(a[i])) != "") return v
  return range_minutes(t)
}
# for_value(v): 1 for a link, or the name of a writer of the vault's day pages (PKM_WRITERS, set by vault_writers).
function for_value(v,   w) {
  sub(/[ \t]+$/, "", v)
  if (v ~ /^\[\[[^]]+\]\]$/) return 1
  w = tolower(v)
  return w ~ /^[a-z0-9-]+$/ && index(" " ENVIRON["PKM_WRITERS"] " ", " " w " ") > 0
}
function at_value(v,   w) {
  w = tolower(v); sub(/ .*/, "", w)
  return w ~ /^[0-9][0-9][0-9][0-9]-/ || w ~ /^\+/ || w == "today" || w == "tomorrow" || \
    w ~ /^(mon|monday|tue|tues|tuesday|wed|wednesday|thu|thur|thurs|thursday|fri|friday|sat|saturday|sun|sunday)$/
}
AWK
}

# awk_lines: the scanner, for scan. Each record has fields separated by the unit separator (OFS):
# 1 path, 2 line, 3 kind (task, question, event or entry), 4 state of a box (open, done, dropped, or empty without one),
# 5 markers (see awk_markers; a 📅 date is added as "due <date>" when the line has no (due …)), 6 the day page's date (or
# empty), 7 the writer of a shared vault's day page (2026-11-14-alex.md: alex), 8 the note's type and 9 its status (from
# its frontmatter, or empty), 10 the text: the line without its indent, tabs as spaces.
# A line with (recall …) is a question, box or not (check reports the box). Another box line is a task. Without a box,
# a line with (at …) or (@ …) followed by a value (a date, a weekday, today, tomorrow or +…) is an event, and any other
# line with a marker, or whose time is a range (time spent: - 09:00-11:30 …), is an entry. The keys are those of
# docs/format.md 7.5.
awk_lines() {
  cat <<'AWK'
  function emoji_date(s,   i, m, rest, v) {
    # Measured, not counted: gawk in a UTF-8 locale counts the emoji as one character, mawk as four bytes.
    m = "\360\237\223\205 "; i = index(s, m); if (i == 0) return ""
    rest = substr(s, i + length(m)); v = match(rest, /[ )]/)
    return v ? substr(rest, 1, v - 1) : rest
  }
  function front_value(s) { sub(/^[a-z_]+:[ \t]*/, "", s); sub(/[ \t]+$/, "", s); gsub(/^["']|["']$/, "", s); return s }
  FNR == 1 {
    file = rel(FILENAME); fence = 0; b = base(file)
    day = (b ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/) ? substr(b, 1, 10) : ""
    writer = (day != "" && b ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-.+\.md$/) ? substr(b, 12, length(b) - 14) : ""
    ntype = ""; nstatus = ""; front = ($0 == "---")
  }
  front && FNR > 1 {
    if ($0 == "---") { front = 0; if (ntype == "close") writer = "" }
    else if ($0 ~ /^type:/) ntype = front_value($0)
    else if ($0 ~ /^status:/) nstatus = front_value($0)
    next
  }
  front { next }
  /^[ \t]*(```|~~~)/ { fence = !fence; next }
  fence || /^[ \t]*#/ { next }
  {
    t = $0; sub(/^[ \t]+/, "", t); gsub(/\t/, " ", t)
    state = ""; body = t
    if ($0 ~ /^[ \t]*- \[.\] /) {
      c = substr(t, 4, 1)
      if (c == " ") state = "open"
      else if (c == "x" || c == "X") state = "done"
      else if (c == "-") state = "dropped"
      if (state != "" && ntype == "list") next
      if (state != "") body = substr(t, 7)
    } else if (t ~ /^[-*+] /) body = substr(t, 3)
    if (substr(body, 1, 2) == "~~") next
    ranged = (state == "" && t ~ /^[-*+] [0-2][0-9]:[0-5][0-9]/ && range_minutes(t) > 0)
    if (state == "" && index(t, "(") == 0 && !ranged) next
    m = line_markers(t)
    if (state == "" && m == "" && !ranged) next
    if (mval(m, "due") == "") { e = emoji_date(t); if (e != "") m = m (m == "" ? "" : "\t") "due " e }
    if (mhas(m, "recall")) kind = "question"
    else if (state != "") kind = "task"
    else kind = mhas(m, "at") ? "event" : "entry"
    print file, FNR, kind, state, m, day, writer, ntype, nstatus, t
  }
AWK
}

# line_records <yes|no: include archive/>: the scanner's records for every note (see awk_lines). The first call in a run
# scans the vault; later calls read the same records again, so a command that changes notes and then reads them again
# calls line_records_forget in between.
line_records() {
  local out="$tmp/lines-$1"
  vault_writers
  if [ ! -f "$out" ]; then
    files "$1" '*.md' > "$tmp/lines-files-$1"
    scan "$tmp/lines-files-$1" "$(awk_markers)$(awk_lines)" -v OFS='\037' > "$out"
  fi
  cat "$out"
}

# line_records_forget: the next line_records call scans the vault again.
line_records_forget() {
  rm -f "$tmp"/lines-yes "$tmp"/lines-no
}

# vault_writers: exports PKM_WRITERS, the writers of a shared vault's day pages (daybook/…/2026-11-14-alex.md: alex),
# separated by spaces, for for_value. A command that reads (for …) calls it first; it lists the files once.
vault_writers() {
  [ "$writers_listed" = yes ] && return 0
  writers_listed=yes
  PKM_WRITERS=$(files no '*.md' | sed -n 's|^daybook/\(.*/\)\{0,1\}[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-\([a-z0-9-]*\)\.md$|\2|p' \
    | LC_ALL=C sort -u | tr '\n' ' ')
  export PKM_WRITERS
}
