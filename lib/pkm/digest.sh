# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/digest.sh: what since and close read from the day pages. digest_pages collects the lines of the day pages dated in
# a range; digest_names the names each line is about (about.sh). Both write US-separated files in $tmp, with \037
# between the fields. Sourced by bin/pkm. Defines functions only.

# digest_pages <from> <to>: $tmp/dg-pages, one row per non-blank line of the day pages dated from <from> to <to>:
# path, date, line, kind, text, as about_pages writes them.
digest_pages() {
  local from=$1 to=$2
  index_ensure
  awk -F "$(printf '\t')" -v from="$from" -v to="$to" \
    '$2 == "day" && substr($1, 1, 10) >= from && substr($1, 1, 10) <= to { print $3 }' "$(cache_dir)/names.tsv" \
    | LC_ALL=C sort > "$tmp/dg-day-files"
  about_pages "$tmp/dg-day-files" "$tmp/dg-pages"
}

# digest_names: $tmp/dg-names, one row per name a line is about (about_names): path, line, name, own, date. Needs
# digest_pages first.
digest_names() {
  about_names "$tmp/dg-pages" "$tmp/dg-names"
}
