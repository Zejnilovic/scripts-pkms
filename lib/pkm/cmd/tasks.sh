# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/tasks.sh: pkm tasks: the open tasks of every note, or the waiting, someday or done ones.
# Order: overdue (oldest due first), then due within due_soon_days (soonest first), then waiting for more than
# waiting_days (longest first), then the rest (by due date, undated last, then by the day page's date, path and line).
# --for <who> keeps the tasks and questions that are someone's (people.sh): a writer's own tasks and those for them.
# --under <note> keeps those of the note's tree (tree.sh).
# Sourced by bin/pkm. Defines functions only.

cmd_tasks() {
  local view=open all=no stale="" link="" since="" cutoff="" soon waited soon_end waited_cut US for="" key="" under=""
  while [ $# -gt 0 ]; do
    case $1 in
      --all) all=yes; shift ;;
      --stale) [ $# -ge 2 ] || die 2 "--stale needs a number of days"; number "$2" "--stale"; stale=$2; shift 2 ;;
      --link) [ $# -ge 2 ] || die 2 "--link needs a name"; link=${2%.md}; shift 2 ;;
      --under) [ $# -ge 2 ] && [ -n "$2" ] || die 2 "--under needs a note, such as apollo"; under=$2; shift 2 ;;
      --for) [ $# -ge 2 ] && [ -n "$2" ] || die 2 "--for needs a name: a writer, or a note such as jane-doe"; for=$2; shift 2 ;;
      open|waiting|someday) view=$1; shift ;;
      "done") view="done"; shift; if [ $# -gt 0 ] && is_date "$1"; then since=$1; shift; fi ;;
      *) die 2 "Usage: pkm tasks [open | waiting | someday | done [YYYY-MM-DD]] [--link <name>] [--for <who>] [--under <note>] [--stale <days>] [--all]" ;;
    esac
  done
  if [ "$view" = "done" ]; then all=yes; [ -n "$since" ] || since=$(day_add "$today" -7); fi
  [ -z "$stale" ] || cutoff=$(day_add "$today" "-$stale")
  soon=$(config due_soon_days 7); number "$soon" due_soon_days
  soon_end=$(day_add "$today" "$soon")
  waited=$(config waiting_days 7); number "$waited" waiting_days
  waited_cut=$(day_add "$today" "-$waited")
  task_records "$all" > "$tmp/tasks-all"
  US=$(printf '\037')
  # --for keeps the tasks that are someone's (people.sh), and adds their questions as records of state "question".
  : > "$tmp/tasks-for"
  if [ -n "$for" ]; then
    key=$(for_key "$for") || die 1 "No writer or note named $for: give a writer of the vault's day pages, or a note's name."
    for_records | KEY=$key awk -F "$US" -v OFS="$US" '$5 == ENVIRON["KEY"] && ($3 == "task" || $3 == "question")' > "$tmp/tasks-for-records"
    awk -F "$US" '{ print $1 ":" $2 }' "$tmp/tasks-for-records" > "$tmp/tasks-for"
    awk -F "$US" -v OFS="$US" '$3 == "question" { print $1, $2, "question", "", "", 0, "", "", "", $8, "", "", $9 }' \
      "$tmp/tasks-for-records" >> "$tmp/tasks-all"
  fi
  # --under keeps the tasks of the notes in a note's tree, and those on day pages about one of them (tree.sh).
  if [ -n "$under" ]; then
    under_build "$under"
    under_keep "$tmp/tasks-all"
  fi
  awk -F "$US" -v OFS="$US" -v view="$view" -v since="$since" -v link="$link" -v cutoff="$cutoff" -v all="$all" \
      -v today="$today" -v soon_end="$soon_end" -v waited_cut="$waited_cut" -v forwho="$for" '
    FILENAME == ARGV[1] { mine[$0] = 1; next }
    function about(text, path,   n, b) {
      n = link; if (n == "") return 1
      b = path; sub(/.*\//, "", b); sub(/\.md$/, "", b)
      return b == n || index(text, "[[" n "]]") || index(text, "[[" n "|") || index(text, "[[" n "#")
    }
    {
      path = $1; line = $2; state = $3; due = $4; waiting = $5; someday = $6; closed = $8; day = $10; start = $12; text = $13
      # A task is hidden until its start date, and a someday task is not an ordinary one until its start date comes.
      hidden = (start != "" && start > today)
      some = (someday == 1 && !(start != "" && start <= today))
      label = ""
      if (view == "done") { if (state != "done" || closed < since) next }
      else if (state != "open" && state != "question") next
      if (forwho != "" && !((path ":" line) in mine)) next
      if (view == "someday") { if (!some) next }
      else if (view != "done") {
        if (some) next
        if (hidden) { if (all != "yes") next; label = "starts " start }
      }
      if (view == "waiting" && waiting == "") next
      if (!about(text, path)) next
      if (cutoff != "" && (day == "" || day >= cutoff)) next
      if (view == "done") { g = 4; k2 = closed; k3 = "" }
      else if (hidden) { g = 5; k2 = start; k3 = day }
      else if (due != "" && due < today) { g = 1; k2 = due; k3 = day }
      else if (due != "" && due <= soon_end) { g = 2; k2 = due; k3 = day }
      else if (waiting != "" && waiting != "?" && waiting < waited_cut) { g = 3; k2 = waiting; k3 = day }
      else { g = 4; k2 = (due == "" ? "9999-99-99" : due); k3 = (day == "" ? "0000-00-00" : day) }
      print g, k2, k3, $0, label
    }
  ' "$tmp/tasks-for" "$tmp/tasks-all" | LC_ALL=C sort -t "$US" -k1,1n -k2,2 -k3,3 -k4,4 -k5,5n > "$tmp/tasks-sorted"
  # The meta file gives --json what the plain listing leaves out: path, line, group, due and state.
  awk -F "$US" -v OFS="$US" -v view="$view" '
    {
      name = (view == "done") ? "done" : ($1 == 1 ? "overdue" : ($1 == 2 ? "due_soon" : ($1 == 3 ? "waiting_long" : "other")))
      print $4, $5, name, $7, $6
    }
  ' "$tmp/tasks-sorted" > "$tmp/task-meta"
  # Each sorted record is: group, key, key, then the task's own fields. The plain line is path:line: text.
  awk -F "$US" '{ print $4 ":" $5 ": " ($17 != "" ? $17 ": " : "") $16 }' "$tmp/tasks-sorted"
}
