# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/overview.sh: pkm overview [--json]: the shape of the vault, from the cache. Each note names the one it
# belongs to with part_of, so the notes make trees. The trees are shown in sections, by the kind of their top note:
# areas (type area), projects (project or writing, not done or dropped), resources (course, topic, source, not done or
# dropped) and other (a note of another kind with notes under it), then the number of notes in archive/. In a tree, the
# notes come by name, each under its parent. A line is path:<title line>: <the titles from the top> (<type>, <status>).
# Day and close pages, and notes in the archive, are not in the trees (tree.sh). Sourced by bin/pkm. Defines functions only.

cmd_overview() {
  local json=no arg US tab
  for arg in "$@"; do
    case $arg in
      --json) json=yes ;;
      *) die 2 "Usage: pkm overview [--json]" ;;
    esac
  done
  [ "$json" = no ] || need_jq
  US=$(printf '\037')
  tab=$(printf '\t')
  index_ensure
  tree_parents "$tmp/ov-parents"
  awk -F "$tab" -v US="$US" '
    function name(p,   n) { n = p; sub(/.*\//, "", n); sub(/\.md$/, "", n); return n }
    function closed(s) { return s ~ /^(done|dropped|published|sold|gone|archived)$/ }
    # by_name: sorts the n paths in a[1..n] by name, then path (insertion sort: lists of children are short).
    function by_name(a, n,   i, j, v) {
      for (i = 2; i <= n; i++) { v = a[i]; j = i - 1
        while (j > 0 && (name(a[j]) > name(v) || (name(a[j]) == name(v) && a[j] > v))) { a[j + 1] = a[j]; j-- }
        a[j + 1] = v }
    }
    function show(p, sec, depth, trail, parent,   label, text, kids, n, i) {
      if (p in shown) return
      shown[p] = 1
      text = trail title[p]
      label = type[p] (status[p] != "" ? ", " status[p] : "")
      print sec US (++order) US p US depth US parent US type[p] US status[p] US text " (" label ")"
      n = split(children[p], kids, "\n")
      by_name(kids, n)
      for (i = 1; i <= n; i++) if (kids[i] != "") show(kids[i], sec, depth + 1, text " / ", p)
    }
    FILENAME == ARGV[1] { up[$1] = $2; next }
    {
      if ($3 == "day" || $3 == "close") next
      if ($1 ~ /^archive\//) { archived++; next }
      note[$1] = 1; title[$1] = $2; type[$1] = $3; status[$1] = $4; all[++n] = $1
    }
    END {
      for (i = 1; i <= n; i++) {
        p = all[i]
        if (p in up) { q = up[p]; parent[p] = q; children[q] = children[q] p "\n"; haskids[q] = 1 }
      }
      by_name(all, n)
      for (s = 1; s <= 4; s++)
        for (i = 1; i <= n; i++) {
          p = all[i]; t = type[p]
          if (p in parent) continue
          if (t == "area") sec = 1
          else if (closed(status[p])) continue
          else if (t == "project" || t == "writing") sec = 2
          else if (t == "course" || t == "topic" || t == "source") sec = 3
          else if (p in haskids) sec = 4
          else continue
          if (sec == s) show(p, s, 0, "", "")
        }
      if (archived > 0) print 5 US (++order) US "" US "" US "" US "" US "" US archived " " (archived == 1 ? "note" : "notes") " in archive/"
    }
  ' "$tmp/ov-parents" "$(cache_dir)/notes.tsv" > "$tmp/ov-records"
  [ -s "$tmp/ov-records" ] || die 1 "Nothing to show: no areas, projects, courses, topics or sources yet."
  # The line of each note's title, the first "# " line after its frontmatter (1 when it has none).
  awk -F "$US" '$3 != "" { print $3 }' "$tmp/ov-records" > "$tmp/ov-files"
  : > "$tmp/ov-lines"
  if [ -s "$tmp/ov-files" ]; then
    # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
    scan "$tmp/ov-files" '
      FNR == 1 { file = rel(FILENAME); front = ($0 ~ /^---\r?$/); found = 0; if (front) next }
      front { if ($0 ~ /^---\r?$/) front = 0; next }
      !found && /^# / { print file "\t" FNR; found = 1 }
    ' > "$tmp/ov-lines"
  fi
  awk -F "$US" -v OFS="$US" -v json="$json" '
    BEGIN { label[1] = "areas"; label[2] = "projects"; label[3] = "resources"; label[4] = "other"; label[5] = "archive"
            kind[1] = "area"; kind[2] = "project"; kind[3] = "resource"; kind[4] = "other"; kind[5] = "archive" }
    FILENAME == ARGV[1] { split($0, f, "\t"); at[f[1]] = f[2]; next }
    {
      line = ($3 == "") ? "" : (($3 in at) ? at[$3] : 1)
      if (json == "yes") { print kind[$1], $3, line, $8, $6, $7, $5, $4; next }
      if ($1 != cur) { cur = $1; print "== " label[$1] }
      print ($3 == "") ? $8 : $3 ":" line ": " $8
    }
  ' "$tmp/ov-lines" "$tmp/ov-records" > "$tmp/ov-out"
  if [ "$json" = no ]; then cat "$tmp/ov-out"; return 0; fi
  jq -R -c 'split("\u001f") as $f
    | if $f[0] == "archive" then {kind: "archive", path: null, line: null, text: $f[3], count: ($f[3] | split(" ")[0] | tonumber)}
      else {kind: $f[0], path: $f[1], line: ($f[2] | tonumber), text: $f[3], type: $f[4],
            status: (if $f[5] == "" then null else $f[5] end), parent: (if $f[6] == "" then null else $f[6] end),
            depth: ($f[7] | tonumber)} end' "$tmp/ov-out"
}
