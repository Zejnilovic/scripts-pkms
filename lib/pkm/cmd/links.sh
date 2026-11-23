# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/links.sh: pkm links --external [note]: each http(s) address outside code, as path:line: address, in the
# order of every listing (by path, then line). An item, [[apollo-web]]#42, is listed by its address (links.sh), after
# the plain addresses of its line. A note limits the list to that note. Links to notes are backlinks.
# Sourced by bin/pkm. Defines functions only.

cmd_links() {
  local external=no note="" path
  while [ $# -gt 0 ]; do
    case $1 in
      --external) external=yes; shift ;;
      *) [ -z "$note" ] || die 2 "Usage: pkm links --external [note]"; note=$1; shift ;;
    esac
  done
  [ "$external" = yes ] || die 2 "pkm links lists web addresses: use links --external. For links to a note, use pkm backlinks <name>."
  index_ensure
  if [ -n "$note" ]; then
    path=$(note_for "$note")
    [ -n "$path" ] || die 1 "No note named $note."
    printf '%s\n' "$path" > "$tmp/links-list"
  else
    files yes '*.md' > "$tmp/links-list"
  fi
  {
    external_addresses "$tmp/links-list" | awk -F '\t' -v OFS='\t' '{ print $1, $2, 0, $3 }'
    item_addresses "$tmp/links-list" | awk -F '\t' -v OFS='\t' '$5 == "ok" { print $1, $2, 1, $6 }'
  } > "$tmp/links-found"
  # The listing order: the list's order of files, then the line, then the plain addresses before the items.
  awk -F '\t' -v OFS='\t' 'NR == FNR { order[$0] = NR; next } { print order[$1], $0 }' "$tmp/links-list" "$tmp/links-found" \
    | LC_ALL=C sort -s -t "$(printf '\t')" -k1,1n -k3,3n -k4,4n | awk -F '\t' '{ print $2 ":" $3 ": " $5 }'
}
