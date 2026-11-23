# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/url.sh: pkm url: the address outside the vault that an item or a note points to (docs/format.md, Links 6).
# [[apollo-web]]#42, or apollo-web#42, is the note's items value and the number; a name or a link is the note's url value.
# The note resolves like any link. Only one http(s) address is printed: pkm never goes online, and an editor opens it.
# Sourced by bin/pkm. Defines functions only.

cmd_url() {
  local usage="Usage: pkm url <[[name]]#number | name>" ref name number="" key found value
  [ $# -eq 1 ] && [ -n "$1" ] || die 2 "$usage"
  ref=$1
  case $ref in
    *']]#'*) number=${ref##*]]#}; name=${ref%]]#*}; name=${name#\[\[} ;;
    '[['*']]') name=${ref#\[\[}; name=${name%\]\]} ;;
    *'#'*) number=${ref##*#}; name=${ref%#*} ;;
    *) name=$ref ;;
  esac
  case $ref in
    *'#'*) case $number in ''|*[!0-9]*) die 2 "$ref is not an item: an item is a link and a number, such as [[apollo-web]]#42." ;; esac ;;
  esac
  name=${name%%|*}; name=${name%\\}; name=${name##*/}
  case $name in
    *'#'*|*'^'*) die 2 "$ref is not an item: a link with a section or a block has no items." ;;
  esac
  [ -n "$name" ] || die 2 "$usage"
  printf '%s\n' "$name" > "$tmp/url-target"
  link_index "$tmp/url-index"
  link_slugs "$tmp/url-target" "$tmp/url-slugs"
  link_resolve "$tmp/url-index" "$tmp/url-slugs" "$tmp/url-resolved"
  found=$(awk -F '\t' '$2 != "dead" { print $3; exit }' "$tmp/url-resolved")
  [ -n "$found" ] || die 1 "No note named $name."
  if [ -n "$number" ]; then key=items; else key=url; fi
  value=$(P=$found K=$key awk -F '\t' '$1 == ENVIRON["P"] && $2 == ENVIRON["K"] { print $3; exit }' "$(cache_dir)/fields.tsv")
  if [ -z "$value" ]; then
    if [ "$key" = items ]; then
      die 1 "$name has no items line: add one to its frontmatter, the start of its items' addresses, such as items: https://github.com/acme-example/apollo-web/issues/"
    fi
    die 1 "$name has no url line: add one to its frontmatter, such as url: https://github.com/acme-example/apollo-web"
  fi
  value=$(V=$value awk "BEGIN { print web_value(ENVIRON[\"V\"]) } $(awk_items_in)" < /dev/null)
  [ -n "$value" ] || die 1 "The $key line of $found is not one http:// or https:// address."
  printf '%s%s\n' "$value" "$number"
}
