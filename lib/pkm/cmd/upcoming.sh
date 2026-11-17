# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/upcoming.sh: pkm upcoming: the tasks due in the next days (routines included), overdue ones, and the
# birthday:, target:, deadline: and warranty: dates in that window. Prints DATE KIND path:line: text, by date.
# Sourced by bin/pkm. Defines functions only.

cmd_upcoming() {
  local days=${1:-14}
  number "$days" "The number of days"
  upcoming_lines "$days"
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
  cat "$tmp/upcoming-dates" "$tmp/upcoming-tasks" | LC_ALL=C sort
}
