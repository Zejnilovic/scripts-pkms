# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/get.sh: pkm get <name>[#Section] [--lines a-b]: a note's text, or one section of it, between the header
# "<<<note <path> lines a-b" and the footer ">>>end". The name resolves as pkm path does. A section runs from its heading
# to the next heading of the same or a higher level, without its trailing blank lines. --lines takes the note's own line
# numbers and narrows what is printed. --plain prints the text as someone outside the vault reads it (get_plain), with no
# header or footer. Exit 1 when the note, the section or those lines are missing. Sourced by bin/pkm.

cmd_get() {
  local arg="" range="" name section="" path bounds first last total a b lo hi plain=no
  local usage="Usage: pkm get <name>[#Section] [--lines a-b] [--plain]"
  while [ $# -gt 0 ]; do
    case $1 in
      --lines) [ $# -ge 2 ] || die 2 "--lines needs a-b, the note's line numbers, such as 10-14"; range=$2; shift 2 ;;
      --plain) plain=yes; shift ;;
      *) [ -z "$arg" ] || die 2 "$usage"; arg=$1; shift ;;
    esac
  done
  [ -n "$arg" ] || die 2 "$usage"
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
  if [ "$plain" = yes ]; then get_plain "$path" "$lo" "$hi"; return 0; fi
  printf '<<<note %s lines %s-%s\n' "$path" "$lo" "$hi"
  sed -n "${lo},${hi}p" "$path" | tr -d '\r'
  echo ">>>end"
}

# get_plain <path> <first> <last>: those lines as someone outside the vault reads them (plain.sh): each link as its shown
# text, or the title of the note it names; without the links to the day pages the lines came from, the markers and a 📅
# date. The frontmatter, with the blank lines after it, and struck lines (no longer true) are left out. Lines in code are printed as they are.
get_plain() {
  sed -n "${2},${3}p" "$1" | tr -d '\r' > "$tmp/get-lines"
  plain_titles "$tmp/get-lines" "$tmp/get-titles"
  vault_writers
  awk -v first="$2" "$(awk_markers)$(awk_plain)"'
    FILENAME == ARGV[1] { split($0, f, "\t"); PLAIN_TITLE[f[1]] = f[2]; next }
    FNR == 1 && first == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") { front = 0; lead = 1 } next }
    lead && $0 == "" { next }
    { lead = 0 }
    /^[ \t]*(```|~~~)/ { fence = !fence; print; next }
    fence { print; next }
    {
      t = $0
      gsub(/ *\(\[\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][^]]*\]\]\)/, "", t)
      s = t; sub(/^[ \t]*([-*+] )?(\[.\] )?/, "", s)
      if (s ~ /^~~.*~~[ \t]*$/) next
      t = plain_links(plain_unmark(t)); sub(/[ \t]+$/, "", t)
      print t
    }
  ' "$tmp/get-titles" "$tmp/get-lines"
}
