# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/done.sh: pkm done: marks the one open task that matches as done, or with --drop as dropped. A routine with
# an interval, such as (every 1m), keeps its box open and moves its due date on by one interval. With --next <day>, a
# routine done early or late is next due on that day, and moves on from there. Sourced by bin/pkm. Defines functions only.

cmd_done() {
  local mark=x word="done" ref line file due rule new old US record text explicit next=""
  local usage="Usage: pkm done <words of the task | path:line> [--drop | --next <day>]"
  US=$(printf '\037')
  while [ $# -gt 0 ]; do
    case $1 in
      --drop) mark="-"; word="dropped"; shift ;;
      --next)
        { [ $# -ge 2 ] && next=$(parse_day "$2") && [ -n "$next" ]; } \
          || die 2 "Not a day: ${2:-} (use YYYY-MM-DD, today, tomorrow, +3d, +2w or a weekday)"
        shift 2 ;;
      *) ref="${ref:+$ref }$1"; shift ;;
    esac
  done
  [ -n "$ref" ] || die 2 "$usage"
  [ -z "$next" ] || [ "$mark" = x ] || die 2 "--next moves a routine that is done, so it doesn't go with --drop."
  task_records no > "$tmp/done-records"
  case $ref in
    *.md:[0-9]*) REF=$ref awk -F "$US" -v OFS="$US" '$3 == "open" && ($1 ":" $2) == ENVIRON["REF"]' "$tmp/done-records" > "$tmp/done-matches" ;;
    *) REF=$ref awk -F "$US" 'BEGIN { want = tolower(ENVIRON["REF"]) } $3 == "open" && index(tolower($13), want)' \
         "$tmp/done-records" > "$tmp/done-matches" ;;
  esac
  local count
  count=$(wc -l < "$tmp/done-matches" | tr -d ' ')
  case $count in
    0) case $ref in *.md:[0-9]*) die 1 "$ref is not an open task." ;; *) die 1 "No open task matches '$ref'." ;; esac ;;
    1) ;;
    *) awk -F "$US" '{ print $1 ":" $2 ": " $13 }' "$tmp/done-matches" >&2
       die 1 "$count open tasks match '$ref': add words, or give the path:line." ;;
  esac
  record=$(cat "$tmp/done-matches")
  IFS=$US read -r file line _ due _ _ _ _ rule _ _ _ text <<EOF
$record
EOF
  # A due date written on the line is explicit. An undated cycle routine gets a due date from its period in the records,
  # which is not written on the line, so it is treated as undated.
  explicit=no
  case $text in *"(due "*|*"📅 "*) explicit=yes ;; esac
  if [ -n "$next" ] && [ -z "$rule" ]; then
    die 1 "$file:$line is not a routine, so it has no next time: to change its date, use pkm moved $file:$line <day>."
  fi
  if [ "$mark" = x ] && [ -n "$rule" ]; then
    local unit n base
    if [ -n "$next" ]; then
      new=$next
    elif printf '%s\n' "$rule" | grep -Eq '^[0-9]+[dwmy]$'; then
      # The due date moves on by one interval from the old due date (today, when there is none).
      base=$due; [ -n "$base" ] || base=$today
      unit=$(printf '%s' "$rule" | tail -c 1); n=${rule%?}
      case $unit in
        d) new=$(day_add "$base" "$n") ;;
        w) new=$(day_add "$base" "$((n * 7))") ;;
        m) new=$(day_add_months "$base" "$n") ;;
        y) new=$(day_add_months "$base" "$((n * 12))") ;;
      esac
    elif cycle_known "$rule"; then
      # A dated cycle routine moves on by its cycle's length: 7N days for Nw, N months for Nm (same day of the month, or
      # the month's last day). An undated one is due on the last day of the period holding today, and moves to the last
      # day of the next period.
      local cunit cn
      if [ "$explicit" = yes ]; then
        read -r cunit cn _ _ <<EOF
$(cycle_spec "$rule")
EOF
        case $cunit in
          w) new=$(day_add "$due" "$((cn * 7))") ;;
          m) new=$(month_add "$due" "$cn") ;;
        esac
      else
        new=$(cycle_period_last "$rule" "$(day_add "$(cycle_routine_due "$rule")" 1)")
      fi
    else
      die 1 "$file:$line has (every $rule), which pkm can't move on: use an interval such as (every 1m), or a cycle name from .pkm/config."
    fi
    is_date "$new" || die 2 "Can't move the due date of $file:$line."
    old=$due; [ "$explicit" = yes ] || old=""
    OLD=$old NEW=$new LINE=$line awk '
      FNR == ENVIRON["LINE"] + 0 {
        eol = ""; if ($0 ~ /\r$/) { sub(/\r$/, ""); eol = "\r" }
        if (ENVIRON["OLD"] != "") {
          old = "(due " ENVIRON["OLD"] ")"; i = index($0, old)
          if (i) $0 = substr($0, 1, i - 1) "(due " ENVIRON["NEW"] ")" substr($0, i + length(old))
          else $0 = $0 " (due " ENVIRON["NEW"] ")"
        } else {
          sub(/[ \t]+$/, "")
          i = index($0, "(every ")
          if (i) $0 = substr($0, 1, i - 1) "(due " ENVIRON["NEW"] ") " substr($0, i)
          else $0 = $0 " (due " ENVIRON["NEW"] ")"
        }
        $0 = $0 eol
      }
      { print }
    ' "$file" > "$tmp/done-file" && cat "$tmp/done-file" > "$file"
  else
    MARK=$mark WORD=$word TODAY=$today LINE=$line awk '
      FNR == ENVIRON["LINE"] + 0 {
        eol = ""; if ($0 ~ /\r$/) { sub(/\r$/, ""); eol = "\r" }
        sub(/- \[ \] /, "- [" ENVIRON["MARK"] "] "); sub(/[ \t]+$/, ""); $0 = $0 " (" ENVIRON["WORD"] " " ENVIRON["TODAY"] ")" eol
      }
      { print }
    ' "$file" > "$tmp/done-file" && cat "$tmp/done-file" > "$file"
  fi
  echo "$file:$line: $(sed -n "${line}p" "$file" | sed 's/^[[:space:]]*//' | tr -d '\r')"
}
