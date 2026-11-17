# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/index.sh: pkm index: brings the cache up to date and says what changed. --rebuild starts it again. The cache
# is only a speed-up: deleting it never changes an answer. Sourced by bin/pkm. Defines functions only.

cmd_index() {
  local rebuild=no
  while [ $# -gt 0 ]; do
    case $1 in
      --rebuild) rebuild=yes; shift ;;
      *) die 2 "Usage: pkm index [--rebuild]" ;;
    esac
  done
  index_update "$rebuild" yes
}
