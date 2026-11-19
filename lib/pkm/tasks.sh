# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/tasks.sh: the tasks of the vault, from the line scanner (lines.sh): its records of kind task. Their markers:
# (due D) or 📅 D, (waiting D), (someday), (high), (low), (every RULE), (start D), and (done D) or (dropped D) once
# closed. A task with an (at …) is due on the event's first day (events.sh) unless it has a (due …). A relative date
# (friday, +3d, today, tomorrow) is read against the date of the day page the task is on, in awk (dates.sh awk_dates),
# so no task starts a process. Sourced by bin/pkm. Defines functions only.

# awk_tasks: reads the scanner's records (lines.sh) and prints the tasks in the fields of task_records. It needs
# awk_dates, awk_markers and awk_events in front of it. A routine goes to the file in RELOUT instead, for task_records
# to check its rule.
awk_tasks() {
  cat <<'AWK'
  $3 != "task" { next }
  {
    m = $5; day = $6; t = $10; state = $4
    due = mval(m, "due")
    waiting = mval(m, "waiting"); sub(/^since /, "", waiting)
    if (waiting == "" && (mflag(m, "waiting") || mhas(m, "waiting"))) waiting = "?"
    someday = mflag(m, "someday")
    prio = mflag(m, "high") ? "high" : (mflag(m, "low") ? "low" : "")
    closed = ""
    if (state == "done") closed = mval(m, "done")
    if (state == "dropped") closed = mval(m, "dropped")
    rule = mval(m, "every")
    start = mval(m, "start")
    problem = ""; due_iso = ""
    if (due != "") {
      if (is_day(due)) due_iso = due
      else if (!relative_word(due)) problem = "cannot read the due date " due
      else if (day == "") problem = "relative date " due " is outside a day page: write its date"
      else if ((due_iso = day_word(due, day)) == "") problem = "cannot read the due date " due
    }
    # A task with an (at …) is due on the event's first day, unless it has its own (due …).
    if (due == "" && mhas(m, "at")) {
      p = event_when(mval(m, "at"), day)
      if (p == "") due_iso = EV_FIRST; else problem = p
    }
    if (problem == "" && waiting != "" && waiting != "?" && !is_day(waiting)) problem = "cannot read the waiting date " waiting
    if (problem == "" && start != "" && !is_day(start)) problem = "cannot read the start date " start
    fields = $1 OFS $2 OFS state OFS due_iso OFS waiting OFS someday OFS prio OFS closed OFS rule OFS day OFS problem OFS start OFS t
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
  local cyc
  cyc=$(cycle_names)
  # The dates are read in awk. A routine goes to task-raw, and its rule is checked below, one routine at a time.
  : > "$tmp/task-raw"
  line_records "$1" > "$tmp/task-lines"
  RELOUT="$tmp/task-raw" awk -F '\037' -v OFS='\037' "$(awk_dates)$(awk_markers)$(awk_events)$(awk_tasks)" "$tmp/task-lines" > "$tmp/task-plain"
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
