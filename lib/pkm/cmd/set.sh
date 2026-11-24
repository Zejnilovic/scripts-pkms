# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/set.sh: pkm set <note> <key=value> ...: sets frontmatter values of a note, so nobody edits the YAML by
# hand. A part_of must name a note. With part_of_folders=yes, a new part_of also moves the note into its parent's
# folder, as pkm mv does. Prints path:line: text of each written line. Sourced by bin/pkm. Defines functions only.

cmd_set() {
  local note tab path type pairs parent folder newpath name
  [ $# -ge 2 ] || die 2 "Usage: pkm set <note> <key=value> ..., such as pkm set apollo-web part_of=acme-portal"
  note=$1; shift
  pairs="$tmp/set-pairs"; : > "$pairs"
  for pair in "$@"; do fm_pair "$pair" "$pairs" set; done
  tab=$(printf '\t')
  path=$(fm_resolve "$note") || die 1 "No note is named $note."
  type=$(awk -F "$tab" -v p="$path" '$3 == p { print $2; exit }' "$(cache_dir)/names.tsv")
  case $type in
    day|close) die 1 "$path is a $type page, a record: its frontmatter stays as it is." ;;
  esac
  parent=$(fm_parent "$pairs" set) || exit $?
  [ "$parent" != "$path" ] || die 1 "pkm set: $note can't be part_of itself."
  fm_apply "$path" "$pairs" "$tmp/set-note" "$tmp/set-changes"
  mv "$tmp/set-note" "$path" || die 1 "Can't write $path."
  if fm_value "$pairs" type > /dev/null; then type=$(fm_value "$pairs" type); fi
  # With part_of_folders=yes, a note goes where its parent's notes go, unless its type has a folder of its own.
  if [ -n "$parent" ] && [ "$(config part_of_folders no)" = yes ] && [ -z "$(config "folder_$type" "")" ]; then
    case $path in archive/*) ;; *)
      folder=$(fm_folder_of "$parent"); name=$(basename "$path")
      newpath="$folder/$name"
      if [ "$newpath" != "$path" ]; then
        refuse_existing "$newpath"
        mkdir -p "$folder" || die 1 "Can't create $folder."
        mv "$path" "$newpath" || die 1 "Can't move $path to $newpath."
        rename_moves_append "$path" "$newpath" || die 1 "Can't write the moves record."
        path=$newpath
      fi ;;
    esac
  fi
  awk -F "$tab" -v p="$path" '{ print p ":" $1 ": " substr($0, length($1) + 2) }' "$tmp/set-changes"
}
