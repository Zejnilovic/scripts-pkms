# shellcheck shell=bash
# lib/pkm/cmd/day.sh: pkm day: the page for a day, created when missing. --edit opens it in $EDITOR.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_day() {
  local date=$today edit=no path
  while [ $# -gt 0 ]; do
    case $1 in
      --edit) edit=yes; shift ;;
      *) is_date "$1" || die 2 "The date must look like YYYY-MM-DD, got: $1"; date=$1; shift ;;
    esac
  done
  path=$(day_ensure "$date") || exit $?
  echo "$path"
  if [ "$edit" = yes ]; then "${EDITOR:-vi}" "$path"; fi
}
