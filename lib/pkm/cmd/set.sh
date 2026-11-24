# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/set.sh: pkm set <note> <key=value> ...: sets frontmatter values of a note, so nobody edits the YAML by
# hand. A part_of must name a note. With part_of_folders=yes, a new part_of also moves the note into its parent's
# folder, as pkm mv does, and the folder of the notes under it along with it. Prints path:line: text of each written
# line. Sourced by bin/pkm. Defines functions only.

cmd_set() {
  local note tab path type pairs parent folder newpath name oldtree newtree f
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
  if fm_value "$pairs" type > /dev/null; then type=$(fm_value "$pairs" type); fi
  # With part_of_folders=yes, a note goes where its parent's notes go, unless its type has a folder of its own, and
  # its own folder (the notes under it) goes along. Every place is checked before anything is written.
  newpath=$path
  : > "$tmp/set-moves"
  if [ -n "$parent" ] && [ "$(config part_of_folders no)" = yes ] && [ -z "$(config "folder_$type" "")" ]; then
    case $path in archive/*) ;; *)
      folder=$(fm_folder_of "$parent"); name=$(basename "$path")
      newpath="$folder/$name"
      if [ "$newpath" != "$path" ]; then
        refuse_existing "$newpath"
        printf '%s\t%s\n' "$path" "$newpath" >> "$tmp/set-moves"
        oldtree=${path%.md}; newtree=${newpath%.md}
        case $newtree/ in "$oldtree"/*) die 1 "pkm set: $note can't be part_of a note under it." ;; esac
        if [ -d "$oldtree" ]; then
          find "$oldtree" -type f | LC_ALL=C sort > "$tmp/set-tree"
          while IFS= read -r f; do
            refuse_existing "$newtree/${f#"$oldtree"/}"
            printf '%s\t%s\n' "$f" "$newtree/${f#"$oldtree"/}" >> "$tmp/set-moves"
          done < "$tmp/set-tree"
        fi
      fi ;;
    esac
  fi
  fm_apply "$path" "$pairs" "$tmp/set-note" "$tmp/set-changes"
  mv "$tmp/set-note" "$path" || die 1 "Can't write $path."
  while IFS="$tab" read -r f name; do
    mkdir -p "${name%/*}" || die 1 "Can't create ${name%/*}."
    mv "$f" "$name" || die 1 "Can't move $f to $name."
    case $f in *.md) rename_moves_append "$f" "$name" || die 1 "Can't write the moves record." ;; esac
  done < "$tmp/set-moves"
  # The old folder goes once it is empty; a folder that still holds something stays.
  if [ "$newpath" != "$path" ] && [ -d "${path%.md}" ]; then
    find "${path%.md}" -depth -type d -exec rmdir {} \; 2>/dev/null || true
  fi
  awk -F "$tab" -v p="$newpath" '{ print p ":" $1 ": " substr($0, length($1) + 2) }' "$tmp/set-changes"
}
