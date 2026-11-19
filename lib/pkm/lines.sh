# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/lines.sh: the line scanner. One awk pass over the vault yields every line that carries a marker, and every
# task, as a record that tasks, upcoming, close and check filter. A line in code or frontmatter, a struck line, a heading,
# and a box in a note of type: list are never records. Sourced by bin/pkm. Defines functions only.

# awk_markers: the awk functions that read a record's markers (field 5: the text inside each pair of parentheses whose
# first word is a marker key, in the order written, separated by tabs). mval(m, key) is the value of the first
# "(key …)" ("" when there is none), mhas(m, key) is 1 when one is written with a value or a space, and mflag(m, key) is 1
# when "(key)" is written alone.
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
AWK
}

# awk_lines: the scanner, for scan. Each record has fields separated by the unit separator (OFS):
# 1 path, 2 line, 3 kind (task, question, event or entry), 4 state of a box (open, done, dropped, or empty without one),
# 5 markers (see awk_markers; a 📅 date is added as "due <date>" when the line has no (due …)), 6 the day page's date (or
# empty), 7 the writer of a shared vault's day page (2026-11-14-alex.md: alex), 8 the note's type and 9 its status (from
# its frontmatter, or empty), 10 the text: the line without its indent, tabs as spaces.
# A line with (recall …) is a question, box or not (check reports the box). Another box line is a task. Without a box, a line with (at …) or (@ …) followed by a
# value (a date, a weekday, today, tomorrow or +…) is an event, and any other line with a marker is an entry. The keys are
# those of docs/format.md 7.5; (at …) and (@ …) without a value are text, and (@ …) is recorded as (at …).
awk_lines() {
  cat <<'AWK'
  function line_markers(s,   out, i, rest, j, c, key, sp) {
    out = ""; rest = s
    while ((i = index(rest, "(")) > 0) {
      rest = substr(rest, i + 1); j = index(rest, ")"); if (j == 0) break
      c = substr(rest, 1, j - 1); sp = index(c, " ")
      key = sp ? substr(c, 1, sp - 1) : c
      if (key == "@") { c = "at" substr(c, 2); key = "at" }
      if (key == "at" && !at_value(substr(c, 4))) continue
      if (key ~ /^(due|start|waiting|someday|high|low|done|dropped|recall|at|every|until|skip)$/) out = out (out == "" ? "" : "\t") c
    }
    return out
  }
  function at_value(v,   w) {
    w = tolower(v); sub(/ .*/, "", w)
    return w ~ /^[0-9][0-9][0-9][0-9]-/ || w ~ /^\+/ || w == "today" || w == "tomorrow" || \
      w ~ /^(mon|monday|tue|tues|tuesday|wed|wednesday|thu|thur|thurs|thursday|fri|friday|sat|saturday|sun|sunday)$/
  }
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
    if (state == "" && index(t, "(") == 0) next
    m = line_markers(t)
    if (state == "" && m == "") next
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
