# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/tree.sh: the trees of the vault. Each note names the one it belongs to with part_of (by name, slug or alias,
# as a link does), so the notes make trees. Day and close pages, and notes in archive/, are not in them. Used by overview,
# and by --under. Sourced by bin/pkm. Defines functions only.

# tree_parents <out>: path<TAB>parent path for each note whose part_of names another note of the trees. A part_of that
# names the note itself, a list, or no note is left out.
tree_parents() {
  local tab
  tab=$(printf '\t')
  index_ensure
  # Each note's part_of, as the name it gives, resolved as a link is.
  awk -F "$tab" -v OFS="$tab" "$(awk_part_of)"'
    $2 == "part_of" { t = part_of_target($3); if (t != "") print $1, t }
  ' "$(cache_dir)/fields.tsv" > "$tmp/tp-parts"
  cut -f2 "$tmp/tp-parts" | LC_ALL=C sort -u > "$tmp/tp-targets"
  link_build "$tmp/tp-targets"
  awk -F "$tab" -v OFS="$tab" '
    FILENAME == ARGV[1] { resolved[$1] = ($2 == "dead") ? "" : $3; next }
    FILENAME == ARGV[2] { want[$1] = $2; next }
    $3 != "day" && $3 != "close" && $1 !~ /^archive\// { note[$1] = 1; all[++n] = $1 }
    END {
      for (i = 1; i <= n; i++) {
        p = all[i]; q = (p in want) ? resolved[want[p]] : ""
        if (q != "" && q != p && (q in note)) print p, q
      }
    }
  ' "$tmp/lb-resolved" "$tmp/tp-parts" "$(cache_dir)/notes.tsv" > "$1"
}

# tree_paths <note path> <out>: the note and every note under it, at any depth, one path per line, sorted. A loop of
# part_of ends where it comes back to a note already in the tree.
tree_paths() {
  local tab
  tab=$(printf '\t')
  tree_parents "$tmp/tp-parents"
  awk -F "$tab" -v top="$1" '
    { kids[$2] = kids[$2] $1 "\n" }
    END {
      queue[1] = top; seen[top] = 1; n = 1
      for (i = 1; i <= n; i++) {
        k = split(kids[queue[i]], a, "\n")
        for (j = 1; j <= k; j++) if (a[j] != "" && !(a[j] in seen)) { seen[a[j]] = 1; queue[++n] = a[j] }
      }
      for (i = 1; i <= n; i++) print queue[i]
    }
  ' "$tmp/tp-parents" | LC_ALL=C sort > "$2"
}
