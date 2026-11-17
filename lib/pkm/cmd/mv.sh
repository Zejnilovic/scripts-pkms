# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/mv.sh: pkm mv <note> <folder>: moves a note into a folder, keeping its name. Links keep working: they name
# the note. The move is recorded in .pkm/moves.tsv. Sourced by bin/pkm. Defines functions only.

cmd_mv() {
  local name folder tab rows count type oldpath newpath
  tab=$(printf '\t')
  [ $# -eq 2 ] || die 2 "Usage: pkm mv <note> <folder>"
  folder=${2%/}
  case $folder in
    ''|/*|*..*) die 2 "The folder must be inside the vault: $2" ;;
  esac
  index_ensure
  rows=$(named_rows "$1")
  count=$(printf '%s' "$rows" | grep -c . || true)
  [ "$count" = 1 ] || die 1 "No single note is named $1."
  type=${rows%%"$tab"*}; oldpath=${rows#*"$tab"}
  name=$(basename "$oldpath" .md)
  case $type in
    day|close) die 1 "$oldpath is a $type page, named by its date, so it stays where it is." ;;
  esac
  newpath="$folder/$name.md"
  [ "$newpath" != "$oldpath" ] || die 1 "$oldpath is already there."
  refuse_existing "$newpath"
  mkdir -p "$folder" || die 1 "Can't create $folder."
  mv "$oldpath" "$newpath" || die 1 "Can't move $oldpath to $newpath."
  rename_moves_append "$oldpath" "$newpath" || die 1 "Can't write the moves record."
  echo "$newpath"
}
