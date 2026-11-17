# shellcheck shell=bash
# lib/pkm/cmd/templates.sh: pkm templates: each template type, where its template comes from, and eject, which copies
# a default template to the vault or the user's folder so it can be changed. Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# templates_in <folder>: the template types in a folder, one per line.
templates_in() {
  local f
  for f in "$1"/*.md; do
    [ -f "$f" ] || continue
    f=${f##*/}
    echo "${f%.md}"
  done
}

templates_eject() {
  local type="" to_user=no dest_dir dest source
  for arg in "$@"; do
    case $arg in
      --user) to_user=yes ;;
      *) [ -z "$type" ] || die 2 "Usage: pkm templates eject <type> [--user]"; type=$arg ;;
    esac
  done
  [ -n "$type" ] || die 2 "Usage: pkm templates eject <type> [--user]"
  case $type in
    *[!A-Za-z0-9_-]*) die 2 "A type has letters, digits, '-' and '_' only, got: $type" ;;
  esac
  source="$pkm_home/share/pkm/templates/$type.md"
  [ -f "$source" ] || die 2 "pkm ships no default template for $type. Make one in the vault's templates folder."
  if [ "$to_user" = yes ]; then dest_dir=$(user_templates_dir); else dest_dir=$(config templates templates); fi
  dest="$dest_dir/$type.md"
  [ ! -e "$dest" ] || die 1 "$dest already exists, so it was not overwritten."
  { mkdir -p "$dest_dir" && cp "$source" "$dest"; } || die 2 "Can't write $dest"
  echo "$dest"
}

cmd_templates() {
  local folder types type source
  case ${1:-} in
    eject) shift; templates_eject "$@"; return ;;
    '') ;;
    *) die 2 "Usage: pkm templates [eject <type> [--user]]" ;;
  esac
  folder=$(config templates templates)
  types=$({ templates_in "$folder"; templates_in "$(user_templates_dir)"; templates_in "$pkm_home/share/pkm/templates"; } | LC_ALL=C sort -u)
  for type in $types; do
    if [ -f "$folder/$type.md" ]; then source=vault
    elif [ -f "$(user_templates_dir)/$type.md" ]; then source=user
    else source=default; fi
    printf '%s\t%s\n' "$type" "$source"
  done
}
