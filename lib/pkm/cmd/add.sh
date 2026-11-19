# shellcheck shell=bash
# lib/pkm/cmd/add.sh: pkm add: writes an entry at the end of a day's Log, as "- HH:MM text", and prints path:line.
# Text with several lines, or read from stdin with -, goes under a "### HH:MM" heading, verbatim. --file <path> copies a
# file into files/<year>/<month>/, named <date>-<slug of its name>, and the entry links it; an existing file is never
# overwritten.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_add() {
  local date=$today text="" from_stdin=no page line file="" stored="" link shown
  while [ $# -gt 0 ]; do
    case $1 in
      --day) { [ $# -ge 2 ] && is_date "$2"; } || die 2 "--day needs a date YYYY-MM-DD"; date=$2; shift 2 ;;
      --file) [ $# -ge 2 ] && [ -n "$2" ] || die 2 "--file needs the path of a file"; file=$2; shift 2 ;;
      -) from_stdin=yes; shift ;;
      *) text="${text:+$text }$1"; shift ;;
    esac
  done
  if [ -n "$file" ]; then
    [ "$from_stdin" = no ] || die 2 "A file goes with one line of text, not with - (stdin)."
    stored=$(add_file_place "$file" "$date") || exit $?
  fi
  if [ "$from_stdin" = yes ]; then cat > "$tmp/add-input"; else printf '%s\n' "$text" > "$tmp/add-input"; fi
  # Trailing blank lines are not part of the entry.
  awk '{ line[NR] = $0 } END { n = NR; while (n > 0 && line[n] ~ /^[ \t]*$/) n--; for (i = 1; i <= n; i++) print line[i] }' \
    "$tmp/add-input" > "$tmp/add-text"
  if [ -n "$file" ]; then
    [ "$(wc -l < "$tmp/add-text" | tr -d ' ')" -le 1 ] || die 2 "A file goes with one line of text."
    page=$(day_path "$date") || exit $?
    # The link is relative to the page's folder, so it works in any editor and on the site.
    shown=${stored##*/}; shown=${shown#"$date"-}
    link="[$shown]($(printf '%s' "$page" | sed -e 's|[^/]*$||' -e 's|[^/][^/]*/|../|g')$stored)"
    if grep -q '[^[:space:]]' "$tmp/add-text"; then printf '%s: %s\n' "$(cat "$tmp/add-text")" "$link" > "$tmp/add-text.new"
    else printf '%s\n' "$link" > "$tmp/add-text.new"; fi
    mv "$tmp/add-text.new" "$tmp/add-text"
    mkdir -p "${stored%/*}" || die 1 "Can't make ${stored%/*}."
    cp "$file" "$stored" || die 1 "Can't copy $file to $stored."
  fi
  if ! grep -q '[^[:space:]]' "$tmp/add-text" 2>/dev/null; then die 2 "Nothing to add: give the text in quotes, or - to read it from stdin."; fi
  block=no
  if [ "$(wc -l < "$tmp/add-text" | tr -d ' ')" -gt 1 ]; then
    { printf '### %s\n\n' "$clock"; cat "$tmp/add-text"; } > "$tmp/add-lines"
    block=yes
  else
    printf -- '- %s %s\n' "$clock" "$(cat "$tmp/add-text")" > "$tmp/add-lines"
  fi
  page=$(day_ensure "$date") || exit $?
  line=$(log_add "$page" "$tmp/add-lines" "$block") || exit $?
  echo "$page:$line"
}

# add_file_place <file> <date>: where add --file keeps a copy of the file: files/<year>/<month>/<date>-<name>, the name
# being the slug of the file's name with its extension in lower case. Fails (2) when the file can't be read, and (1) when
# that place is taken, since a file is never overwritten.
add_file_place() {
  local src=$1 date=$2 base stem ext name place
  [ -f "$src" ] && [ -r "$src" ] || die 2 "No file to add at $src."
  base=${src##*/}
  case $base in
    ?*.*) stem=${base%.*}; ext=$(lowercase "${base##*.}") ;;
    *) stem=$base; ext="" ;;
  esac
  name=$(slugify "$stem")
  [ -n "$name" ] || die 2 "No file name in '$base': rename the file with Latin letters or digits first."
  place="files/${date:0:4}/${date:5:2}/$date-$name${ext:+.$ext}"
  [ ! -e "$place" ] || die 1 "$place exists, and pkm never overwrites a file: rename the file first."
  printf '%s\n' "$place"
}
