# shellcheck shell=bash
# lib/pkm/links.sh: how a link finds its note. A link names a note by its file name, by the slug of its text, or by an
# alias in the note's frontmatter, in that order. Every command that follows links (check, find, backlinks, path)
# uses link_build, so they agree. Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# link_index <out>: the names and aliases a link can use, from the cache (index.sh): N<TAB>name<TAB>path for a note (its
# file name without .md), F<TAB>file name<TAB>path for any other file, and A<TAB>alias<TAB>path for each alias.
link_index() {
  index_ensure
  awk -F "$(printf '\t')" -v OFS="$(printf '\t')" '
    $2 == "attachment" { print "F", $1, $3; next }
    { print "N", $1, $3
      if ($4 != "") { n = split($4, a, ","); for (i = 1; i <= n; i++) if (a[i] != "") print "A", a[i], $3 } }
  ' "$(cache_dir)/names.tsv" | LC_ALL=C sort -s -t "$(printf '\t')" -k3,3 > "$1"
}

# link_occurrences <out>: the links of the notes, from the cache (index.sh): path, line, target, and an empty text, which
# backlinks reads from the note only for the lines it prints.
link_occurrences() {
  index_ensure
  awk -F "$(printf '\t')" -v OFS="$(printf '\t')" '{ print $1, $2, $3, "" }' "$(cache_dir)/links.tsv" > "$1"
}

# link_slugs <texts file> <out>: text<TAB>slug for each line of the texts file, with the same slug as slugify.
link_slugs() {
  LC_ALL=C sed "$translit" "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]' \
    | LC_ALL=C sed -e 's/[^a-z0-9][^a-z0-9]*/-/g' -e 's/^-//' -e 's/-$//' > "$tmp/slug-values"
  paste "$1" "$tmp/slug-values" > "$2"
}

# link_resolve <index> <slugs> <out>: text<TAB>status<TAB>path for each text in the slugs file. Status is exact (the
# file name, with or without .md), slug (the slug of the text is a file name), alias, or dead. Path is empty when dead.
link_resolve() {
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  awk -F '\t' '
    FILENAME == ARGV[1] {
      if ($1 == "N" || $1 == "F") { if (!($2 in name)) name[$2] = $3 }
      else if ($1 == "A") { alias_text[++na] = $2; alias_path[na] = $3 }
      next
    }
    FILENAME == ARGV[2] { text[++nt] = $1; slug[$1] = $2; next }
    END {
      for (i = 1; i <= na; i++) {
        s = slug[alias_text[i]]
        if (s != "" && !(s in aliasslug)) aliasslug[s] = alias_path[i]
        if (!(alias_text[i] in alias)) alias[alias_text[i]] = alias_path[i]
      }
      for (i = 1; i <= nt; i++) {
        t = text[i]; s = slug[t]; st = "dead"; dest = ""
        if (t in name) { st = "exact"; dest = name[t] }
        else if (t ~ /\.md$/ && substr(t, 1, length(t) - 3) in name) { st = "exact"; dest = name[substr(t, 1, length(t) - 3)] }
        else if (s != "" && s in name) { st = "slug"; dest = name[s] }
        else if (t in alias) { st = "alias"; dest = alias[t] }
        else if (s != "" && s in aliasslug) { st = "alias"; dest = aliasslug[s] }
        print t "\t" st "\t" dest
      }
    }
  ' "$1" "$2" > "$3"
}

# link_build <extra texts file or empty>: fills $tmp/lb-index (the names and aliases), $tmp/lb-slugs and
# $tmp/lb-links: path<TAB>line<TAB>target<TAB>text<TAB>status<TAB>path, one line per link in the notes. The extra
# file adds texts to resolve (a name typed on the command line), and is resolved into $tmp/lb-resolved.
link_build() {
  link_index "$tmp/lb-index"
  link_occurrences "$tmp/lb-occurrences"
  {
    awk -F "$(printf '\t')" '$1 == "N" || $1 == "F" || $1 == "A" { print $2 }' "$tmp/lb-index"
    cut -f3 "$tmp/lb-occurrences"
    if [ -n "$1" ]; then cat "$1"; fi
  } | LC_ALL=C sort -u > "$tmp/lb-texts"
  link_slugs "$tmp/lb-texts" "$tmp/lb-slugs"
  link_resolve "$tmp/lb-index" "$tmp/lb-slugs" "$tmp/lb-resolved"
  awk -F '\t' -v OFS='\t' '
    NR == FNR { status[$1] = $2; path[$1] = $3; next }
    { t = $3
      if (t in status) print $1, $2, $3, $4, status[t], path[t]
      else print $1, $2, $3, $4, "dead", ""
    }
  ' "$tmp/lb-resolved" "$tmp/lb-occurrences" > "$tmp/lb-links"
}

# external_addresses <list file>: path<TAB>line<TAB>address for each http(s) address outside code, in the notes listed
# (one line per address on a line; bare or in [text](url)). A trailing punctuation mark is not part of the address.
external_addresses() {
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$1" '
    FNR == 1 { file = rel(FILENAME); fence = 0 }
    /^[ \t]*(```|~~~)/ { fence = !fence; next }
    fence { next }
    {
      s = $0; gsub(/`[^`]*`/, "", s); seen = "|"
      while (match(s, /https?:\/\/[^] \t<>()"'"'"'`[]+/)) {
        u = substr(s, RSTART, RLENGTH); s = substr(s, RSTART + RLENGTH)
        sub(/[.,;:!?]+$/, "", u)
        if (index(seen, "|" u "|") == 0) { seen = seen u "|"; print file "\t" FNR "\t" u }
      }
    }
  '
}
