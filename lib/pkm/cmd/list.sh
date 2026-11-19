# shellcheck shell=bash
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cmd/list.sh: pkm list: the notes whose frontmatter matches the field=value filters, from the cache. Each line is
# path, type, title, then the fields named by --show (- when a note has none). A field matches a value when the value is,
# or contains as a word, the value asked for (case and brackets ignored). The archive is left out unless --all.
# --under <note> keeps the notes of the note's tree (tree.sh).
# Sourced by bin/pkm. Defines functions only.

cmd_list() {
  local all=no show="" filters="" tab quiet="" quiet_mode=no under=""
  tab=$(printf '\t')
  while [ $# -gt 0 ]; do
    case $1 in
      --all) all=yes; shift ;;
      --quiet) [ $# -ge 2 ] || die 2 "--quiet needs a number of days"; number "$2" "--quiet"; quiet=$2; quiet_mode=yes; shift 2 ;;
      --under) [ $# -ge 2 ] && [ -n "$2" ] || die 2 "--under needs a note, such as apollo"; under=$2; shift 2 ;;
      --show) [ $# -ge 2 ] || die 2 "--show needs field names"; show=$2; shift 2 ;;
      *=*) filters="$filters$1
"; shift ;;
      *) die 2 "Usage: pkm list [<field>=<value> ...] [--show <field>,...] [--under <note>] [--all]" ;;
    esac
  done
  index_ensure
  : > "$tmp/under-paths"
  [ -z "$under" ] || under_build "$under"
  if [ "$quiet_mode" = yes ]; then
    # The notes a day page in the last <quiet> days links, by name, slug or alias: those are not quiet.
    link_build ""
    local start
    start=$(day_add "$today" $((1 - quiet)))
    awk -F "$tab" -v start="$start" -v today="$today" \
      '$2 == "day" && substr($1, 1, 10) >= start && substr($1, 1, 10) <= today { print $3 }' \
      "$(cache_dir)/names.tsv" > "$tmp/quiet-days"
    awk -F "$tab" 'NR == FNR { day[$0] = 1; next } ($1 in day) && $6 != "" { print $6 }' \
      "$tmp/quiet-days" "$tmp/lb-links" | LC_ALL=C sort -u > "$tmp/quiet-linked"
  fi
  UNDER=$under TREE="$tmp/under-paths" QUIET=$quiet_mode LINKED="$tmp/quiet-linked" FILTERS=$filters SHOW=$show ALL=$all awk -F "$tab" -v OFS="$tab" '
    function value_has(value, want,   v, parts, n, i) {
      v = tolower(value); want = tolower(want); gsub(/[][\"'"'"']/, " ", v)
      gsub(/^[ ,]+|[ ,]+$/, "", v)
      if (v == want) return 1
      n = split(v, parts, /[ ,]+/)
      for (i = 1; i <= n; i++) if (parts[i] == want) return 1
      return 0
    }
    function field_of(path, key) {
      if (key == "type") return type[path]
      if (key == "title") return title[path]
      return ((path SUBSEP key) in fv) ? fv[path, key] : "-"
    }
    BEGIN {
      n = split(ENVIRON["FILTERS"], raw, "\n")
      for (i = 1; i <= n; i++) if (raw[i] != "") { nf++; fk[nf] = substr(raw[i], 1, index(raw[i], "=") - 1); fw[nf] = substr(raw[i], index(raw[i], "=") + 1) }
      ns = split(ENVIRON["SHOW"], shown, ",")
      if (ENVIRON["UNDER"] != "") { while ((getline p < ENVIRON["TREE"]) > 0) tree[p] = 1; close(ENVIRON["TREE"]) }
      if (ENVIRON["QUIET"] == "yes") { while ((getline p < ENVIRON["LINKED"]) > 0) linked[p] = 1; close(ENVIRON["LINKED"]) }
    }
    FILENAME == ARGV[1] { fv[$1, $2] = $3; next }
    {
      path = $1; title[path] = $2; type[path] = $3
      if (ENVIRON["ALL"] != "yes" && path ~ /^archive\//) next
      if (ENVIRON["UNDER"] != "" && !(path in tree)) next
      if (ENVIRON["QUIET"] == "yes" && (type[path] == "day" || type[path] == "close" || (path in linked))) next
      for (i = 1; i <= nf; i++) if (!value_has(field_of(path, fk[i]), fw[i])) next
      line = path OFS type[path] OFS title[path]
      for (i = 1; i <= ns; i++) line = line OFS field_of(path, shown[i])
      print line
    }
  ' "$(cache_dir)/fields.tsv" "$(cache_dir)/notes.tsv"
}
