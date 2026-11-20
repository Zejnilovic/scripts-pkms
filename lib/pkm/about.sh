# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/about.sh: the lines about a name. A line is about a name when it links the name, or sits in the block of a ###
# heading that links it. The block ends at the next heading of level 1, 2 or 3, or at a blank line after its lines that
# is followed by an entry (- HH:MM …). Used by since --about and the digest, and by --under and
# backlinks. Files are US-separated, with \037 between the fields. Sourced by bin/pkm. Defines functions only.

# about_pages <files list> <out>: one row per non-blank line of the files listed, outside the frontmatter: path, date,
# line, kind, text, sorted by path and line. date is the date a day page's name starts with, and empty for a file whose
# name starts with none. The kind is t for the title, x for the ## Tasks and ## Log headings, r for a line with a
# (recall …), and l for any other line.
about_pages() {
  local US
  US=$(printf '\037')
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$1" '
    FNR == 1 {
      file = rel(FILENAME); date = substr(base(file), 1, 10); title_done = 0; front = 0
      if (date !~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/) date = ""
    }
    FNR == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") front = 0; next }
    /[^ \t]/ {
      kind = "l"
      if (!title_done && $0 ~ /^# /) { kind = "t"; title_done = 1 }
      else if ($0 == "## Tasks" || $0 == "## Log") kind = "x"
      if (kind == "l" && $0 ~ /\(recall [^)]*\)[ \t]*$/) kind = "r"
      print file US date US FNR US kind US $0
    }
  ' -v US="$US" | LC_ALL=C sort -t "$US" -k1,1 -k3,3n > "$2"
}

# about_names <pages> <out>: one row per name a line is about: path, line, name, own, date. A name is the note's name, or
# the slug of a link to no note. Links to day, close and attachment pages are not names. own is 1 for a link on the line
# itself, and 0 for a name of the ### heading the line sits under. The rows with own 1 come for every line that has a
# link, with an empty date; the lines of the pages (from about_pages) add theirs again with their date, and their
# heading's names. Sorted, with no row twice.
about_names() {
  local US
  US=$(printf '\037')
  index_ensure
  link_build ""
  awk -F '\t' '$6 == "" { print $3 }' "$tmp/lb-links" | LC_ALL=C sort -u > "$tmp/an-dead"
  link_slugs "$tmp/an-dead" "$tmp/an-slugs"
  awk -F '\t' -v US="$US" -v slugs="$tmp/an-slugs" -v types="$(cache_dir)/names.tsv" '
    BEGIN {
      while ((getline l < slugs) > 0) { split(l, f, "\t"); slug[f[1]] = f[2] }
      close(slugs)
      while ((getline l < types) > 0) { split(l, g, "\t"); ty[g[3]] = g[2] }
      close(types)
    }
    {
      if ($6 == "") n = slug[$3]
      else {
        t = ty[$6]
        if (t == "day" || t == "close" || t == "attachment") next
        n = $6; sub(/.*\//, "", n); sub(/\.md$/, "", n)
      }
      print $1 US $2 US n US 1 US ""
    }
  ' "$tmp/lb-links" > "$tmp/an-own"
  # Each line of the pages gets its own names, and those of the ### heading whose block it is in. The pages have no blank
  # lines, so a blank line shows as a gap in the line numbers.
  awk -F "$US" -v OFS="$US" -v US="$US" '
    FILENAME == ARGV[1] { own[$1 SUBSEP $2] = own[$1 SUBSEP $2] "|" $3; next }
    function emit(s, o,   arr, n, i) {
      if (s == "") return
      n = split(s, arr, "|")
      for (i = 1; i <= n; i++) if (arr[i] != "") print path US line US arr[i] US o US date
    }
    {
      path = $1; line = $3; text = $5; date = $2
      if (path != lastpath) { lastpath = path; cur = ""; prev = 0 }
      mine = own[path SUBSEP line]
      if (text ~ /^##? /) cur = ""
      if (text ~ /^### /) { cur = mine; seen = 0; prev = line; emit(mine, 1); next }
      if (seen && line > prev + 1 && text ~ /^- [0-2][0-9]:[0-5][0-9] /) cur = ""
      emit(mine, 1)
      emit(cur, 0)
      seen = 1; prev = line
    }
  ' "$tmp/an-own" "$1" > "$tmp/an-page-names"
  LC_ALL=C sort -u "$tmp/an-own" "$tmp/an-page-names" > "$2"
}

# about_key <name>: the name as about_names writes it: the name of the note it means (a path in the vault, a name, a
# slug, an alias or a [[link]]), else its slug, for a name with no note yet. Callers have run index_ensure.
about_key() {
  local name=$1 target
  name=${name#\[\[}; name=${name%\]\]}; name=${name%%|*}
  target=$(note_for "$name")
  if [ -n "$target" ]; then basename "$target" .md; return 0; fi
  printf '%s\n' "$name" > "$tmp/ak-name"
  link_slugs "$tmp/ak-name" "$tmp/ak-slug"
  cut -f 2 "$tmp/ak-slug"
}
