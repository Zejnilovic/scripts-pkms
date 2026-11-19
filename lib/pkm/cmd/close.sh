# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/close.sh: pkm close [--cycle name] [--date D] [--quarter] [--json]: the close of a period, by default the close
# cycle's period holding yesterday. The first line names the period, its entry count and its close page. Then only the
# sections with lines: == tasks (overdue, and open for 21 days or more), == open (questions, and every waiting task),
# == for (the open tasks and the period's questions with a (for …), by person, which the two before leave out),
# == due (from today to the end of the next period, as upcoming prints them), == marked (the period's ! Decided: Idea:
# entries), == names (names linked on three lines or more of day pages, with no note), == quiet (projects and people linked
# 15 to 42 days ago and not in the last 14 days) and == ideas (every Idea: entry and someday task, in a period that holds the
# first day of a quarter, or with --quarter). Exit 0. Sourced by bin/pkm.

# close_period <cycle> <date>: sets PFIRST and PLAST (the period holding the date) and PNEXT (the last day of the next one).
close_period() {
  local line
  line=$(cycle_period "$1" "$2") || die 1 "No cycle named $1: add cycle_$1 to .pkm/config, or see pkm config."
  PFIRST=${line%% *}
  PLAST=${line#* }
  PNEXT=$(cycle_period_last "$1" "$(day_add "$PLAST" 1)")
}

# The records are US-separated with 13 fields: section, sort 1, sort 2, sort 3, path, line, text, state, days, name, count,
# last, label. rec_awk is their awk function, shared by the programs below.
rec_awk() {
  cat <<'AWK'
function rec(sec, a, b, c, path, line, text, state, days, name, count, last, label) {
  print sec US a US b US c US path US line US text US state US days US name US count US last US label
}
function pad(n) { return sprintf("%06d", n) }
AWK
}

# close_sections <first> <last> <next last> <quarter yes|no>: writes $tmp/close-records (every section, sorted by section),
# and sets PENTRIES, the number of log lines of the period.
close_sections() {
  local US first=$1 last=$2 next=$3 quarter=$4 w1s w1e w2s
  US=$(printf '\037')
  index_ensure
  link_build ""
  digest_pages "$first" "$last"
  task_records no > "$tmp/close-tasks"
  # Whose move it is: the open tasks and the period's questions with a (for …) go to == for, by person, and only there.
  for_records | awk -F "$US" -v first="$first" -v last="$last" \
    '$7 == 1 && ($3 == "task" || ($3 == "question" && $8 >= first && $8 <= last))' > "$tmp/close-for"
  awk -F "$US" '{ print $1 ":" $2 }' "$tmp/close-for" > "$tmp/close-for-lines"
  upcoming_lines "$(day_diff "$today" "$next")" | awk '$2 != "overdue"' > "$tmp/close-due"
  w1s=$(day_add "$today" -41); w1e=$(day_add "$today" -14); w2s=$(day_add "$today" -13)
  PENTRIES=$(awk -F "$US" '$4 == "l"' "$tmp/dg-pages" | wc -l | tr -d ' ')
  : > "$tmp/close-records"

  # The period's questions, and its ! Decided: Idea: entries.
  # shellcheck disable=SC2016,SC2129 # awk program: the $ in it is awk's; each section below is its own program
  awk -F "$US" -v US="$US" "$(awk_dates)$(awk_markers)$(awk_plain)$(rec_awk)"'
    FILENAME == ARGV[1] { theirs[$0] = 1; next }
    function marked(t,  s) {
      if (t !~ /^[ \t]*- /) return 0
      s = t; sub(/^[ \t]*- /, "", s)
      if (s ~ /^~~/) return 0
      sub(/^[0-9][0-9]:[0-9][0-9] /, "", s)
      return (s ~ /^! / || s ~ /^Decided:/ || s ~ /^Idea:/)
    }
    $4 == "l" {
      # A question ends with "?" before its markers; one that is someone'"'"'s is in == for.
      q = plain_unmark($5)
      if (q ~ /\?[ \t]*$/ && !(($1 ":" $3) in theirs)) rec("2open", $1, pad($3), "", $1, $3, $5, "", "", "", "", "", "question")
      if (marked($5)) rec("4marked", $1, pad($3), "", $1, $3, $5, "", "", "", "", "", "")
    }
  ' "$tmp/close-for-lines" "$tmp/dg-pages" >> "$tmp/close-records"

  # Overdue tasks, tasks open 21 days or more on their day page, and waiting tasks. Someday tasks go to ideas.
  awk -F "$US" -v US="$US" -v today="$today" "$(awk_dates)$(rec_awk)"'
    FILENAME == ARGV[1] { theirs[$0] = 1; next }
    $3 != "open" || (($1 ":" $2) in theirs) { next }
    $12 != "" && $12 > today { next }                    # hidden until its start date
    $6 == 1 && !($12 != "" && $12 <= today) { next }     # someday: only in ideas
    $4 != "" && $4 < today { rec("1tasks", $1, pad($2), "", $1, $2, $13, "open", ymd(today) - ymd($4), "", "", "", "overdue"); next }
    # Open 21 days or more on its day page; a task with a start date counts from that date instead.
    $10 != "" && (base = ($12 != "" ? $12 : $10)) != "" && ymd(today) - ymd(base) >= 21 {
      d = ymd(today) - ymd(base)
      rec("1tasks", $1, pad($2), "", $1, $2, $13, "open", d, "", "", "", "open " d " days")
    }
    $5 == "?" { rec("2open", $1, pad($2), "", $1, $2, $13, "open", "", "", "", "", "waiting") }
    $5 != "" && $5 != "?" && $5 <= today {
      d = ymd(today) - ymd($5)
      rec("2open", $1, pad($2), "", $1, $2, $13, "open", d, "", "", "", "waiting " d " days")
    }
  ' "$tmp/close-for-lines" "$tmp/close-tasks" >> "$tmp/close-records"

  # For: by person, then path and line. A task shows what it waits on: overdue, waiting, or its due date.
  awk -F "$US" -v US="$US" -v today="$today" "$(awk_dates)$(rec_awk)"'
    FILENAME == ARGV[1] { who[$1 ":" $2] = $6; kind[$1 ":" $2] = $3; if ($3 == "question") q[$1 ":" $2] = $0; next }
    FILENAME == ARGV[2] {
      k = $1 ":" $2
      if (!(k in who) || $3 != "open") next
      if ($12 != "" && $12 > today) next                   # hidden until its start date
      if ($6 == 1 && !($12 != "" && $12 <= today)) next    # someday: only in ideas
      l = "for " who[k]
      if ($4 != "" && $4 < today) { l = l ", overdue"; d = ymd(today) - ymd($4) }
      else if ($5 == "?") { l = l ", waiting"; d = "" }
      else if ($5 != "" && $5 <= today) { d = ymd(today) - ymd($5); l = l ", waiting " d " days" }
      else if ($4 != "") { l = l ", due " $4; d = "" }
      else d = ""
      rec("2pfor", tolower(who[k]), $1, pad($2), $1, $2, $13, "open", d, who[k], "", "", l)
      next
    }
    END {
      for (k in q) { split(q[k], f, US); rec("2pfor", tolower(f[6]), f[1], pad(f[2]), f[1], f[2], f[9], "", "", f[6], "", "", "for " f[6] ", question") }
    }
  ' "$tmp/close-for" "$tmp/close-tasks" >> "$tmp/close-records"
  awk -F "$US" -v US="$US" "$(awk_dates)$(rec_awk)"'
    $3 != "open" || $6 != 1 || ($12 != "" && $12 <= today) { next }
    { rec("7ideas", $1, pad($2), "", $1, $2, $13, "open", "", "", "", "", "someday") }
  ' "$tmp/close-tasks" > "$tmp/close-someday"

  # Due: the lines upcoming prints from today to the end of the next period.
  awk -v US="$US" "$(awk_dates)$(rec_awk)"'
    { rec("3due", substr($0, 1, 10), $0, "", "", "", $0, "", "", "", "", "", "") }
  ' "$tmp/close-due" >> "$tmp/close-records"

  # Names with no note: a link to no note on three lines or more of day pages.
  awk -F '\t' -v types="$(cache_dir)/names.tsv" '
    BEGIN { while ((getline l < types) > 0) { split(l, g, "\t"); isday[g[3]] = (g[2] == "day") } close(types) }
    isday[$1] && $6 == "" && !(($3 SUBSEP $1 SUBSEP $2) in seen) { seen[$3 SUBSEP $1 SUBSEP $2] = 1; cnt[$3]++ }
    END { for (t in cnt) if (cnt[t] >= 3) print t "\t" cnt[t] }
  ' "$tmp/lb-links" > "$tmp/close-dead"
  if [ -s "$tmp/close-dead" ]; then
    cut -f 1 "$tmp/close-dead" | LC_ALL=C sort -u > "$tmp/close-dead-targets"
    link_slugs "$tmp/close-dead-targets" "$tmp/close-dead-slugs"
    awk -F '\t' -v US="$US" "$(rec_awk)"'
      FILENAME == ARGV[1] { slug[$1] = $2; next }
      { rec("5names", pad(999999 - $2), slug[$1], "", "", "", "", "", "", slug[$1], $2, "", "no note") }
    ' "$tmp/close-dead-slugs" "$tmp/close-dead" >> "$tmp/close-records"
  fi

  # Quiet: projects that are not done, and people, linked from a day page 15 to 42 days ago and not in the last 14 days.
  awk -F '\t' -v today="$today" -v w1s="$w1s" -v w1e="$w1e" -v w2s="$w2s" \
    -v names="$(cache_dir)/names.tsv" -v notes="$(cache_dir)/notes.tsv" '
    BEGIN {
      while ((getline l < names) > 0) { split(l, g, "\t"); if (g[2] == "day") date[g[3]] = substr(g[1], 1, 10) }
      close(names)
      while ((getline l < notes) > 0) { split(l, h, "\t"); ty[h[1]] = h[3]; st[h[1]] = h[4] }
      close(notes)
    }
    $6 != "" && ($1 in date) {
      d = date[$1]
      if (d >= w1s && d <= w1e && d > last[$6]) last[$6] = d
      if (d >= w2s && d <= today) recent[$6] = 1
    }
    END {
      for (p in last) {
        if (recent[p] || p ~ /^archive\//) continue
        if (ty[p] == "person" || (ty[p] == "project" && st[p] != "done")) print p "\t" last[p]
      }
    }
  ' "$tmp/lb-links" | LC_ALL=C sort > "$tmp/close-quiet"
  if [ -s "$tmp/close-quiet" ]; then
    cut -f 1 "$tmp/close-quiet" > "$tmp/close-quiet-paths"
    # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
    scan "$tmp/close-quiet-paths" '
      FNR == 1 { file = rel(FILENAME); done = 0 }
      !done && /^# / { print file "\t" FNR "\t" $0; done = 1 }
    ' > "$tmp/close-quiet-titles"
    awk -F '\t' -v US="$US" "$(rec_awk)"'
      FILENAME == ARGV[1] { last[$1] = $2; next }
      { rec("6quiet", $1, "", "", $1, $2, $3, "", "", "", "", last[$1], "last linked " last[$1]) }
    ' "$tmp/close-quiet" "$tmp/close-quiet-titles" >> "$tmp/close-records"
  fi

  # Ideas: every Idea: entry on any day page, and the someday tasks, in a period holding a quarter's first day, or with --quarter.
  if [ "$quarter" = yes ] || [ "$(quarter_start "$first" "$last")" = yes ]; then
    awk -F "$(printf '\t')" -v types="$(cache_dir)/names.tsv" '$2 == "day" { print $3 }' "$(cache_dir)/names.tsv" \
      | LC_ALL=C sort > "$tmp/close-day-files"
    # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
    scan "$tmp/close-day-files" '
      FNR == 1 { file = rel(FILENAME) }
      /^[ \t]*- / {
        s = $0; sub(/^[ \t]*- /, "", s)
        if (s ~ /^~~/) next
        sub(/^[0-9][0-9]:[0-9][0-9] /, "", s)
        if (s ~ /^Idea:/) { t = $0; print file "\t" FNR "\t" t }
      }
    ' > "$tmp/close-idea-lines"
    awk -F '\t' -v US="$US" "$(rec_awk)"'
      { rec("7ideas", $1, pad($2), "", $1, $2, $3, "", "", "", "", "", "idea") }
    ' "$tmp/close-idea-lines" >> "$tmp/close-records"
    cat "$tmp/close-someday" >> "$tmp/close-records"
  fi
  LC_ALL=C sort -t "$US" -k1,1 -k2,2 -k3,3 -k4,4 "$tmp/close-records" -o "$tmp/close-records"
}

# quarter_start <first> <last>: yes when a day in the range is the first day of January, April, July or October.
quarter_start() {
  awk -v a="$1" -v b="$2" "$(awk_dates)"' BEGIN {
    for (z = ymd(a); z <= ymd(b); z++) { civil(z); if (CD == 1 && (CM - 1) % 3 == 0) { print "yes"; exit } }
    print "no"
  }'
}

# close_render <json yes|no> <cycle> <first> <last>: the first line, then the sections (or JSON Lines).
close_render() {
  local US
  US=$(printf '\037')
  if [ "$1" != yes ]; then
    local word=entries
    [ "$PENTRIES" = 1 ] && word=entry
    echo "== $2 $3 to $4: $PENTRIES $word (closes/${3:0:4}/$3-$2.md)"
  fi
  awk -F "$US" -v OFS="$US" -v json="$1" '
    BEGIN {
      label["1tasks"] = "tasks"; label["2open"] = "open"; label["2pfor"] = "for"; label["3due"] = "due"; label["4marked"] = "marked"
      label["5names"] = "names"; label["6quiet"] = "quiet"; label["7ideas"] = "ideas"
      json = (json == "yes")
    }
    FNR == NR { if ($1 == "5names" && length($10) > w) w = length($10); next }
    {
      sec = $1
      if (sec != cur) { cur = sec; if (!json) print "== " label[sec] }
      if (json) { print label[sec], $5, $6, $7, $8, $9, $10, $11, $12, $13; next }
      if (sec == "3due") print $7
      else if (sec == "4marked") print $5 ":" $6 ": " $7
      else if (sec == "5names") printf "%-" w "s  %d %s, no note\n", $10, $11, ($11 == 1 ? "mention" : "mentions")
      else print $5 ":" $6 ": " $13 ": " $7
    }
  ' "$tmp/close-records" "$tmp/close-records"
}

cmd_close() {
  local cycle="" date="" quarter=no json=no
  while [ $# -gt 0 ]; do
    case $1 in
      --cycle) [ $# -ge 2 ] || die 2 "--cycle needs a cycle name"; cycle=$2; shift 2 ;;
      --date) [ $# -ge 2 ] || die 2 "--date needs a day, YYYY-MM-DD"; is_date "$2" || die 2 "--date needs a day, YYYY-MM-DD, got: $2"; date=$2; shift 2 ;;
      --quarter) quarter=yes; shift ;;
      --json) json=yes; shift ;;
      *) die 2 "Usage: pkm close [--cycle name] [--date YYYY-MM-DD] [--quarter] [--json]" ;;
    esac
  done
  [ "$json" = no ] || need_jq
  index_ensure
  [ -n "$cycle" ] || cycle=$(config close week)
  [ -n "$date" ] || date=$(day_add "$today" -1)
  close_period "$cycle" "$date"
  close_sections "$PFIRST" "$PLAST" "$PNEXT" "$quarter"
  if [ "$json" = yes ]; then
    close_render yes "$cycle" "$PFIRST" "$PLAST" | jq -R -c 'split("\u001f") as $f
      | {kind: $f[0], path: (if $f[1] == "" then null else $f[1] end), line: (if $f[2] == "" then null else ($f[2] | tonumber) end),
         text: (if $f[3] == "" then null else $f[3] end), state: (if $f[4] == "" then null else $f[4] end),
         days: (if $f[5] == "" then null else ($f[5] | tonumber) end), name: (if $f[6] == "" then null else $f[6] end),
         count: (if $f[7] == "" then null else ($f[7] | tonumber) end), last: (if $f[8] == "" then null else $f[8] end),
         label: (if $f[9] == "" then null else $f[9] end)}'
  else
    close_render no "$cycle" "$PFIRST" "$PLAST"
  fi
}

