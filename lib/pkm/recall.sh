# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/recall.sh: recall questions. A question is an entry that ends with a recall mark, (recall YYYY-MM-DD <N>d): the day
# to ask it, and the current interval in days. The lines indented under it are the answer, which pkm doesn't read. Marks
# outside code count; a struck line is history and never comes up. Sourced by bin/pkm. Defines functions only.

# recall_awk: the awk functions. recall_inner(c) is the text of the mark at the end of c (code removed first), or "";
# recall_parse(inner) sets RDATE and RDAYS and succeeds when inner is a valid "<date> <N>d".
recall_awk() {
  cat <<'AWK'
function days_in(y, m,   d) {
  split("31 28 31 30 31 30 31 31 30 31 30 31", d, " ")
  if (m == 2 && (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0))) return 29
  return d[m] + 0
}
function recall_date_ok(s,   y, m, dd) {
  if (s !~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/) return 0
  y = substr(s, 1, 4) + 0; m = substr(s, 6, 2) + 0; dd = substr(s, 9, 2) + 0
  return m >= 1 && m <= 12 && dd >= 1 && dd <= days_in(y, m)
}
function recall_inner(c,   m) {
  if (!match(c, /\(recall [^)]*\)[ \t]*$/)) return ""
  m = substr(c, RSTART, RLENGTH)
  sub(/^\(recall /, "", m); sub(/\)[ \t]*$/, "", m)
  return m
}
function recall_parse(inner,   p) {
  if (inner !~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9]+d$/) return 0
  split(inner, p, " ")
  if (!recall_date_ok(p[1])) return 0
  RDATE = p[1]; RDAYS = substr(p[2], 1, length(p[2]) - 1) + 0
  return 1
}
AWK
}

# recall_rung <days> <yes|no>: the interval after an answer: no is 1 day; yes is the next rung of 1 3 7 14 30 60 120 above
# the current interval (120 stays 120; an interval off the ladder goes to the next rung above it).
recall_rung() {
  local n=$1 r
  if [ "$2" = no ]; then echo 1; return 0; fi
  for r in 1 3 7 14 30 60 120; do
    if [ "$r" -gt "$n" ]; then echo "$r"; return 0; fi
  done
  echo 120
}
