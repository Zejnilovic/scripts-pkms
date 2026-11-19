# shellcheck shell=bash
# lib/pkm/cmd/backlinks.sh: pkm backlinks: every line that links a note, by its name, slug or alias, archive included,
# and every line under a ### heading that links it (about.sh). --under <note> keeps the lines of the notes in its tree,
# and the day page lines about one of them (tree.sh). Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_backlinks() {
  local usage="Usage: pkm backlinks <name> [--since YYYY-MM-DD] [--under <note>]"
  local name="" since="" under="" target status dest key US
  US=$(printf '\037')
  while [ $# -gt 0 ]; do
    case $1 in
      --since) { [ $# -ge 2 ] && is_date "$2"; } || die 2 "--since needs a date YYYY-MM-DD"; since=$2; shift 2 ;;
      --under) [ $# -ge 2 ] && [ -n "$2" ] || die 2 "--under needs a note, such as apollo"; under=$2; shift 2 ;;
      *) [ -z "$name" ] || die 2 "$usage"; name=$1; shift ;;
    esac
  done
  [ -n "$name" ] || die 2 "$usage"
  [ -z "$under" ] || under_build "$under"
  target=${name#\[\[}; target=${target%\]\]}; target=${target%%|*}; target=${target%%#*}; target=${target##*/}
  printf '%s\n' "$target" > "$tmp/backlinks-target"
  link_build "$tmp/backlinks-target"
  dest=$(awk -F '\t' -v t="$target" '$1 == t { print $3; exit }' "$tmp/lb-resolved")
  status=$(awk -F '\t' -v t="$target" '$1 == t { print $2; exit }' "$tmp/lb-resolved")
  # A name with no note yet still has backlinks: the lines that write it, as the name is written.
  if [ "$status" = dead ] || [ -z "$dest" ]; then dest=""; fi
  # The lines that link the note.
  awk -F "$(printf '\t')" -v OFS="$US" -v dest="$dest" -v target="$target" '
    (dest != "" && $6 == dest) || (dest == "" && $3 == target) { print $1, $2 }
  ' "$tmp/lb-links" > "$tmp/bl-rows"
  [ -s "$tmp/bl-rows" ] || die 1 "No note or link named $target."
  # And the lines under a ### heading that links it, in the files that link it: about_names gives them with own 0, under
  # the note's name, or the slug of a name with no note.
  if [ -n "$dest" ]; then key=$(basename "$dest" .md)
  else link_slugs "$tmp/backlinks-target" "$tmp/bl-slug"; key=$(cut -f 2 "$tmp/bl-slug"); fi
  cut -d "$US" -f 1 "$tmp/bl-rows" | LC_ALL=C sort -u > "$tmp/bl-files"
  about_pages "$tmp/bl-files" "$tmp/bl-pages"
  about_names "$tmp/bl-pages" "$tmp/bl-names"
  KEY=$key awk -F "$US" -v OFS="$US" '$3 == ENVIRON["KEY"] && $4 == 0 { print $1, $2 }' "$tmp/bl-names" >> "$tmp/bl-rows"
  # --since leaves out the dated pages before the date; --under keeps the lines of the tree.
  awk -F "$US" -v OFS="$US" -v since="$since" '
    { b = $1; sub(/.*\//, "", b)
      if (since != "" && b ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ && substr(b, 1, 10) < since) next
      print }
  ' "$tmp/bl-rows" | LC_ALL=C sort -t "$US" -k1,1 -k2,2n -u > "$tmp/bl-kept"
  [ -z "$under" ] || under_keep "$tmp/bl-kept"
  # Their text, read once from each file that has one.
  ROWS="$tmp/bl-kept" awk -v US="$US" '
    BEGIN {
      while ((getline r < ENVIRON["ROWS"]) > 0) {
        split(r, f, US); key = f[1] SUBSEP f[2]
        if (!(key in want)) order[++n] = key
        want[key] = 1
        if (!(f[1] in seen)) { seen[f[1]] = 1; files[++nf] = f[1] }
      }
      for (k = 1; k <= nf; k++) {
        ln = 0
        while ((getline l < files[k]) > 0) { ln++; sub(/\r$/, "", l); if ((files[k] SUBSEP ln) in want) text[files[k] SUBSEP ln] = l }
        close(files[k])
      }
      for (i = 1; i <= n; i++) if (order[i] in text) {
        split(order[i], f, SUBSEP); t = text[order[i]]; gsub(/\t/, " ", t)
        print f[1] ":" f[2] ": " t
      }
    }
  ' /dev/null
}
