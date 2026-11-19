# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/todo.sh: pkm todo: a task for today, written under the Tasks section of today's page; prints path:line.
# Sourced by bin/pkm. Defines functions only.

cmd_todo() {
  local text="" due="" priority="" kind="" start="" rule="" into="" markers page loc type
  local usage_todo="Usage: pkm todo <text> [--due <day>] [--high | --low] [--waiting | --someday | --start <day> | --every <N>d|w|m|y or cycle [--in <note>]]"
  local days_help="use YYYY-MM-DD, today, tomorrow, +3d, +2w or a weekday"
  while [ $# -gt 0 ]; do
    case $1 in
      --due) { [ $# -ge 2 ] && due=$(parse_day "$2"); } || die 2 "Not a day: ${2:-} ($days_help)"; shift 2 ;;
      --high|--low) priority=${1#--}; shift ;;
      --in) [ $# -ge 2 ] && [ -n "$2" ] || die 2 "--in needs a note's name"; into=$2; shift 2 ;;
      --waiting|--someday|--start|--every)
        [ -z "$kind" ] || die 2 "A task is only one of --waiting, --someday, --start and --every."
        kind=${1#--}
        case $kind in
          start) { [ $# -ge 2 ] && start=$(parse_day "$2"); } || die 2 "Not a day: ${2:-} ($days_help)"; shift ;;
          every)
            # A routine is an interval (1d, 1w, 1m, 1y) or a cycle from the settings (week is built in). Routines live in
            # notes, so todo writes one only as a task for today's page's Tasks section, as any other task.
            rule=$(lowercase "${2:-}")
            if ! printf '%s\n' "$rule" | grep -Eq '^[0-9]+[dwmy]$' && ! cycle_known "$rule"; then
              die 2 "Not a routine: ${2:-} (use <N>d, <N>w, <N>m or <N>y, such as 1w, or a cycle name from the settings)"
            fi
            shift ;;
        esac
        shift ;;
      *) text="${text:+$text }$1"; shift ;;
    esac
  done
  [ -n "$text" ] || die 2 "$usage_todo"
  [ -z "$into" ] || [ "$kind" = every ] || die 2 "--in is for a routine: give it --every too, such as --every 1y --in $into"
  markers=""
  [ -z "$due" ] || markers="$markers (due $due)"
  [ -z "$priority" ] || markers="$markers ($priority)"
  case $kind in
    waiting) markers="$markers (waiting $today)" ;;
    someday) markers="$markers (someday)" ;;
    start) markers="$markers (start $start)" ;;
    every) markers="$markers (every $rule)" ;;
  esac
  if [ "$kind" = every ]; then
    # A routine lives in a note, so it goes to the note named routines (made when missing), not to today's page.
    index_ensure
    if [ -n "$into" ]; then
      # --in puts the routine with what it is about, at the end of the note's Routines section (made when missing).
      page=$(resolve_note "$into")
      [ -n "$page" ] || die 1 "No note named $into: make it with pkm new area \"$into\", or name another."
      type=$(note_type "$page")
      case $type in day|close) die 1 "$page is a $type page, and a page is a record: a routine lives in a note." ;; esac
      loc=$(section_add "$page" Routines "- [ ] $text$markers" no) || exit $?
      echo "$page:$loc"
      return 0
    fi
    page=$(resolve_note routines)
    [ -n "$page" ] || page=$(routines_note_create) || exit $?
    loc=$(append_task_line "$page" "- [ ] $text$markers") || exit $?
    echo "$page:$loc"
    return 0
  fi
  page=$(day_ensure "$today") || exit $?
  loc=$(section_add "$page" Tasks "- [ ] $text$markers" no) || exit $?
  echo "$page:$loc"
}

# routines_note_create: writes notes/routines.md from the note template, titled Routines, and prints its path. An existing
# file of that path that the name doesn't resolve to is not overwritten.
routines_note_create() {
  local path=notes/routines.md template
  template=$(template_file note.md)
  [ -f "$template" ] || die 2 "No note template: add $(template_file note.md), or reinstall pkm."
  [ ! -e "$path" ] || die 1 "$path exists, but the name routines doesn't find it: give that note the name routines."
  mkdir -p notes || die 1 "Can't make notes/."
  render "$template" Routines routines routines "$today" > "$tmp/routines-note" || die 1 "Can't render the note template."
  SUMMARY="summary: What comes back; when one is done, its date moves on" awk '
    /^summary:/ && !done { print ENVIRON["SUMMARY"]; done = 1; next }
    { print }
  ' "$tmp/routines-note" > "$tmp/routines-note.new"
  mv "$tmp/routines-note.new" "$path" || die 1 "Can't write $path."
  echo "$path"
}

# append_task_line <file> <line>: appends the line after the file's last non-blank line, with a blank line first when that
# line is a heading, in the file's own line ending. Prints the line's number.
append_task_line() {
  local file=$1 text=$2 eol last blank=no total
  eol=$(eol_of "$file")
  last=$(awk '{ if ($0 ~ /[^ \t\r]/) n = NR } END { print n + 0 }' "$file")
  if [ "$last" -gt 0 ] && sed -n "${last}p" "$file" | grep -qE '^#+[[:space:]]'; then blank=yes; fi
  {
    head -n "$last" "$file"
    if [ "$blank" = yes ]; then printf '%s\n' "$eol"; fi
    printf '%s%s\n' "$text" "$eol"
    tail -n +"$((last + 1))" "$file"
  } > "$tmp/todo-note"
  mv "$tmp/todo-note" "$file" || die 1 "Can't write $file."
  total=$((last + 1))
  if [ "$blank" = yes ]; then total=$((total + 1)); fi
  echo "$total"
}
