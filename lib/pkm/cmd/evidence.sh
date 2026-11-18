# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/evidence.sh: pkm evidence [--verify] <note | ->: every summary line must link its source. The summary is a
# note's ## Now section, a close page whole, or stdin (-). Only list items are checked, after a leading "> " is taken off;
# struck items are skipped. A source is a link to a day page or a source note, a path:line naming a vault file, or an
# http(s) address. A link to any other note only says what the line is about. --verify also checks that each link
# resolves, and that each path:line names an existing file with at least that many lines. Findings print as path:line: text
# (-:N: for stdin) and exit 1. Sourced by bin/pkm. Defines functions only.

# The lines to check: "label<TAB>line<TAB>text" for each list item in the range, outside code and frontmatter.
ev_items_awk() {
  cat <<'AWK'
{ sub(/\r$/, "") }
NR == 1 { bom_mark = "\357\273\277"; if (substr($0, 1, length(bom_mark)) == bom_mark) $0 = substr($0, length(bom_mark) + 1) }
NR == 1 && $0 == "---" { front = 1; next }
front { if ($0 == "---") front = 0; next }
/^[ \t]*(```|~~~)/ { fence = !fence; next }
fence { next }
NR < from || NR > to { next }
{
  s = $0; sub(/^> /, "", s)
  if (!match(s, /^[ \t]*([-*+]|[0-9]+[.)])[ \t]+/)) next
  t = substr(s, RLENGTH + 1)
  if (match(t, /^\[.\][ \t]+/)) t = substr(t, RLENGTH + 1)
  if (substr(t, 1, 2) == "~~") next
  print label "\t" NR "\t" s
}
AWK
}

# The link targets written in the items, one per line, to be resolved by link_build.
ev_targets_awk() {
  cat <<'AWK'
function target_of(inner,   t) {
  t = inner; sub(/\|.*/, "", t); sub(/#.*/, "", t); sub(/\^.*/, "", t)
  gsub(/^[ \t]+|[ \t]+$/, "", t); sub(/.*\//, "", t); return t
}
{
  s = $3; gsub(/`[^`]*`/, "", s); r = s
  while (match(r, /\[\[[^]]*\]\]/)) {
    inner = substr(r, RSTART + 2, RLENGTH - 4); r = substr(r, RSTART + RLENGTH)
    tg = target_of(inner); if (tg != "") print tg
  }
}
AWK
}

# The file paths named by path:line in the items, one per line.
ev_paths_awk() {
  cat <<'AWK'
{
  p = $3; gsub(/`[^`]*`/, "", p); gsub(/https?:\/\/[^] \t<>()"'`[]+/, " ", p)
  while (match(p, /[A-Za-z0-9_.\/-]+\.[A-Za-z0-9]+:[0-9]+/)) {
    tok = substr(p, RSTART, RLENGTH); p = substr(p, RSTART + RLENGTH)
    f = tok; sub(/:[0-9]+$/, "", f); print f
  }
}
AWK
}

