# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/plain.sh: a line as someone outside the vault reads it: links as their shown text, or the title of the note
# they name, and, for a summary, without the list mark, the box, the entry's time, the markers and the link to the day
# the line came from. Used by upcoming --ics. Sourced by bin/pkm. Defines functions only.

# plain_titles <texts file> <out>: name<TAB>title for each link target in the texts, from the cache (a target that
# names no note keeps no row).
plain_titles() {
  local tab
  tab=$(printf '\t')
  awk "$(awk_links_in)"'{ n = targets($0, t); for (i = 1; i <= n; i++) print t[i] }' "$1" | LC_ALL=C sort -u > "$tmp/pl-targets"
  : > "$2"
  [ -s "$tmp/pl-targets" ] || return 0
  link_index "$tmp/pl-index"
  link_slugs "$tmp/pl-targets" "$tmp/pl-slugs"
  link_resolve "$tmp/pl-index" "$tmp/pl-slugs" "$tmp/pl-resolved"
  awk -F "$tab" -v OFS="$tab" '
    FILENAME == ARGV[1] { title[$1] = $2; next }
    $2 != "dead" && ($3 in title) && title[$3] != "" { print $1, title[$3] }
  ' "$(cache_dir)/notes.tsv" "$tmp/pl-resolved" > "$2"
}

# awk_plain: the awk functions. They need awk_markers in front of them, and the titles from plain_titles in
# PLAIN_TITLE[name]. plain_links(t) shows each link as its shown text or its note's title (its name when it names no
# note). plain_unmark(t) takes out the markers and a 📅 date. plain_summary(t) is the line as a summary: without the
# list mark, the box, the entry's time, the link to its day page and the markers, its links shown, its spaces tidied.
awk_plain() {
  cat <<'AWK'
function plain_link(inner,   bar, t) {
  bar = index(inner, "|")
  if (bar > 0) return substr(inner, bar + 1)
  t = inner; sub(/\\$/, "", t); sub(/#.*/, "", t); sub(/\^.*/, "", t); gsub(/^[ \t]+|[ \t]+$/, "", t); sub(/.*\//, "", t)
  if (t == "") { t = inner; sub(/^#/, "", t); return t }
  return (t in PLAIN_TITLE) ? PLAIN_TITLE[t] : t
}
function plain_links(t,   out) {
  out = ""
  while (match(t, /\[\[[^]]*\]\]/)) {
    out = out substr(t, 1, RSTART - 1) plain_link(substr(t, RSTART + 2, RLENGTH - 4))
    t = substr(t, RSTART + RLENGTH)
  }
  return out t
}
function plain_unmark(t,   out, i, j, c, e, rest) {
  out = ""
  while ((i = index(t, "(")) > 0) {
    rest = substr(t, i + 1); j = index(rest, ")")
    if (j == 0) break
    c = substr(rest, 1, j - 1)
    if (line_markers("(" c ")") != "") { out = out substr(t, 1, i - 1); sub(/ +$/, "", out) }
    else out = out substr(t, 1, i + j)
    t = substr(rest, j + 1)
  }
  t = out t
  e = "\360\237\223\205 "; i = index(t, e)
  if (i > 0) {
    rest = substr(t, i + length(e)); sub(/^[^ )]*/, "", rest)
    out = substr(t, 1, i - 1); sub(/ +$/, "", out); t = out rest
  }
  return t
}
function plain_summary(t) {
  sub(/^[-*+] (\[.\] )?/, "", t)
  sub(/^[0-2][0-9]:[0-5][0-9](-[0-2][0-9]:[0-5][0-9])? /, "", t)
  t = plain_unmark(t)
  gsub(/ *\(\[\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][^]]*\]\]\)/, "", t)
  t = plain_links(t)
  gsub(/[ \t]+/, " ", t); sub(/^ /, "", t); sub(/ $/, "", t)
  return t
}
AWK
}
