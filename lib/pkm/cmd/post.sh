# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/post.sh: pkm post <path:line[-line]> <note>[#Section]: copies the lines of a page into a note, verbatim, with
# " ([[<page>]])" after the last line, where <page> is the source page's name. The lines go right after the section's last
# line, with no blank between list items. An empty section, or a note that ends after its heading, gets a blank line and
# then the lines. A missing section is created at the end as "## <Section>". Refuses (exit 1) a range with a heading, an
# open task (it would show twice in tasks), a day or close target, and a missing target. A malformed source, a source
# outside the vault, or lines out of range exit 2. Prints path:line of the first posted line. Sourced by bin/pkm.

# final_line_copy <file> <copy>: a copy of the file that ends with a line end, so an entry written after its last line starts on
# a line of its own, even when the note ends without a newline.
final_line_copy() {
  cat "$1" > "$2"
  if [ -n "$(tail -c 1 "$1")" ]; then printf '\n' >> "$2"; fi
}

# insert_after <file> <after> <blank yes|no> <entries>: puts the entries after line <after> of the file, with a blank
# line before them when asked. Prints the number of the first entry line.
insert_after() {
  local file=$1 after=$2 blank=$3 entries=$4 first eol
  eol=$(eol_of "$file")
  final_line_copy "$file" "$tmp/post-src"
  {
    head -n "$after" "$tmp/post-src"
    if [ "$blank" = yes ]; then printf '%s\n' "$eol"; fi
    cat "$entries"
    tail -n +"$((after + 1))" "$tmp/post-src"
  } > "$tmp/post-page"
  mv "$tmp/post-page" "$file" || die 1 "Can't write $file."
  first=$((after + 1))
  if [ "$blank" = yes ]; then first=$((first + 1)); fi
  echo "$first"
}

# add_section <file> <section> <entries>: creates "## <section>" at the end of the file, then the entries. Prints the
# number of the first entry line.
add_section() {
  local file=$1 section=$2 entries=$3 total extra=0 eol
  eol=$(eol_of "$file")
  final_line_copy "$file" "$tmp/post-src"
  total=$(awk 'END { print NR }' "$file")
  if [ "$total" -gt 0 ] && [ -n "$(tail -n 1 "$file" | tr -d ' \t\r')" ]; then extra=1; fi
  {
    cat "$tmp/post-src"
    if [ "$extra" = 1 ]; then printf '%s\n' "$eol"; fi
    printf '## %s%s\n' "$section" "$eol"
    printf '%s\n' "$eol"
    cat "$entries"
  } > "$tmp/post-page"
  mv "$tmp/post-page" "$file" || die 1 "Can't write $file."
  echo $((total + extra + 3))
}

cmd_post() {
  [ $# -eq 2 ] || die 2 "Usage: pkm post <path:line[-line]> <note>[#Section]"
  local spec=$1 target=$2 path loc a b total name section tpath ttype base bounds first last ins blank
  case $spec in
    *:*) path=${spec%:*}; loc=${spec##*:} ;;
    *) die 2 "A source is path:line or path:line-line, such as daybook/2026/11/2026-11-10.md:10, got: $spec" ;;
  esac
  case $loc in
    *-*) a=${loc%-*}; b=${loc#*-} ;;
    *) a=$loc; b=$loc ;;
  esac
  case $a in ''|*[!0-9]*) die 2 "A source is path:line or path:line-line, got: $spec" ;; esac
  case $b in ''|*[!0-9]*) die 2 "A source is path:line or path:line-line, got: $spec" ;; esac
  case $path in
    /*|../*|*/../*) die 2 "The source is outside the vault: $path" ;;
  esac
  [ -f "$path" ] || die 2 "No file $path in the vault."
  total=$(awk 'END { print NR }' "$path")
  [ "$a" -ge 1 ] && [ "$a" -le "$b" ] && [ "$b" -le "$total" ] \
    || { if [ "$a" = "$b" ]; then die 2 "Line $loc is outside $path, which has $total lines."; fi
         die 2 "Lines $loc are outside $path, which has $total lines."; }
  sed -n "${a},${b}p" "$path" > "$tmp/post-lines"
  grep -qE '^#+[[:space:]]' "$tmp/post-lines" \
    && die 1 "A range with a heading can't be posted: post the lines under the heading instead."
  grep -qE '^[[:space:]]*[-*+][[:space:]]+\[ \]' "$tmp/post-lines" \
    && die 1 "An open task stays where it was written: posting it would show it twice in tasks."

  case $target in
    *'#'*) name=${target%%#*}; section=${target#*#}; [ -n "$section" ] || die 2 "The section name after # is missing." ;;
    *) name=$target; section="" ;;
  esac
  index_ensure
  tpath=$(note_for "$name")
  [ -n "$tpath" ] || die 1 "No note named $name."
  ttype=$(note_type "$tpath")
  case $ttype in
    day|close) die 1 "$tpath is a $ttype page: entries are posted to notes, not to $ttype pages." ;;
  esac

  base=$(basename "$path" .md)
  awk -v suffix=" ([[$base]])" -v a="$a" -v b="$b" -v eol="$(eol_of "$tpath")" '
    NR >= a && NR <= b { sub(/\r$/, ""); if (NR == b) print $0 suffix eol; else print $0 eol }
  ' "$path" > "$tmp/post-entries"

  # The entry already in the note, anywhere in it, is not written twice: the existing place is printed, and it exits 1.
  dup=$(awk -v entries="$tmp/post-entries" '
    BEGIN { k = 0; while ((getline l < entries) > 0) { sub(/\r$/, "", l); E[++k] = l }; close(entries) }
    { sub(/\r$/, ""); T[NR] = $0 }
    END {
      if (k == 0) exit
      for (i = 1; i + k - 1 <= NR; i++) {
        ok = 1
        for (j = 1; j <= k; j++) if (T[i + j - 1] != E[j]) { ok = 0; break }
        if (ok) { print i; exit }
      }
    }
  ' "$tpath")
  if [ -n "$dup" ]; then
    echo "$tpath:$dup"
    die 1 "The entry is posted there already: nothing was written."
  fi

  if [ -n "$section" ]; then
    bounds=$(section_bounds "$tpath" "$section")
    if [ -n "$bounds" ]; then
      first=${bounds%% *}; last=${bounds##* }
      blank=no
      [ "$first" = "$last" ] && blank=yes
      ins=$last
      echo "$tpath:$(insert_after "$tpath" "$ins" "$blank" "$tmp/post-entries")"
    else
      echo "$tpath:$(add_section "$tpath" "$section" "$tmp/post-entries")"
    fi
  else
    ins=$(awk '{ if ($0 ~ /[^ \t\r]/) n = NR } END { print n + 0 }' "$tpath")
    blank=no
    if [ "$ins" -gt 0 ] && sed -n "${ins}p" "$tpath" | grep -qE '^#+[[:space:]]'; then blank=yes; fi
    echo "$tpath:$(insert_after "$tpath" "$ins" "$blank" "$tmp/post-entries")"
  fi
}
