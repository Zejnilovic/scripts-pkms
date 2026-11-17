# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/digest.sh: what since and close read from the day pages. digest_pages collects the lines of the day pages dated in
# a range; digest_names the names each line links. Both write US-separated files in $tmp, with \037 between the fields.
# Sourced by bin/pkm. Defines functions only.

# digest_pages <from> <to>: $tmp/dg-pages, one row per non-blank line of the day pages dated from <from> to <to>:
# path, date, line, kind, text. The kind is t for the title, x for the ## Tasks and ## Log headings, and l for any other line.
digest_pages() {
  local US from=$1 to=$2
  US=$(printf '\037')
  index_ensure
  awk -F "$(printf '\t')" -v from="$from" -v to="$to" \
    '$2 == "day" && substr($1, 1, 10) >= from && substr($1, 1, 10) <= to { print $3 }' "$(cache_dir)/names.tsv" \
    | LC_ALL=C sort > "$tmp/dg-day-files"
  # shellcheck disable=SC2016 # awk program: the $ in it is awk's, not the shell's
  scan "$tmp/dg-day-files" '
    FNR == 1 { file = rel(FILENAME); date = substr(base(file), 1, 10); title_done = 0; front = 0 }
    FNR == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") front = 0; next }
    /[^ \t]/ {
      kind = "l"
      if (!title_done && $0 ~ /^# /) { kind = "t"; title_done = 1 }
      else if ($0 == "## Tasks" || $0 == "## Log") kind = "x"
      if (kind == "l" && $0 ~ /\(recall [^)]*\)[ \t]*$/) kind = "r"
      print file US date US FNR US kind US $0
    }
  ' -v US="$US" | LC_ALL=C sort -t "$US" -k1,1 -k3,3n > "$tmp/dg-pages"
}

# digest_names: $tmp/dg-names, one row per link name a line has: path, line, name, own, date. A name is the note's name, or
# the slug of a link to no note. Links to day, close and attachment pages are not names. own is 1 for a link on the line
# itself, and 0 for a link inherited from the ### heading the line sits under (day pages). date is the day page's date, for
# the day page lines. Needs digest_pages first.
digest_names() {
  local US
  US=$(printf '\037')
  index_ensure
  link_build ""
  awk -F '\t' '$6 == "" { print $3 }' "$tmp/lb-links" | LC_ALL=C sort -u > "$tmp/dg-dead"
  link_slugs "$tmp/dg-dead" "$tmp/dg-slugs"
  awk -F '\t' -v US="$US" -v slugs="$tmp/dg-slugs" -v types="$(cache_dir)/names.tsv" '
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
  ' "$tmp/lb-links" > "$tmp/dg-own"
  # Each day page line gets its own names, and those of the ### heading above it (until the next heading of level 1 or 2).
  awk -F "$US" -v OFS="$US" -v US="$US" '
    FILENAME == ARGV[1] { own[$1 SUBSEP $2] = own[$1 SUBSEP $2] "|" $3; next }
    function emit(s, o,   arr, n, i) {
      if (s == "") return
      n = split(s, arr, "|")
      for (i = 1; i <= n; i++) if (arr[i] != "") print path US line US arr[i] US o US date
    }
    {
      path = $1; line = $3; text = $5; date = $2
      if (path != lastpath) { lastpath = path; cur = "" }
      mine = own[path SUBSEP line]
      if (text ~ /^##? /) cur = ""
      if (text ~ /^### /) { cur = mine; emit(mine, 1); next }
      emit(mine, 1)
      emit(cur, 0)
    }
  ' "$tmp/dg-own" "$tmp/dg-pages" > "$tmp/dg-day-names"
  LC_ALL=C sort -u "$tmp/dg-own" "$tmp/dg-day-names" > "$tmp/dg-names"
}
