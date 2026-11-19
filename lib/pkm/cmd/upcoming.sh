# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/upcoming.sh: pkm upcoming: the tasks due in the next days (routines included), overdue ones, the
# birthday:, target:, deadline: and warranty: dates in that window, and the events on each of their days (events.sh). Prints DATE KIND path:line: text, by date.
# Sourced by bin/pkm. Defines functions only.

cmd_upcoming() {
  local days=14 ics=no arg
  for arg in "$@"; do
    case $arg in
      --ics) ics=yes ;;
      *) days=$arg ;;
    esac
  done
  number "$days" "The number of days"
  if [ "$ics" = yes ]; then upcoming_ics; else upcoming_lines "$days"; fi
}

# upcoming_lines <days>: the dated lines of the next <days> days, as DATE KIND path:line: text, sorted by date.
upcoming_lines() {
  local days=$1 end window i d US
  US=$(printf '\037')
  end=$(day_add "$today" "$days") window="" i=0
  while [ "$i" -le "$days" ]; do
    d=$(day_add "$today" "$i"); window="$window ${d#*-}=$d"; i=$((i + 1))
  done
  files no '*.md' > "$tmp/list"
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  TODAY=$today END=$end WINDOW=$window scan "$tmp/list" '
    function is_day(s) { return s ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/ }
    function close_front(   k) {
      if (status ~ /^(done|dropped|published|sold|gone|archived)$/) return
      for (k in dated) if (dated[k] >= ENVIRON["TODAY"] && dated[k] <= ENVIRON["END"]) print dated[k] " " k " " file ":" dated_line[k] ": " dated_text[k]
    }
    BEGIN { n = split(ENVIRON["WINDOW"], pairs, " "); for (i = 1; i <= n; i++) win[substr(pairs[i], 1, 5)] = substr(pairs[i], 7) }
    FNR == 1 {
      file = rel(FILENAME); status = ""; split("", dated); split("", dated_line); split("", dated_text)
      front = ($0 == "---"); if (front) next
    }
    front && $0 == "---" { front = 0; close_front(); next }
    front && match($0, /^[A-Za-z0-9_-]+:/) {
      key = substr($0, 1, RLENGTH - 1); v = substr($0, RLENGTH + 1); gsub(/^[ \t"]+|[ \t"]+$/, "", v)
      if (key == "status") status = tolower(v)
      if (key == "birthday" && length(v) >= 5 && (substr(v, length(v) - 4) in win)) print win[substr(v, length(v) - 4)] " birthday " file ":" FNR ": " $0
      if ((key == "target" || key == "deadline" || key == "warranty") && is_day(v)) { dated[key] = v; dated_line[key] = FNR; dated_text[key] = $0 }
      next
    }
  ' | LC_ALL=C sort > "$tmp/upcoming-dates"
  # A task hidden until its start date, or a someday task that has not started, is not due; a hidden one whose start
  # falls in the window is listed by that start date, as "<start> start path:line: text".
  task_records no | awk -F "$US" -v OFS=' ' -v end="$end" -v today="$today" '
    $3 == "open" && $12 != "" && $12 > today && $12 <= end { print $12, "start", $1 ":" $2 ": " $13 }
    $3 == "open" && $4 != "" && $4 <= end && !($12 != "" && $12 > today) && !($6 == 1 && !($12 != "" && $12 <= today)) {
      kind = ($4 < today) ? "overdue" : "due"
      print $4, kind, $1 ":" $2 ": " $13
    }
  ' | LC_ALL=C sort > "$tmp/upcoming-tasks"
  # Each line gets a sort key: itself, or for an event, its date and start time, so a day's events come by time.
  { awk '{ print $0 "\037" $0 }' "$tmp/upcoming-dates" "$tmp/upcoming-tasks"; event_lines "$today" "$end"; } \
    | LC_ALL=C sort | cut -d "$US" -f 2-
}

