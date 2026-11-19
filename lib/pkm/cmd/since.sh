# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/since.sh: pkm since [last | YYYY-MM-DD | N | cycle] [--about NAME] [--limit n] [--json]: what happened from
# a date to today, in the day pages of every writer, as sections: == notes (created in the range), == log (every line),
# == tasks (overdue, and waiting, each with its days), == marked (! Decided: Idea: entries and questions) and == names (the
# names linked, with their count and last day). Only sections with lines are printed; with none, "Nothing since <date>."
# and exit 1. last starts on the date in .pkm/state (set by since --seen, with its time), or the last 7 days; on that date it
# leaves out the entries timed at or before the stored time, and keeps untimed lines. N is today and the N-1 days
# before. --about NAME keeps the lines that link NAME, a ### heading's links included. Sourced by bin/pkm.

# since_build <start>: the records of the sections, US-separated: section, sort keys, path, line, text, state, days, name,
# count, last, label. Reads $tmp/dg-names, $tmp/dg-pages and $tmp/since-tasks; the environment has ABOUT, TODAY and US.
since_build() {
  awk -F "$US" -v OFS="$US" -v US="$US" -v ABOUT="$ABOUT" -v TODAY="$TODAY" -v START="$1" -v SEEN="${SEEN_TIME:-}" "$(awk_dates)"'
    function ago(d,  k) { k = ymd(TODAY) - ymd(d); if (k == 0) return "today"; if (k == 1) return "yesterday"; return k " days ago" }
    function pad(n) { return sprintf("%06d", n) }
    function marked_text(t,  s) {
      if (t !~ /^[ \t]*- /) return 0
      s = t; sub(/^[ \t]*- /, "", s)
      if (s ~ /^~~/) return 0
      sub(/^[0-9][0-9]:[0-9][0-9] /, "", s)
      return (s ~ /^! / || s ~ /^Decided:/ || s ~ /^Idea:/ || s ~ /\?[ \t]*$/)
    }
    function emit(sec, a, b, c, path, line, text, state, days, name, count, last, label) {
      print sec US a US b US c US path US line US text US state US days US name US count US last US label
    }
    FILENAME == ARGV[1] {
      key = $1 SUBSEP $2
      if ($4 == 1) {
        allk[key] = allk[key] "|" $3 "|"
        if ($5 != "" && !((key SUBSEP $3) in seen)) { seen[key SUBSEP $3] = 1; dayown[key] = dayown[key] "|" $3 "|"; dayd[key] = $5 }
      } else allk[key] = allk[key] "|" $3 "|"
      next
    }
    FILENAME == ARGV[2] {
      if ($4 != "l") next
      # since last leaves out the entries of the seen day timed at or before the seen time; untimed lines stay.
      if (SEEN != "" && $2 == START && $5 ~ /^[ \t]*- [0-9][0-9]:[0-9][0-9]/) {
        t = $5; sub(/^[ \t]*- /, "", t); t = substr(t, 1, 5)
        if (t <= SEEN) next
      }
      key = $1 SUBSEP $3
      if (ABOUT != "" && index(allk[key], "|" ABOUT "|") == 0) next
      kept[key] = 1
      emit("2log", $1, pad($3), "", $1, $3, $5, "", "", "", "", "", "")
      if (marked_text($5)) emit("4marked", $1, pad($3), "", $1, $3, $5, "", "", "", "", "", "")
      next
    }
    FILENAME == ARGV[3] {
      if ($3 != "open") next
      if ($12 != "" && $12 > TODAY) next                      # hidden until its start date
      if ($6 == 1 && !($12 != "" && $12 <= TODAY)) next       # someday, and not started yet
      key = $1 SUBSEP $2
      if (ABOUT != "" && index(allk[key], "|" ABOUT "|") == 0) next
      if ($4 != "" && $4 < TODAY) {
        emit("3task", $1, pad($2), "", $1, $2, $13, "open", ymd(TODAY) - ymd($4), "", "", "", "overdue")
      } else if ($5 == "?") {
        emit("3task", $1, pad($2), "", $1, $2, $13, "open", "", "", "", "", "waiting")
      } else if ($5 != "" && $5 <= TODAY) {
        d = ymd(TODAY) - ymd($5)
        emit("3task", $1, pad($2), "", $1, $2, $13, "open", d, "", "", "", "waiting " d " days")
      }
      next
    }
    END {
      for (key in kept) {
        if (!(key in dayown)) continue
        n = split(dayown[key], arr, "|")
        for (i = 1; i <= n; i++) {
          if (arr[i] == "" || ((arr[i] SUBSEP key) in counted)) continue
          counted[arr[i] SUBSEP key] = 1; cnt[arr[i]]++
          if (!(arr[i] in lastd) || dayd[key] > lastd[arr[i]]) lastd[arr[i]] = dayd[key]
        }
      }
      for (name in cnt) emit("5name", pad(999999 - cnt[name]), name, "", "", "", "", "", "", name, cnt[name], lastd[name], ago(lastd[name]))
    }
  ' "$tmp/dg-names" "$tmp/dg-pages" "$tmp/since-tasks"
}