# new_close [--cycle name] [--date D]: writes the close page of a period (by default the one holding yesterday), at
# closes/<year>/<first day>-<cycle>.md, titled "<Cycle> of <first day>". An existing page exits 1 and its path is printed.
new_close() {
  local cycle="" date="" path title template cap
  while [ $# -gt 0 ]; do
    case $1 in
      --cycle) [ $# -ge 2 ] || die 2 "--cycle needs a cycle name"; cycle=$2; shift 2 ;;
      --date) [ $# -ge 2 ] || die 2 "--date needs a day, YYYY-MM-DD"; is_date "$2" || die 2 "--date needs a day, YYYY-MM-DD, got: $2"; date=$2; shift 2 ;;
      *) die 2 "pkm new close takes no title: the period sets it. Usage: pkm new close [--cycle name] [--date YYYY-MM-DD]" ;;
    esac
  done
  index_ensure
  [ -n "$cycle" ] || cycle=$(config close week)
  [ -n "$date" ] || date=$(day_add "$today" -1)
  close_period "$cycle" "$date"
  path="closes/${PFIRST:0:4}/$PFIRST-$cycle.md"
  if [ -f "$path" ]; then echo "$path"; die 1 "$path already exists: open it, or pick another --cycle or --date."; fi
  template=$(template_file close.md)
  [ -f "$template" ] || die 2 "No close template: add $(template_file close.md), or reinstall pkm."
  cap=$(printf '%s' "${cycle:0:1}" | tr '[:lower:]' '[:upper:]')
  title="$cap${cycle:1} of $PFIRST"
  mkdir -p "$(dirname "$path")" || die 1 "Can't create $(dirname "$path")."
  render "$template" "$title" "$PFIRST-$cycle" "$PFIRST-$cycle" "$today" > "$tmp/close-page"
  mv "$tmp/close-page" "$path"
  echo "$path"
}
