# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/tasks.sh: the tasks of the vault. A task is a "- [ ]" line in any note outside code. A box in a note of
# type: list, and a struck line, is not a task. Its markers sit in the line: (due D) or 📅 D, (waiting D), (someday),
# (high), (low), (every RULE), and (done D) or (dropped D) once closed. A relative date (friday, +3d, today, tomorrow)
# is read against the date of the day page the task is on. Sourced by bin/pkm. Defines functions only.

# awk_tasks: the raw task lines, one per line, fields separated by the unit separator: file, line, state, due as written,
# waiting ("?" when marked without a date), someday (1 or 0), priority, done date, rule, day page date, text.
awk_tasks() {
  cat <<'AWK'
  function marker(s, key,   i, rest, v) {
    i = index(s, "(" key " "); if (i == 0) return ""
    rest = substr(s, i + length(key) + 2); v = index(rest, ")"); if (v == 0) return ""
    return substr(rest, 1, v - 1)
  }
  # A calendar date written YYYY-MM-DD. Checked here, in awk, so the common case never starts a process.
  function iso(s,   y, m, d, dim) {
    if (s !~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/) return 0
    y = substr(s, 1, 4) + 0; m = substr(s, 6, 2) + 0; d = substr(s, 9, 2) + 0
    if (m < 1 || m > 12 || d < 1) return 0
    split("31 28 31 30 31 30 31 31 30 31 30 31", dim, " ")
    dim[2] = (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)) ? 29 : 28
    return d <= dim[m] + 0
  }
  function emoji_date(s,   i, rest, v) {
    i = index(s, "\360\237\223\205 "); if (i == 0) return ""
    rest = substr(s, i + 5); v = match(rest, /[ )]/)
    return v ? substr(rest, 1, v - 1) : rest
  }
  FNR == 1 {
    file = rel(FILENAME); fence = 0; b = base(file)
    day = (b ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/) ? substr(b, 1, 10) : ""
    list = 0; front = ($0 == "---")
  }
  front && FNR > 1 { if ($0 == "---") front = 0; else if ($0 ~ /^type:[ \t]*list[ \t]*$/) list = 1; next }
  /^[ \t]*(```|~~~)/ { fence = !fence; next }
  fence || list || !/^[ \t]*- \[.\] / { next }
  {
    t = $0; sub(/^[ \t]+/, "", t); gsub(/\t/, " ", t)
    c = substr(t, 4, 1)
    if (c == " ") state = "open"
    else if (c == "x" || c == "X") state = "done"
    else if (c == "-") state = "dropped"
    else next
    if (substr(t, 7, 2) == "~~") next
    if (index(t, "(recall ")) next
    due = marker(t, "due"); if (due == "") due = emoji_date(t)
    waiting = marker(t, "waiting"); sub(/^since /, "", waiting)
    if (waiting == "" && index(t, "(waiting")) waiting = "?"
    someday = index(t, "(someday)") ? 1 : 0
    prio = index(t, "(high)") ? "high" : (index(t, "(low)") ? "low" : "")
    closed = ""
    if (state == "done") closed = marker(t, "done")
    if (state == "dropped") closed = marker(t, "dropped")
    rule = marker(t, "every")
    start = marker(t, "start")
    fields = file OFS FNR OFS state OFS due OFS waiting OFS someday OFS prio OFS closed OFS rule OFS day OFS "" OFS start OFS t
    # A task with a routine, or a date that isn't a calendar date, is resolved in bash (task_records).
    if ((due != "" && !iso(due)) || (waiting != "" && waiting != "?" && !iso(waiting)) || (start != "" && !iso(start)) || rule != "") print fields > ENVIRON["RELOUT"]
    else print fields
  }
AWK
}

# task_records <yes|no: include archive/>: one line per task, fields separated by the unit separator:
# 1 path, 2 line, 3 state (open, done or dropped), 4 due (ISO, or empty), 5 waiting (ISO, "?", or empty),
# 6 someday (1 or 0), 7 priority (high, low or empty), 8 done or dropped date, 9 rule of an (every) routine,
# 10 the day page's date (or empty), 11 a problem with a marker (or empty), 12 start (ISO, or empty: the task is hidden
# until then), 13 the text of the line.
# A relative due date is resolved against the day page's date; the problem says when it cannot be. A routine (every) is
# an interval (every 1w), a cycle name (every sprint), or an old rule that is no longer one: a routine lives in a note,
# so one on a day page is a problem too.
task_records() {
  files "$1" '*.md' > "$tmp/task-files"
  local cyc
  cyc=$(cycle_names)
  # Dates written as calendar dates pass straight through; a relative date, or one that can't be read as it stands,
  # goes to task-raw and is resolved below, one task at a time.
  : > "$tmp/task-raw"
  RELOUT="$tmp/task-raw" scan "$tmp/task-files" "$(awk_tasks)" -F '\037' -v OFS='\037' > "$tmp/task-plain"
  local US file line state due waiting someday prio closed rule day start text problem due_iso
  US=$(printf '\037')
  : > "$tmp/task-records"
  while IFS=$US read -r file line state due waiting someday prio closed rule day _ start text; do
    problem="" due_iso=""
    if [ -n "$due" ]; then
      if is_date "$due"; then due_iso=$due
      elif ! (today=2000-01-01; parse_day "$due") >/dev/null 2>&1; then problem="cannot read the due date $due"
      elif [ -z "$day" ]; then problem="relative date $due is outside a day page: write its date"
      elif due_iso=$(today=$day; parse_day "$due"); then :
      else problem="cannot read the due date $due"; fi
    fi
    if [ -n "$waiting" ] && [ "$waiting" != "?" ] && ! is_date "$waiting"; then
      [ -n "$problem" ] || problem="cannot read the waiting date $waiting"
    fi
    if [ -n "$start" ] && ! is_date "$start"; then
      [ -n "$problem" ] || problem="cannot read the start date $start"
    fi
    # A routine is an interval (every 1m) or a cycle (every sprint). An undated cycle routine is due on the last day of
    # the period holding today. An old rule (every monday) is no longer a routine, and a name that is neither is a problem.
    if [ -n "$rule" ]; then
      if [ -n "$day" ]; then
        [ -n "$problem" ] || problem="a routine belongs in a note: a day page is a record, so move (every $rule) to a note"
      fi
      if printf '%s\n' "$rule" | grep -Eq '^[0-9]+[dwmy]$'; then :
      elif printf '%s\n' "$cyc" | grep -qx -- "$rule"; then
        [ -n "$due_iso" ] || due_iso=$(cycle_routine_due "$rule")
      elif valid_rule "$rule"; then
        [ -n "$problem" ] || problem="(every $rule) is no longer a routine: write it as (every 1w) with a due date, or name a cycle"
      else
        [ -n "$problem" ] || problem="(every $rule) names no cycle: set cycle_$rule in .pkm/config, or use an interval such as (every 1m)"
      fi
    fi
    printf '%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s\037%s\n' \
      "$file" "$line" "$state" "$due_iso" "$waiting" "$someday" "$prio" "$closed" "$rule" "$day" "$problem" "$start" "$text"
  done < "$tmp/task-raw" > "$tmp/task-records"
  cat "$tmp/task-plain" "$tmp/task-records"
}
