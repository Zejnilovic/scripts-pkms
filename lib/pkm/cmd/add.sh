# shellcheck shell=bash
# lib/pkm/cmd/add.sh: pkm add: writes an entry at the end of a day's Log, as "- HH:MM text", and prints path:line.
# Text with several lines, or read from stdin with -, goes under a "### HH:MM" heading, verbatim.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_add() {
  local date=$today text="" from_stdin=no page line
  while [ $# -gt 0 ]; do
    case $1 in
      --day) { [ $# -ge 2 ] && is_date "$2"; } || die 2 "--day needs a date YYYY-MM-DD"; date=$2; shift 2 ;;
      -) from_stdin=yes; shift ;;
      *) text="${text:+$text }$1"; shift ;;
    esac
  done
  if [ "$from_stdin" = yes ]; then cat > "$tmp/add-input"; else printf '%s\n' "$text" > "$tmp/add-input"; fi
  # Trailing blank lines are not part of the entry.
  awk '{ line[NR] = $0 } END { n = NR; while (n > 0 && line[n] ~ /^[ \t]*$/) n--; for (i = 1; i <= n; i++) print line[i] }' \
    "$tmp/add-input" > "$tmp/add-text"
  if ! grep -q '[^[:space:]]' "$tmp/add-text" 2>/dev/null; then die 2 "Nothing to add: give the text in quotes, or - to read it from stdin."; fi
  block=no
  if [ "$(wc -l < "$tmp/add-text" | tr -d ' ')" -gt 1 ]; then
    { printf '### %s\n\n' "$clock"; cat "$tmp/add-text"; } > "$tmp/add-lines"
    block=yes
  else
    printf -- '- %s %s\n' "$clock" "$(cat "$tmp/add-text")" > "$tmp/add-lines"
  fi
  page=$(day_ensure "$date") || exit $?
  line=$(log_add "$page" "$tmp/add-lines" "$block") || exit $?
  echo "$page:$line"
}
