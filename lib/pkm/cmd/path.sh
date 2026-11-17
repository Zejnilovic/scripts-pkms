# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/path.sh: pkm path: the file a name, slug, alias or link points to. It reads the cache's names only.
# Sourced by bin/pkm. Defines functions only.

cmd_path() {
  [ $# -eq 1 ] || die 2 "Usage: pkm path <name>"
  # Accepts a bare name or a whole link, such as [[apollo|the portal]] or [[apollo#Risks]].
  local name=$1 found
  name=${name#\!}; name=${name#[[}; name=${name%]]}; name=${name%%|*}; name=${name%%#*}; name=${name##*/}
  printf '%s\n' "$name" > "$tmp/path-target"
  link_index "$tmp/path-index"
  link_slugs "$tmp/path-target" "$tmp/path-slugs"
  link_resolve "$tmp/path-index" "$tmp/path-slugs" "$tmp/path-resolved"
  found=$(awk -F '\t' -v t="$name" '$1 == t && $2 != "dead" { print $3; exit }' "$tmp/path-resolved")
  [ -n "$found" ] || die 1 "No note or attachment named $name."
  echo "$found"
}
