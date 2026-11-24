# shellcheck shell=bash
# lib/pkm/cmd/new.sh: pkm new: a note of a type, made from its template, in notes/ or the type's folder.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_new() {
  local type="" title="" name="" slug folder="" template retype="" taken address="" repo parent pairs
  pairs="$tmp/new-pairs"; : > "$pairs"
  while [ $# -gt 0 ]; do
    case $1 in
      --name) [ $# -ge 2 ] || die 2 "--name needs a value"; name=$2; shift 2 ;;
      --folder) [ $# -ge 2 ] || die 2 "--folder needs a folder"; folder=${2%/}; fm_folder_ok "$folder" new; shift 2 ;;
      --url) [ $# -ge 2 ] || die 2 "--url needs an address"; address=$2; shift 2 ;;
      --set) [ $# -ge 2 ] || die 2 "--set needs key=value"; fm_pair "$2" "$tmp/new-set" new; shift 2 ;;
      *) if [ -z "$type" ]; then type=$1; elif [ -z "$title" ]; then title=$1; else title="$title $1"; fi; shift ;;
    esac
  done
  # --url fills url, and for a repository also items and, without a title, the title: the repository's name.
  if [ -n "$address" ]; then
    if [ "$type" = repo ]; then
      repo=$(fm_repo "$address") || die 2 "pkm new: $address is not a repository address, such as https://github.com/acme-example/apollo-web or acme-example/apollo-web"
      printf 'url\t%s\nitems\t%s\n' "$(printf '%s' "$repo" | cut -f2)" "$(printf '%s' "$repo" | cut -f3)" > "$pairs"
      [ -n "$title" ] || title=$(printf '%s' "$repo" | cut -f1)
    else
      fm_pair "url=$address" "$pairs" new
    fi
  fi
  if [ -f "$tmp/new-set" ]; then
    if fm_value "$tmp/new-set" type > /dev/null; then die 2 "pkm new: the type is the first word, not --set type=: pkm new <type> <title>"; fi
    cat "$tmp/new-set" >> "$pairs"
  fi
  # On a terminal, a missing type is picked from the templates, and a missing title is asked for (ask.sh). Day and close
  # pages have their own commands, so they are not in the list.
  if [ -z "$type" ]; then
    need_answer "Usage: pkm new <type> <title> [--name <name>] [--folder <folder>] [--url <address>] [--set key=value ...]"
    (cmd_templates) 2>/dev/null | awk -F '\t' -v OFS='\t' '$1 != "day" && $1 != "close" { print $1, $1 }' > "$tmp/new-types"
    pick_one Type "$tmp/new-types" "No templates: pkm templates lists where they come from."
    type=$answer
  fi
  if [ -z "$title" ]; then
    need_answer "Usage: pkm new $type <title> [--name <name>] [--folder <folder>] [--url <address>] [--set key=value ...]"
    ask_text "Title of the new $type: "
    title=$answer
  fi
  [ "$type" != day ] || die 2 "pkm day makes the day's page; new makes notes of the other types."
  parent=$(fm_parent "$pairs" new) || exit $?
  # The folder: --folder, else the type's own folder setting, else (part_of_folders=yes) the folder of its parent.
  if [ -z "$folder" ]; then folder=$(config "folder_$type" "")
    if [ -z "$folder" ]; then
      folder=notes
      if [ -n "$parent" ] && [ "$(config part_of_folders no)" = yes ]; then folder=$(fm_folder_of "$parent"); fi
    fi
  fi
  template=$(template_file "$type.md")
  if [ ! -f "$template" ]; then
    # A type with no template of its own is made from the note template, with its type: set to this type.
    template=$(template_file note.md)
    retype=$type
  fi
  [ -f "$template" ] || die 2 "No template for $type, and no note template to make it from: add $(template_file note.md)."
  slug=$(slugify "$title")
  if [ -z "$name" ]; then
    [ -n "$slug" ] || die 2 "No file name in '$title': give one with --name"
    # A letter with no Latin form (日本語) is dropped by the slug, which would name the note after the rest of the title.
    if printf '%s' "$title" | LC_ALL=C sed "$translit" | LC_ALL=C grep -q '[^ -~]'; then
      die 2 "The file name from '$title' drops letters it can't spell in Latin letters, so give one with --name, such as --name <name>"
    fi
    name=$slug
    if [ "$type" = coaching ]; then name="$slug-coaching"; fi
  fi
  case $name in
    [A-Za-z0-9]*) case $name in *[!A-Za-z0-9._-]*) die 2 "A name has only letters, digits, '.', '_' and '-': $name" ;; esac ;;
    *) die 2 "A name starts with a letter or digit: $name" ;;
  esac
  taken=$(files yes "$name.md" | head -n 1)
  if [ -n "$taken" ]; then
    echo "$taken"
    die 1 "$taken already uses the name $name, and names are unique in the vault. Name the new one by what tells them apart, for example: pkm new $type \"$title\" --name $name-<word>"
  fi
  render "$template" "$title" "$slug" "$name" "$today" > "$tmp/note"
  # The title becomes an alias when it differs from the name, so the words you wrote still find the note, unless a link
  # with those words already reaches another note: then the alias would only hide which one is meant.
  aliases="[]"
  if [ "$title" != "$name" ] && ! fm_resolve "$title" > /dev/null; then aliases="[$title]"; fi
  ALIASES=$aliases TYPE=$retype awk '
    /^aliases:/ && !aliased { print "aliases: " ENVIRON["ALIASES"]; aliased = 1; next }
    ENVIRON["TYPE"] != "" && /^type:/ && !typed { print "type: " ENVIRON["TYPE"]; typed = 1; next }
    { print }
  ' "$tmp/note" > "$tmp/note.new" && mv "$tmp/note.new" "$tmp/note"
  if [ -s "$pairs" ]; then fm_apply "$tmp/note" "$pairs" "$tmp/note.new" "$tmp/new-changes" && mv "$tmp/note.new" "$tmp/note"; fi
  refuse_existing "$folder/$name.md"
  mkdir -p "$folder" && mv "$tmp/note" "$folder/$name.md"
  echo "$folder/$name.md"
}
