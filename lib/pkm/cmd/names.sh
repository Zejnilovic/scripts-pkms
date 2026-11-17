# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/names.sh: pkm names: every note's name, type, path and aliases, by name, from the cache. Day and close
# pages, and files other than notes, are left out unless --type says them: names --type person lists the people.
# Sourced by bin/pkm. Defines functions only.

cmd_names() {
  local type="" tab
  tab=$(printf '\t')
  while [ $# -gt 0 ]; do
    case $1 in
      --type) [ $# -ge 2 ] || die 2 "--type needs a type"; type=$2; shift 2 ;;
      *) die 2 "Usage: pkm names [--type <type>]" ;;
    esac
  done
  index_ensure
  TYPE=$type awk -F "$tab" -v OFS="$tab" '
    { if (ENVIRON["TYPE"] != "") { if ($2 != ENVIRON["TYPE"]) next }
      else if ($2 == "day" || $2 == "close" || $2 == "attachment") next
      print $1, $2, $3, $4 }
  ' "$(cache_dir)/names.tsv"
}
