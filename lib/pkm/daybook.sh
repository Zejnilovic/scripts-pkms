# shellcheck shell=bash
# lib/pkm/daybook.sh: the day pages. A page is daybook/<year>/<month>/<date>.md; in a shared vault (shared=yes) it is
# <date>-<writer>.md, with the writer from the user config. Every command that needs a day uses these functions.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# day_name <date>: the page's file name in this vault. A shared vault needs writer= in the user config; without it the
# function says how to set it and fails (2), and the caller exits.
day_name() {
  local writer
  if [ "$(config shared no)" = yes ]; then
    writer=$(user_config_value writer)
    if [ -z "$writer" ]; then
      echo "This vault is shared, so each page carries its writer's name: set writer=<name> in $(user_config_file)." >&2
      return 2
    fi
    printf '%s-%s.md\n' "$1" "$writer"
  else
    printf '%s.md\n' "$1"
  fi
}

# day_path <date>: the page for a date: one that already exists anywhere under daybook/ (an editor may have made it
# flat, or in another month), else the page in its month's folder.
day_path() {
  local name existing
  name=$(day_name "$1") || return 2
  existing=$(files yes "$name" | grep '^daybook/' | head -n 1)
  if [ -n "$existing" ]; then printf '%s\n' "$existing"
  else printf 'daybook/%s/%s/%s\n' "${1:0:4}" "${1:5:2}" "$name"; fi
}

# day_ensure <date>: the page for a date, created from the day template when missing. Prints its path.
day_ensure() {
  local date=$1 path name title template first
  name=$(day_name "$date") || return 2
  path=$(day_path "$date") || return 2
  if [ -f "$path" ]; then printf '%s\n' "$path"; return 0; fi
  template=$(template_file day.md)
  [ -f "$template" ] || die 2 "No day template: add $(template_file day.md), or reinstall pkm."
  title=$date
  if [ "$(config shared no)" = yes ]; then
    # The writer's name with its first letter in upper case, without bash 4's case conversion.
    writer=$(user_config_value writer)
    first=$(printf '%s' "${writer%"${writer#?}"}" | tr '[:lower:]' '[:upper:]')
    title="$date $first${writer#?}"
  fi
  mkdir -p "$(dirname "$path")" || die 2 "Can't create $(dirname "$path")"
  render "$template" "$title" "$date" "$name" "$date" > "$tmp/day-page"
  mv "$tmp/day-page" "$path"
  printf '%s\n' "$path"
}

# section_add <page> <heading> <lines> <yes|no: a blank line before the lines>: adds the lines at the end of the page's
# "## <heading>" section, after its last line of text, and creates the section at the end of the page when it is
# missing. A blank line comes before the section's first line, and before the lines when they are a block (yes). Prints
# the line number of the first added line.
section_add() {
  local lines_file eol
  printf '%s\n' "$3" > "$tmp/section-lines"
  lines_file="$tmp/section-lines"
  eol=$(eol_of "$1")
  EOL=$eol HEAD=$2 SEP=$4 LINES=$lines_file FIRST="$tmp/log-first" awk '
    function block(   b) {
      while ((getline b < ENVIRON["LINES"]) > 0) {
        if (!placed) { first = out + 1; placed = 1 }
        print b ENVIRON["EOL"]; out++
      }
      close(ENVIRON["LINES"])
    }
    # line keeps the file'"'"'s own text and ending; plain is the same line without its carriage return, for the comparisons.
    { line[NR] = $0; plain[NR] = $0; sub(/\r$/, "", plain[NR]) }
    END {
      heading = "## " ENVIRON["HEAD"]
      for (i = 1; i <= NR; i++) { l = plain[i]; sub(/[ \t]+$/, "", l); if (l == heading) { start = i; break } }
      if (start) {
        end = NR
        for (i = start + 1; i <= NR; i++) if (plain[i] ~ /^## /) { end = i - 1; break }
        last = start
        for (i = start + 1; i <= end; i++) if (plain[i] !~ /^[ \t]*$/) last = i
        for (i = 1; i <= NR; i++) {
          print line[i]; out++
          if (i == last) { if (last == start || ENVIRON["SEP"] == "yes") { print ENVIRON["EOL"]; out++ } block() }
        }
      } else {
        for (i = 1; i <= NR; i++) { print line[i]; out++ }
        if (NR > 0 && plain[NR] !~ /^[ \t]*$/) { print ENVIRON["EOL"]; out++ }
        print heading ENVIRON["EOL"]; out++
        print ENVIRON["EOL"]; out++
        block()
      }
      print first > ENVIRON["FIRST"]
    }
  ' "$1" > "$tmp/section-page" && mv "$tmp/section-page" "$1"
  cat "$tmp/log-first"
}

# log_add <page> <lines file> <yes|no>: section_add for the Log section, with the lines from a file.
log_add() {
  section_add "$1" Log "$(cat "$2")" "$3"
}
