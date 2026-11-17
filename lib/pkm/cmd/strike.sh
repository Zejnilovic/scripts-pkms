# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/strike.sh: pkm strike <path:line>: strikes a line through, when it is no longer true. The text after the
# list marker and the task box is wrapped in ~~, and " ([[<today's page>]])" is added, so the link is never dead: today's
# page is made when it is missing. Refuses (exit 1) a blank line, a heading and a line already struck. A malformed
# argument, a file outside the vault, or a line out of range exits 2. Prints path:line. Sourced by bin/pkm.

cmd_strike() {
  [ $# -eq 1 ] || die 2 "Usage: pkm strike <path:line>"
  local spec=$1 path ln total line parts prefix rest day dayname new US cr eol
  case $spec in
    *:*) path=${spec%:*}; ln=${spec##*:} ;;
    *) die 2 "Usage: pkm strike <path:line>, such as daybook/2026/11/2026-11-12.md:7" ;;
  esac
  case $ln in ''|*[!0-9]*) die 2 "A line is a whole number: $spec" ;; esac
  case $path in
    /*|../*|*/../*) die 2 "$path is outside the vault." ;;
  esac
  [ -f "$path" ] || die 2 "No file $path in the vault."
  total=$(awk 'END { print NR }' "$path")
  [ "$ln" -ge 1 ] && [ "$ln" -le "$total" ] || die 2 "Line $ln is outside $path, which has $total lines."
  line=$(sed -n "${ln}p" "$path")
  cr=$(printf '\r'); eol=""
  case $line in *"$cr") eol=$cr; line=${line%"$cr"} ;; esac
  printf '%s' "$line" | grep -q '[^[:space:]]' || die 1 "Line $ln of $path is blank: there is nothing to strike."
  printf '%s' "$line" | grep -qE '^#+[[:space:]]' && die 1 "Line $ln of $path is a heading: strike the lines under it."
  US=$(printf '\037')
  parts=$(printf '%s\n' "$line" | awk -v US="$US" '{
    s = $0
    if (match(s, /^[ \t]*([-*+]|[0-9]+[.)])[ \t]+(\[.\][ \t]+)?/)) { p = substr(s, 1, RLENGTH); r = substr(s, RLENGTH + 1) }
    else { match(s, /^[ \t]*/); p = substr(s, 1, RLENGTH); r = substr(s, RLENGTH + 1) }
    sub(/[ \t]+$/, "", r)
    printf "%s%s%s", p, US, r
  }')
  prefix=${parts%%"$US"*}
  rest=${parts#*"$US"}
  case $rest in
    '') die 1 "Line $ln of $path has no text after its marker: there is nothing to strike." ;;
    '~~'*) die 1 "Line $ln of $path is struck already." ;;
  esac
  day=$(day_ensure "$today") || exit $?
  dayname=$(basename "$day" .md)
  new="$prefix~~$rest~~ ([[$dayname]])$eol"
  NEW=$new awk -v ln="$ln" '{ if (NR == ln) print ENVIRON["NEW"]; else print }' "$path" > "$tmp/strike-page"
  mv "$tmp/strike-page" "$path" || die 1 "Can't write $path."
  echo "$path:$ln"
}
