# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/cycle.sh: pkm cycle [name] [--date D]: the period holding the date (today by default), as
# name<TAB>first<TAB>last, and a fourth field "close" on the close cycle. With no name, every cycle. Sourced by bin/pkm.

cmd_cycle() {
  local name="" date=$today close line n
  while [ $# -gt 0 ]; do
    case $1 in
      --date) [ $# -ge 2 ] || die 2 "--date needs a day, YYYY-MM-DD"; is_date "$2" || die 2 "--date needs a day, YYYY-MM-DD, got: $2"; date=$2; shift 2 ;;
      *) [ -z "$name" ] || die 2 "Usage: pkm cycle [name] [--date YYYY-MM-DD]"; name=$1; shift ;;
    esac
  done
  close=$(config close week)
  if [ -n "$name" ]; then
    cycle_known "$name" || die 1 "No cycle named $name: add cycle_$name to .pkm/config, or see pkm config."
    line=$(cycle_period "$name" "$date") || die 1 "No cycle named $name."
    printf '%s\t%s' "$name" "$line" | tr ' ' '\t'
    [ "$name" = "$close" ] && printf '\tclose'
    printf '\n'
    return 0
  fi
  for n in week $(cycle_names); do
    line=$(cycle_period "$n" "$date") || continue
    printf '%s\t%s' "$n" "$line" | tr ' ' '\t'
    [ "$n" = "$close" ] && printf '\tclose'
    printf '\n'
  done
}
