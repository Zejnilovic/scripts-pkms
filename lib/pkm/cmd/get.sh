# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/get.sh: pkm get <name>[#Section] [--lines a-b]: a note's text, or one section of it, between the header
# "<<<note <path> lines a-b" and the footer ">>>end". The name resolves as pkm path does. A section runs from its heading
# to the next heading of the same or a higher level, without its trailing blank lines. --lines takes the note's own line
# numbers and narrows what is printed. Exit 1 when the note, the section or those lines are missing. Sourced by bin/pkm.

cmd_get() {
  local arg="" range="" name section="" path bounds first last total a b lo hi
  while [ $# -gt 0 ]; do
    case $1 in
      --lines) [ $# -ge 2 ] || die 2 "--lines needs a-b, the note's line numbers, such as 10-14"; range=$2; shift 2 ;;
      *) [ -z "$arg" ] || die 2 "Usage: pkm get <name>[#Section] [--lines a-b]"; arg=$1; shift ;;
    esac
  done
  [ -n "$arg" ] || die 2 "Usage: pkm get <name>[#Section] [--lines a-b]"
  # A whole link works too, as path accepts it: [[apollo#Decisions|text]] names apollo's Decisions section.
  case $arg in
    '[['*) arg=${arg#\[\[}; arg=${arg%\]\]} ;;
  esac
  arg=${arg%%|*}
  name=${arg%%#*}
  case $arg in
    *'#'*) section=${arg#*#}; [ -n "$section" ] || die 2 "Usage: pkm get <name>#Section: the section name is missing" ;;
  esac
  index_ensure
  path=$(note_for "$name")
  [ -n "$path" ] || die 1 "No note named $name."
  total=$(awk 'END { print NR }' "$path")
  first=1; last=$total
  if [ -n "$section" ]; then
    bounds=$(section_bounds "$path" "$section")
    [ -n "$bounds" ] || die 1 "No section $section in $path."
    first=${bounds%% *}; last=${bounds##* }
  fi
  lo=$first; hi=$last
  if [ -n "$range" ]; then
    case $range in
      [0-9]*-[0-9]*) ;;
      *) die 2 "--lines takes a-b, such as 10-14, got: $range" ;;
    esac
    a=${range%-*}; b=${range#*-}
    [ "$a" -ge 1 ] 2>/dev/null && [ "$a" -le "$b" ] && [ "$a" -le "$total" ] \
      || die 2 "--lines $range is outside $path, which has $total lines."
    # An end past the last line is clamped to it: the lines that exist are printed.
    [ "$b" -gt "$total" ] && b=$total
    [ "$a" -gt "$lo" ] && lo=$a
    [ "$b" -lt "$hi" ] && hi=$b
    [ "$lo" -le "$hi" ] || die 1 "No lines $range in ${section:-$path}: they are outside it."
  fi
  printf '<<<note %s lines %s-%s\n' "$path" "$lo" "$hi"
  sed -n "${lo},${hi}p" "$path" | tr -d '\r'
  echo ">>>end"
}
