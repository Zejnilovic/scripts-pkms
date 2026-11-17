# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/recall.sh: pkm recall [note] lists the recall questions due today or earlier, oldest first, as path:line: text.
# pkm recall <path:line> yes|no rewrites only the mark: yes moves the interval one rung up the ladder, no goes back to 1 day,
# and the next question date is today plus the new interval. The line is printed as path:line: text. With nothing due, it
# exits 1 with one line on stderr saying when the next question is due. Sourced by bin/pkm.

# recall_rewrite <path:line> <yes|no>: rewrites the mark of one question, keeping the line ends of the file.
recall_rewrite() {
  local spec=$1 decision=$2 path ln total line cur new newdate cr
  case $spec in
    *:*) path=${spec%:*}; ln=${spec##*:} ;;
    *) die 2 "Usage: pkm recall <path:line> yes|no" ;;
  esac
  case $ln in ''|*[!0-9]*) die 2 "A line is a whole number: $spec" ;; esac
  case $path in
    /*|../*|*/../*) die 2 "$path is outside the vault." ;;
  esac
  [ -f "$path" ] || die 2 "No file $path in the vault."
  total=$(awk 'END { print NR }' "$path")
  [ "$ln" -ge 1 ] && [ "$ln" -le "$total" ] || die 2 "Line $ln is outside $path, which has $total lines."
  line=$(sed -n "${ln}p" "$path")
  cur=$(printf '%s\n' "$line" | awk "$(recall_awk)"'
    { c = $0; sub(/\r$/, "", c); gsub(/`[^`]*`/, "", c); if (recall_parse(recall_inner(c))) print RDAYS }')
  [ -n "$cur" ] || die 1 "$spec has no recall mark: a question ends with (recall YYYY-MM-DD <N>d), such as (recall 2026-11-16 7d)."
  new=$(recall_rung "$cur" "$decision")
  newdate=$(day_add "$today" "$new")
  NEWMARK="(recall $newdate ${new}d)" LN=$ln awk '
    NR == ENVIRON["LN"] + 0 {
      cr = ""; if ($0 ~ /\r$/) { sub(/\r$/, ""); cr = "\r" }
      sub(/\(recall [^)]*\)[ \t]*$/, ENVIRON["NEWMARK"]); $0 = $0 cr
    }
    { print }
  ' "$path" > "$tmp/recall-page"
  mv "$tmp/recall-page" "$path" || die 1 "Can't write $path."
  cr=$(printf '\r')
  line=$(sed -n "${ln}p" "$path")
  echo "$path:$ln: ${line%"$cr"}"
}

# recall_add <note> <question> [--answer <text>]...: writes the question at the end of the note's ## Questions section (made at
# the end of the note when missing), marked to be asked tomorrow, with each answer indented below it. Prints path:line of the
# question. Refuses a day or close page, a question the note already has, and a note that doesn't exist (exit 1).
recall_add() {
  local name question path ttype dup tomorrow loc
  local usage="Usage: pkm recall add <note> <question> [--answer <text>]..."
  [ $# -ge 2 ] || die 2 "$usage"
  name=$1; question=$2; shift 2
  : > "$tmp/recall-answers"
  while [ $# -gt 0 ]; do
    case $1 in
      --answer) [ $# -ge 2 ] || die 2 "--answer needs a text. $usage"; printf '  - %s\n' "$2" >> "$tmp/recall-answers"; shift 2 ;;
      *) die 2 "$usage" ;;
    esac
  done
  question=$(printf '%s' "$question" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')
  [ -n "$question" ] || die 2 "The question is empty. $usage"
  case $question in *"(recall"*) die 2 "Write the question without its (recall ...) mark: pkm adds it." ;; esac
  index_ensure
  path=$(note_for "$name")
  [ -n "$path" ] || die 1 "No note named $name."
  ttype=$(note_type "$path")
  case $ttype in
    day|close) die 1 "$path is a $ttype page: questions are written to notes, not to $ttype pages." ;;
  esac
  # The question as the note already has it: the same text in a list line, with or without its mark.
  dup=$(QUESTION="$question" awk '
    {
      c = $0; sub(/\r$/, "", c); sub(/^[ \t]*([-*+]|[0-9]+[.)])[ \t]+/, "", c)
      sub(/[ \t]*\(recall [^)]*\)[ \t]*$/, "", c); sub(/[ \t]+$/, "", c)
      if (c == ENVIRON["QUESTION"]) { print NR; exit }
    }' "$path")
  [ -z "$dup" ] || die 1 "$path:$dup already has this question."
  tomorrow=$(day_add "$today" 1)
  { printf '%s\n' "- $question (recall $tomorrow 1d)"; cat "$tmp/recall-answers"; } > "$tmp/recall-block"
  loc=$(section_add "$path" Questions "$(cat "$tmp/recall-block")" no) || exit $?
  echo "$path:$loc"
}

cmd_recall() {
  if [ "${1:-}" = add ]; then shift; recall_add "$@"; return $?; fi
  if [ $# -eq 2 ] && { [ "$2" = yes ] || [ "$2" = no ]; }; then
    recall_rewrite "$1" "$2"
    return $?
  fi
  [ $# -le 1 ] || die 2 "Usage: pkm recall [note] | pkm recall <path:line> yes|no"
  index_ensure
  if [ $# -eq 1 ]; then
    local found
    found=$(note_for "$1")
    [ -n "$found" ] || die 1 "No note named $1."
    printf '%s\n' "$found" > "$tmp/recall-files"
    scope="$found"
  else
    files yes '*.md' > "$tmp/recall-files"
    scope="the vault"
  fi
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/recall-files" "$(recall_awk)"'
    FNR == 1 { file = rel(FILENAME); fence = 0; front = 0 }
    FNR == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") front = 0; next }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence { next }
    {
      c = $0; sub(/\r$/, "", c); gsub(/`[^`]*`/, "", c)
      if (!recall_parse(recall_inner(c))) next
      t = c; sub(/^[ \t]*([-*+]|[0-9]+[.)])[ \t]+/, "", t); if (t ~ /^\[.\][ \t]+/) sub(/^\[.\][ \t]+/, "", t)
      if (t ~ /^~~/) next
      print RDATE "\t" file "\t" FNR "\t" $0
    }
  ' > "$tmp/recall-all"
  local tab
  tab=$(printf '\t')
  LC_ALL=C sort -t "$tab" -k1,1 -k2,2 -k3,3n "$tmp/recall-all" > "$tmp/recall-sorted"
  awk -F "$tab" -v today="$today" '$1 <= today { print $2 ":" $3 ": " $4 }' "$tmp/recall-sorted" > "$tmp/recall-due"
  if [ -s "$tmp/recall-due" ]; then
    cat "$tmp/recall-due"
    return 0
  fi
  local next
  next=$(awk -F "$tab" -v today="$today" '$1 > today { print $1 " " $2 ":" $3; exit }' "$tmp/recall-sorted")
  if [ -n "$next" ]; then
    echo "Nothing due. The next recall question is due ${next%% *} (${next#* })." >&2
  elif [ "$scope" = "the vault" ]; then
    echo "No recall questions in the vault." >&2
  else
    echo "No recall questions in $scope." >&2
  fi
  return 1
}