# The check. Reads RES (link_build's lb-resolved), TYPES (path and type), COUNTS (path and line count, or missing or
# outside) and VERIFY (yes or no) from the environment, and prints a finding for each item without a source.
ev_check_awk() {
  cat <<'AWK'
function target_of(inner,   t) {
  t = inner; sub(/\|.*/, "", t); sub(/#.*/, "", t); sub(/\^.*/, "", t)
  gsub(/^[ \t]+|[ \t]+$/, "", t); sub(/.*\//, "", t); return t
}
function report(label, n, msg) { print label ":" n ": " msg }
BEGIN {
  FS = "\t"
  while ((getline line < ENVIRON["RES"]) > 0) { split(line, f, "\t"); st[f[1]] = f[2]; pa[f[1]] = f[3] }
  close(ENVIRON["RES"])
  while ((getline line < ENVIRON["TYPES"]) > 0) { split(line, f, "\t"); ty[f[1]] = f[2] }
  close(ENVIRON["TYPES"])
  while ((getline line < ENVIRON["COUNTS"]) > 0) { split(line, f, "\t"); ct[f[1]] = f[2] }
  close(ENVIRON["COUNTS"])
  verify = ENVIRON["VERIFY"]
}
{
  label = $1; n = $2; text = $3
  src = 0
  s = text; gsub(/`[^`]*`/, "", s)
  r = s
  while (match(r, /\[\[[^]]*\]\]/)) {
    inner = substr(r, RSTART + 2, RLENGTH - 4); r = substr(r, RSTART + RLENGTH)
    tg = target_of(inner)
    if (!(tg in st) || st[tg] == "dead" || pa[tg] == "") {
      if (verify == "yes") report(label, n, "broken link [[" inner "]]")
      continue
    }
    if (ty[pa[tg]] == "day" || ty[pa[tg]] == "source") src = 1
  }
  p = s; gsub(/https?:\/\/[^] \t<>()"'`[]+/, " ", p)
  u = s
  while (match(u, /https?:\/\/[^] \t<>()"'`[]+/)) { src = 1; u = substr(u, RSTART + RLENGTH) }
  while (match(p, /[A-Za-z0-9_.\/-]+\.[A-Za-z0-9]+:[0-9]+/)) {
    tok = substr(p, RSTART, RLENGTH); p = substr(p, RSTART + RLENGTH)
    pth = tok; sub(/:[0-9]+$/, "", pth); lineno = tok; sub(/^.*:/, "", lineno)
    c = (pth in ct) ? ct[pth] : "missing"
    if (c == "outside") { if (verify == "yes") report(label, n, "outside the vault: " tok); continue }
    if (verify != "yes") { src = 1; continue }
    if (c == "missing") report(label, n, "no such file: " pth)
    else if (lineno + 0 > c + 0) report(label, n, "no such line: " tok " (it has " c " lines)")
    else src = 1
  }
  if (!src) report(label, n, text)
}
AWK
}

cmd_evidence() {
  local verify=no arg="" src label type path bounds from to total
  while [ $# -gt 0 ]; do
    case $1 in
      --verify) verify=yes; shift ;;
      *) [ -z "$arg" ] || die 2 "Usage: pkm evidence [--verify] <note or name | ->"; arg=$1; shift ;;
    esac
  done
  [ -n "$arg" ] || die 2 "Usage: pkm evidence [--verify] <note or name | ->"
  index_ensure
  if [ "$arg" = - ]; then
    cat > "$tmp/ev-stdin"
    src="$tmp/ev-stdin"; label="-"; type=note
  else
    path=$(note_for "$arg")
    [ -n "$path" ] || die 1 "No note named $arg."
    src=$path; label=$path; type=$(note_type "$path")
  fi
  total=$(awk 'END { print NR }' "$src")
  from=1; to=$total
  if [ "$arg" != - ] && [ "$type" != close ]; then
    bounds=$(section_bounds "$src" Now)
    [ -n "$bounds" ] || die 1 "$label has no ## Now section: evidence checks that section, or a close page whole."
    from=${bounds%% *}; to=${bounds##* }
  fi
  awk -F '\t' -v label="$label" -v from="$from" -v to="$to" "$(ev_items_awk)" "$src" > "$tmp/ev-items"
  awk -F '\t' "$(ev_targets_awk)" "$tmp/ev-items" | LC_ALL=C sort -u > "$tmp/ev-targets"
  link_build "$tmp/ev-targets"
  awk -F "$(printf '\t')" -v OFS="$(printf '\t')" '{ print $3, $2 }' "$(cache_dir)/names.tsv" > "$tmp/ev-types"
  awk -F '\t' "$(ev_paths_awk)" "$tmp/ev-items" | LC_ALL=C sort -u > "$tmp/ev-paths"
  : > "$tmp/ev-counts"
  while IFS= read -r p; do
    case $p in
      /*|../*|*/../*) printf '%s\t%s\n' "$p" outside >> "$tmp/ev-counts" ;;
      *)
        if [ -f "$p" ]; then printf '%s\t%s\n' "$p" "$(awk 'END { print NR }' "$p")" >> "$tmp/ev-counts"
        else printf '%s\t%s\n' "$p" missing >> "$tmp/ev-counts"; fi ;;
    esac
  done < "$tmp/ev-paths"
  RES="$tmp/lb-resolved" TYPES="$tmp/ev-types" COUNTS="$tmp/ev-counts" VERIFY=$verify \
    awk -F '\t' "$(ev_check_awk)" "$tmp/ev-items" > "$tmp/ev-findings"
  if [ -s "$tmp/ev-findings" ]; then
    cat "$tmp/ev-findings"
    return 1
  fi
  echo "Every summary line links its source."
}
