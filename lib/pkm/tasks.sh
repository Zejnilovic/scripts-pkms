# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/tasks.sh: the tasks of the vault. A task is a "- [ ]" line in any note outside code. A box in a note of
# type: list, and a struck line, is not a task. Its markers sit in the line: (due D) or 📅 D, (waiting D), (someday),
# (high), (low), (every RULE), and (done D) or (dropped D) once closed. A relative date (friday, +3d, today, tomorrow)
# is read against the date of the day page the task is on, in awk (dates.sh awk_dates), so no task starts a process.
# Sourced by bin/pkm. Defines functions only.

# awk_tasks: the task lines, one per line, in the fields of task_records. It needs awk_dates in front of it. A routine
# goes to the file in RELOUT instead, for task_records to check its rule.
awk_tasks() {
  cat <<'AWK'
  function marker(s, key,   i, rest, v) {
    i = index(s, "(" key " "); if (i == 0) return ""
    rest = substr(s, i + length(key) + 2); v = index(rest, ")"); if (v == 0) return ""
    return substr(rest, 1, v - 1)
  }
  function emoji_date(s,   i, m, rest, v) {
    # Measured, not counted: gawk in a UTF-8 locale counts the emoji as one character, mawk as four bytes.
    m = "\360\237\223\205 "; i = index(s, m); if (i == 0) return ""
    rest = substr(s, i + length(m)); v = match(rest, /[ )]/)
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
    problem = ""; due_iso = ""
    if (due != "") {
      if (is_day(due)) due_iso = due
      else if (!relative_word(due)) problem = "cannot read the due date " due
      else if (day == "") problem = "relative date " due " is outside a day page: write its date"
      else if ((due_iso = day_word(due, day)) == "") problem = "cannot read the due date " due
    }
    if (problem == "" && waiting != "" && waiting != "?" && !is_day(waiting)) problem = "cannot read the waiting date " waiting
    if (problem == "" && start != "" && !is_day(start)) problem = "cannot read the start date " start
    fields = file OFS FNR OFS state OFS due_iso OFS waiting OFS someday OFS prio OFS closed OFS rule OFS day OFS problem OFS start OFS t
    if (rule != "") print fields > ENVIRON["RELOUT"]
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
  # The dates are read in awk. A routine goes to task-raw, and its rule is checked below, one routine at a time.
  : > "$tmp/task-raw"
  RELOUT="$tmp/task-raw" scan "$tmp/task-files" "$(awk_dates)$(awk_tasks)" -F '\037' -v OFS='\037' > "$tmp/task-plain"
  local US file line state due_iso waiting someday prio closed rule day start text problem
  US=$(printf '\037')
  : > "$tmp/task-records"
  while IFS=$US read -r file line state due_iso waiting someday prio closed rule day problem start text; do
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
