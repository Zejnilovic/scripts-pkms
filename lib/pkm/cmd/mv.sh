# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/mv.sh: pkm mv <note> ... <folder>: moves notes into a folder, each keeping its name. Links keep working: they name
# the note. The move is recorded in .pkm/moves.tsv. Sourced by bin/pkm. Defines functions only.

cmd_mv() {
  local name folder tab rows count type oldpath newpath note
  tab=$(printf '\t')
  [ $# -ge 2 ] || die 2 "Usage: pkm mv <note> ... <folder>"
  folder=${!#}
  folder=${folder%/}
  case $folder in
    ''|/*|*..*) die 2 "The folder must be inside the vault: $folder" ;;
  esac
  index_ensure
  # Every note is checked before any moves, so one that can't move leaves them all where they are.
  : > "$tmp/mv-plan"
  while [ $# -gt 1 ]; do
    note=$1; shift
    rows=$(named_rows "$note")
    count=$(printf '%s' "$rows" | grep -c . || true)
    [ "$count" = 1 ] || die 1 "No single note is named $note."
    type=${rows%%"$tab"*}; oldpath=${rows#*"$tab"}
    name=$(basename "$oldpath" .md)
    case $type in
      day|close) die 1 "$oldpath is a $type page, named by its date, so it stays where it is." ;;
    esac
    newpath="$folder/$name.md"
    [ "$newpath" != "$oldpath" ] || die 1 "$oldpath is already there."
    refuse_existing "$newpath"
    if cut -f2 "$tmp/mv-plan" | grep -qxF -- "$newpath"; then die 1 "$note is named twice."; fi
    printf '%s\t%s\n' "$oldpath" "$newpath" >> "$tmp/mv-plan"
  done
  mkdir -p "$folder" || die 1 "Can't create $folder."
  while IFS="$tab" read -r oldpath newpath; do
    mv "$oldpath" "$newpath" || die 1 "Can't move $oldpath to $newpath."
    rename_moves_append "$oldpath" "$newpath" || die 1 "Can't write the moves record."
    echo "$newpath"
  done < "$tmp/mv-plan"
}