# upcoming_ics: the vault's events, its open tasks with an (at …) and its birthdays as an iCalendar file (RFC 5545), from
# all of the vault: one VEVENT each, an event that comes back with its RRULE and an EXDATE for each skip. Times are
# floating (local, with no time zone); a whole-day event is a DATE. The SUMMARY is the line's plain text (plain.sh). The
# UID is made from the path and the summary, so it stays when lines above move; a repeat in the same file adds -2, -3.
upcoming_ics() {
  local US tab
  US=$(printf '\037')
  tab=$(printf '\t')
  index_ensure
  # kind, path, line, markers, page date, text: the readable events and the open tasks with an (at …).
  line_records no | awk -F "$US" -v OFS="$US" "$(awk_dates)$(awk_events)"'
    ($3 == "event" && event_readable($8, $9)) || ($3 == "task" && $4 == "open" && index("\t" $5, "\tat ")) {
      print $3, $1, $2, $5, $6, $10
    }' > "$tmp/ics-lines"
  # The birthdays: birthday, path, 0, the date as written, "", the note's title.
  awk -F "$tab" -v OFS="$US" '
    FILENAME == ARGV[1] { title[$1] = $2; next }
    $2 == "birthday" && $1 !~ /^archive\// && $3 != "" { print "birthday", $1, 0, $3, "", ($1 in title) ? title[$1] : $1 }
  ' "$(cache_dir)/notes.tsv" "$(cache_dir)/fields.tsv" >> "$tmp/ics-lines"
  awk -F "$US" '$1 != "birthday" { print $6 }' "$tmp/ics-lines" > "$tmp/ics-texts"
  plain_titles "$tmp/ics-texts" "$tmp/ics-titles"
  LC_ALL=C awk -F "$US" -v now="$now" -v year="${today%%-*}" -v version="$pkm_version" \
    "$(awk_dates)$(awk_markers)$(awk_events)$(awk_plain)"'
    function out(s,   n) {
      # Folded at 75 octets, never inside a character: a cut moves back over UTF-8 continuation bytes.
      while (length(s) > 75) {
        n = (first_line ? 75 : 74); first_line = 0
        while (n > 1 && substr(s, n + 1, 1) >= "\200" && substr(s, n + 1, 1) < "\300") n--
        printf "%s\r\n ", substr(s, 1, n); s = substr(s, n + 1)
      }
      printf "%s\r\n", s
    }
    function line(s) { first_line = 1; out(s) }
    # A backslash, semicolon or comma gets a backslash: one character at a time, as awks differ on "\\" in gsub.
    function esc(s,   o, i, c) {
      o = ""
      for (i = 1; i <= length(s); i++) { c = substr(s, i, 1); o = o ((c == "\\" || c == ";" || c == ",") ? "\\" c : c) }
      return o
    }
    function compact(d) { gsub(/-/, "", d); return d }
    function hash(s, seed,   h, i) {
      h = seed
      for (i = 1; i <= length(s); i++) h = (h * 31 + ORD[substr(s, i, 1)]) % 4294967291
      return sprintf("%08x", h)
    }
    function uid(path, summary,   key) {
      key = path "\n" summary; count[key]++
      return hash(key, 7) hash(key, 11) (count[key] > 1 ? "-" count[key] : "") "@pkm"
    }
    function skip_backward(date, unit) {
      return (unit == "m" && substr(date, 9, 2) + 0 >= 29) || (unit == "y" && substr(date, 6, 5) == "02-29")
    }
    function begin(summary, path) {
      line("BEGIN:VEVENT"); line("UID:" uid(path, summary)); line("DTSTAMP:" stamp); line("SUMMARY:" esc(summary))
    }
    BEGIN {
      for (i = 1; i < 256; i++) ORD[sprintf("%c", i)] = i
      stamp = substr(now, 1, 8) "T" substr(now, 9, 6) "Z"
      line("BEGIN:VCALENDAR"); line("VERSION:2.0"); line("PRODID:-//pkm//pkm " version "//EN"); line("CALSCALE:GREGORIAN")
    }
    FILENAME == ARGV[1] { split($0, f, "\t"); PLAIN_TITLE[f[1]] = f[2]; next }
    $1 == "birthday" {
      d = $4
      if (!is_day(d)) { d = year "-" substr(d, length(d) - 4); if (!is_day(d) && substr(d, 6) != "02-29") next }
      begin("Birthday: " $6, $2)
      line("DTSTART;VALUE=DATE:" compact(d)); line("DTEND;VALUE=DATE:" compact(iso(ymd(d) + 1)))
      line("RRULE:" (skip_backward(d, "y") ? "RSCALE=GREGORIAN;" : "") "FREQ=YEARLY;INTERVAL=1" (skip_backward(d, "y") ? ";SKIP=BACKWARD" : ""))
      line("END:VEVENT"); next
    }
    {
      m = $4
      if (event_when(mval(m, "at"), $5) != "") next
      rule = ""
      if ($1 == "event" && $5 == "") { rule = mval(m, "every"); if (!event_rule_ok(rule)) rule = "" }
      begin(plain_summary($6), $2)
      if (EV_START == "") {
        line("DTSTART;VALUE=DATE:" compact(EV_FIRST)); line("DTEND;VALUE=DATE:" compact(iso(ymd(EV_LAST) + 1)))
      } else {
        line("DTSTART:" compact(EV_FIRST) "T" compact_time(EV_START))
        if (EV_END != "") line("DTEND:" compact((EV_END < EV_START) ? iso(ymd(EV_FIRST) + 1) : EV_FIRST) "T" compact_time(EV_END))
      }
      if (rule != "") {
        unit = substr(rule, length(rule)); n = substr(rule, 1, length(rule) - 1) + 0
        freq = (unit == "d") ? "DAILY" : (unit == "w") ? "WEEKLY" : (unit == "m") ? "MONTHLY" : "YEARLY"
        until = mval(m, "until"); back = skip_backward(EV_FIRST, unit)
        r = (back ? "RSCALE=GREGORIAN;" : "") "FREQ=" freq ";INTERVAL=" n
        if (is_day(until)) r = r ";UNTIL=" compact(until) (EV_START == "" ? "" : "T235959")
        line("RRULE:" r (back ? ";SKIP=BACKWARD" : ""))
        k = split(m, a, "\t")
        for (i = 1; i <= k; i++) if (substr(a[i], 1, 5) == "skip " && is_day(v = substr(a[i], 6)))
          line(EV_START == "" ? "EXDATE;VALUE=DATE:" compact(v) : "EXDATE:" compact(v) "T" compact_time(EV_START))
      }
      line("END:VEVENT")
    }
    function compact_time(t) { sub(/:/, "", t); return t "00" }
    END { line("END:VCALENDAR") }
  ' "$tmp/ics-titles" "$tmp/ics-lines"
}