# since_render <records file> <json yes|no> <limit>: prints the sorted records as sections, or as JSON Lines (kind, path,
# line, text, state, days, name, count, last). Lines past the limit of a section are left out, with a footer on stderr.
since_render() {
  local US
  US=$(printf '\037')
  awk -F "$US" -v OFS="$US" -v json="$2" -v limit="$3" '
    BEGIN {
      label["1note"] = "notes"; label["2log"] = "log"; label["3task"] = "tasks"; label["4marked"] = "marked"; label["5name"] = "names"
      json = (json == "yes")
    }
    FNR == NR {
      if ($1 == "5name") { if (length($10) > w1) w1 = length($10); if (length($11) > w2) w2 = length($11) }
      cnt[$1]++
      next
    }
    function footer() { if (!json && cnt[cur] > limit) printf "... %d more (use --limit)\n", cnt[cur] - limit > "/dev/stderr" }
    {
      sec = $1
      if (sec != cur) { footer(); cur = sec; shown = 0; if (!json) print "== " label[sec] }
      shown++
      if (shown > limit) next
      if (json) {
        print substr(sec, 2), $5, $6, $7, $8, $9, $10, $11, $12
        next
      }
      if (sec == "5name") printf "%-" w1 "s  %" w2 "d %s  last %s\n", $10, $11, ($11 == 1 ? "mention" : "mentions"), $13
      else if (sec == "3task") print $5 ":" $6 ": " $13 ": " $7
      else print $5 ":" $6 ": " $7
    }
    END { footer() }
  ' "$1" "$1"
}

