# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/rename.sh: pkm rename <old> <new>: renames a note and rewrites every link that names it, in day pages,
# notes and struck lines alike, outside code. The old name becomes an alias of the note unless --no-alias. Nothing is
# deleted. The changes are made as one transaction: every changed file is first written as a copy, the originals are
# copied aside, and the files are moved into place, the note last. A failure rolls back from the copies. Sourced by
# bin/pkm. Defines functions only.
# For tests only: PKM_RENAME_FAIL_AFTER=n makes the n-th move fail, to test the rollback.

cmd_rename() {
  local old="" new="" dry=no noalias=no tab rows count type oldpath newpath taken i f n
  local work moved=0 fail_after plan_self=""
  tab=$(printf '\t')
  while [ $# -gt 0 ]; do
    case $1 in
      --dry-run) dry=yes; shift ;;
      --no-alias) noalias=yes; shift ;;
      *) if [ -z "$old" ]; then old=${1%.md}; elif [ -z "$new" ]; then new=${1%.md}; else die 2 "Usage: pkm rename <old> <new> [--dry-run] [--no-alias]"; fi; shift ;;
    esac
  done
  [ -n "$old" ] && [ -n "$new" ] || die 2 "Usage: pkm rename <old> <new> [--dry-run] [--no-alias]"
  case $new in
    [A-Za-z0-9]*) case $new in *[!A-Za-z0-9._-]*) die 2 "A name has only letters, digits, '.', '_' and '-': $new" ;; esac ;;
    *) die 2 "A name starts with a letter or digit: $new" ;;
  esac
  [ "$old" != "$new" ] || die 2 "$old and $new are the same name."
  index_ensure
  rows=$(named_rows "$old")
  count=$(printf '%s' "$rows" | grep -c . || true)
  [ "$count" = 1 ] || die 1 "No single note is named $old."
  type=${rows%%"$tab"*}; oldpath=${rows#*"$tab"}
  old=$(basename "$oldpath" .md)
  case $type in
    day|close) die 1 "$oldpath is a $type page, named by its date, so it can't be renamed." ;;
  esac
  taken=$(awk -F "$tab" -v n="$new" '$1 == n { print $3; exit }' "$(cache_dir)/names.tsv")
  if [ -n "$taken" ]; then echo "$taken"; die 1 "$taken already uses the name $new, and names are unique in the vault."; fi
  case $oldpath in
    */*) newpath="${oldpath%/*}/$new.md" ;;
    *) newpath="$new.md" ;;
  esac
  refuse_existing "$newpath"
  work=".pkm/rename.$$"
  rm -rf "$work"; mkdir -p "$work/new" "$work/bak" || die 1 "Can't make $work."
  link_build ""
  awk -F "$tab" -v p="$oldpath" '$3 == p && $2 != "dead" { print $1 }' "$tmp/lb-resolved" | LC_ALL=C sort -u > "$work/texts"
  { awk -F "$tab" -v p="$oldpath" '$6 == p { print $1 }' "$tmp/lb-links"; echo "$oldpath"; } | LC_ALL=C sort -u > "$work/files"
  : > "$work/changes"; : > "$work/plan"
  i=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    i=$((i + 1))
    OLD=$old NEW=$new TEXTS="$work/texts" CHANGES="$work/changes" awk "$(awk_rename_links)" "$f" > "$work/new/$i" || die 1 "Can't rewrite $f."
    if [ "$f" = "$oldpath" ]; then
      plan_self=$i
      if [ "$noalias" = no ]; then
        OLD=$old FILE=$f EOL=$(eol_of "$f") CHANGES="$work/changes" awk "$(awk_rename_alias)" "$work/new/$i" > "$work/new/$i.alias" || die 1 "Can't add the alias to $f."
        mv "$work/new/$i.alias" "$work/new/$i"
      fi
    fi
    if ! cmp -s "$f" "$work/new/$i"; then printf '%s\t%s\n' "$i" "$f" >> "$work/plan"; fi
  done < "$work/files"
  if [ "$dry" = yes ]; then
    if [ -s "$work/changes" ]; then cat "$work/changes"; else echo "Nothing names $old in the vault, besides the note itself."; fi
    rm -rf "$work"
    return 0
  fi
  # The transaction. Each move is recorded in the undo log before the next one, and a failure undoes them in reverse.
  : > "$work/undo"
  fail_after=${PKM_RENAME_FAIL_AFTER:-0}
  rollback() {
    local kind a b
    awk '{ line[NR] = $0 } END { for (k = NR; k >= 1; k--) print line[k] }' "$work/undo" > "$work/undo-reversed"
    while IFS="$tab" read -r kind a b; do
      case $kind in
        A|C) mv "$work/bak/$a" "$b" ;;
        B) mv "$b" "$a" ;;
      esac
    done < "$work/undo-reversed"
    rm -rf "$work"
    die 1 "$1 Every file is as it was."
  }
  tick() {
    moved=$((moved + 1))
    if [ "$fail_after" -gt 0 ] && [ "$moved" -ge "$fail_after" ]; then rollback "A test asked for a failure after move $moved."; fi
  }
  n=0
  while IFS="$tab" read -r i f; do
    [ "$f" != "$oldpath" ] || continue
    cp "$f" "$work/bak/$i" || rollback "Can't copy $f aside."
    mv "$work/new/$i" "$f" || rollback "Can't write $f."
    printf 'A\t%s\t%s\n' "$i" "$f" >> "$work/undo"
    n=$((n + 1)); tick
  done < "$work/plan"
  cp "$oldpath" "$work/bak/note" || rollback "Can't copy $oldpath aside."
  mv "$oldpath" "$newpath" || rollback "Can't move $oldpath to $newpath."
  printf 'B\t%s\t%s\n' "$oldpath" "$newpath" >> "$work/undo"
  tick
  if [ -n "$plan_self" ] && [ -f "$work/new/$plan_self" ] && ! cmp -s "$work/bak/note" "$work/new/$plan_self"; then
    mv "$work/new/$plan_self" "$newpath" || rollback "Can't write $newpath."
    printf 'C\tnote\t%s\n' "$newpath" >> "$work/undo"
    tick
  fi
  rename_moves_append "$old" "$new" || rollback "Can't write the moves record."
  rm -rf "$work"
  echo "Renamed $old to $new: the note is now $newpath, and $n other file$( [ "$n" = 1 ] || echo s) changed."
}