# since_notes <from> <to>: the notes section records: notes whose created: date is in the range (not day or close pages, not
# the archive), each with the line of its title.
since_notes() {
  local US
  US=$(printf '\037')
  awk -F "$(printf '\t')" -v from="$1" -v to="$2" \
    'FILENAME == ARGV[1] { if ($2 == "created") { v = $3; gsub(/[ \t"]/, "", v); if (v >= from && v <= to) cr[$1] = 1 } next }
     FILENAME == ARGV[2] { if ($3 != "day" && $3 != "close" && $1 !~ /^archive\//) ok[$1] = 1 }
     END { for (p in cr) if (p in ok) print p }' "$(cache_dir)/fields.tsv" "$(cache_dir)/notes.tsv" \
    | LC_ALL=C sort > "$tmp/since-note-files"
  [ -s "$tmp/since-note-files" ] || return 0
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/since-note-files" '
    FNR == 1 { file = rel(FILENAME); done = 0 }
    !done && /^# / { print "1note" US file US "000000" US "" US file US FNR US $0 US "" US "" US "" US "" US "" US ""; done = 1 }
  ' -v US="$US"
}

cmd_since() {
  local arg="" about="" seen=no limit="" json=no start US ABOUT TODAY
  US=$(printf '\037')
  while [ $# -gt 0 ]; do
    case $1 in
      --seen) seen=yes; shift ;;
      --json) json=yes; shift ;;
      --about) [ $# -ge 2 ] || die 2 "--about needs a name"; about=$2; shift 2 ;;
      --limit) [ $# -ge 2 ] || die 2 "--limit needs a whole number"; number "$2" "--limit"; limit=$2; shift 2 ;;
      *) [ -z "$arg" ] || die 2 "Usage: pkm since [last | YYYY-MM-DD | N | cycle] [--about NAME] [--limit n] [--json]"; arg=$1; shift ;;
    esac
  done
  TODAY=$today
  if [ "$seen" = yes ]; then
    [ -z "$arg" ] && [ -z "$about" ] && [ "$json" = no ] && [ -z "$limit" ] || die 2 "pkm since --seen takes no other argument."
    local seen_time
    seen_time="${now:8:2}:${now:10:2}"
    state_write_since "$today" "$seen_time" || exit $?
    echo "The next since last starts after $today $seen_time."
    return 0
  fi
  index_ensure
  [ -n "$limit" ] || limit=$(config limit 30)
  [ -n "$arg" ] || arg=last
  SEEN_TIME=""
  if is_date "$arg"; then start=$arg
  elif [ "$arg" = last ]; then
    start=$(state_since)
    [ -n "$start" ] || start=$(day_add "$today" -6)
    SEEN_TIME=$(state_since_time)
  elif printf '%s\n' "$arg" | grep -Eq '^[0-9]+$'; then
    [ "$arg" -ge 1 ] || die 2 "A number of days is at least 1, got: $arg"
    start=$(day_add "$today" $((1 - arg)))
  elif cycle_known "$arg"; then
    start=$(cycle_period "$arg" "$(day_add "$today" -1)" | cut -d ' ' -f 1)
  else
    die 2 "Usage: pkm since [last | YYYY-MM-DD | N | cycle] [--about NAME] [--limit n] [--json]: $arg is none of them"
  fi
  ABOUT=""
  if [ -n "$about" ]; then
    local target
    target=$(resolve_note "$about")
    if [ -n "$target" ]; then ABOUT=$(basename "$target" .md)
    else printf '%s\n' "$about" > "$tmp/since-about"; link_slugs "$tmp/since-about" "$tmp/since-about-slug"; ABOUT=$(cut -f 2 "$tmp/since-about-slug"); fi
  fi
  digest_pages "$start" "$today"
  digest_names
  task_records no > "$tmp/since-tasks"
  {
    [ -n "$about" ] || since_notes "$start" "$today"
    ABOUT=$ABOUT TODAY=$today US=$US SEEN_TIME=$SEEN_TIME since_build "$start"
  } | LC_ALL=C sort -t "$US" -k1,1 -k2,2 -k3,3 -k4,4 > "$tmp/since-records"
  if [ ! -s "$tmp/since-records" ]; then
    [ "$json" = yes ] || echo "Nothing since $start."
    return 1
  fi
  if [ "$json" = yes ]; then
    since_render "$tmp/since-records" yes "$limit" | jq -R -c 'split("\u001f") as $f
      | {kind: $f[0], path: (if $f[1] == "" then null else $f[1] end), line: (if $f[2] == "" then null else ($f[2] | tonumber) end),
         text: (if $f[3] == "" then null else $f[3] end)}
      | (if $f[0] == "task" then . + {state: $f[4], days: (if $f[5] == "" then null else ($f[5] | tonumber) end)} else . end)
      | (if $f[0] == "name" then . + {name: $f[6], count: ($f[7] | tonumber), last: $f[8]} else . end)'
  else
    since_render "$tmp/since-records" no "$limit"
  fi
}
