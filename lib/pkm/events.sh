# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/events.sh: events (docs/format.md, Events): lines with (at <when>), or (@ <when>), from the line scanner. An
# event is listed on each of its days; one in a note can come back with (every <n><d|w|m|y>), (until D) and (skip D),
# its times counted from the date in its (at …). Events on close pages, in archive/ and in closed notes are not read.
# Sourced by bin/pkm. Defines functions only.

# awk_events: the awk functions for events. It needs awk_dates in front of it.
# event_when(v, page) reads the value of an (at …) on a page with that date (or ""): it returns "" and sets EV_FIRST and
# EV_LAST (the first and last day), EV_START and EV_END (HH:MM, or "") when it can, or returns the problem.
# event_rule_ok(r) is 1 for an interval such as 1w. event_days(first, last, rule, until, skips, from, to, out) puts the
# days of the event from <from> to <to> in out[1..n], each time but the skipped ones, and returns n.
# event_readable(type, status) is 0 for a close page and a closed note, whose lines are not read as events.
awk_events() {
  cat <<'AWK'
function event_readable(type, status) {
  return type != "close" && status !~ /^(done|dropped|published|sold|gone|archived)$/
}
function event_hhmm(s) { return s ~ /^[0-2][0-9]:[0-5][0-9]$/ && substr(s, 1, 2) + 0 < 24 }
function event_day(w, page,   r) {
  if (is_day(w)) return w
  if (!relative_word(w)) return "?"
  if (page == "") return "relative"
  r = day_word(w, page)
  return (r == "") ? "?" : r
}
function event_when(v, page,   p) {
  p = event_when_read(v, page)
  if (p != "") { EV_FIRST = ""; EV_LAST = ""; EV_START = ""; EV_END = "" }
  return p
}
function event_when_read(v, page,   n, a, d, d2, t, i, dash) {
  EV_FIRST = ""; EV_LAST = ""; EV_START = ""; EV_END = ""
  gsub(/[ \t]+/, " ", v); sub(/^ /, "", v); sub(/ $/, "", v)
  n = split(v, a, " ")
  d = event_day(a[1], page)
  if (d == "relative") return "relative date " a[1] " is outside a day page: write its date"
  if (d == "?") return "cannot read the event time " v
  EV_FIRST = d; EV_LAST = d
  if (n == 1) return ""
  if (n == 3 && tolower(a[2]) == "to") {
    d2 = event_day(a[3], page)
    if (d2 == "relative") return "relative date " a[3] " is outside a day page: write its date"
    if (d2 == "?") return "cannot read the event time " v
    if (d2 < d) return "an event ends before it starts: " v
    EV_LAST = d2
    return ""
  }
  if (n == 2) {
    # The en dash is found as a string, and measured: awks differ on byte escapes in a regular expression, and gawk
    # in a UTF-8 locale counts it as one character.
    t = a[2]; dash = "\342\200\223"; i = index(t, dash); if (i > 0) t = substr(t, 1, i - 1) "-" substr(t, i + length(dash))
    if (event_hhmm(t)) { EV_START = t; return "" }
    i = index(t, "-")
    if (i > 0 && event_hhmm(substr(t, 1, i - 1)) && event_hhmm(substr(t, i + 1))) {
      EV_START = substr(t, 1, i - 1); EV_END = substr(t, i + 1)
      if (EV_START == EV_END) return "a time range ends when it starts: " v
      return ""
    }
  }
  return "cannot read the event time " v
}
function event_rule_ok(r) { return r ~ /^[0-9]+[dwmy]$/ && substr(r, 1, length(r) - 1) + 0 >= 1 }
function event_span(s, dur, zf, zt, out, n,   z, e) {
  z = (s > zf) ? s : zf; e = (s + dur < zt) ? s + dur : zt
  for (; z <= e; z++) out[++n] = iso(z)
  return n
}
function event_days(first, last, rule, until, skips, from, to, out,   n, dur, z0, zf, zt, zu, num, unit, step, k, s, months, mi) {
  n = 0; z0 = ymd(first); dur = ymd(last) - z0; zf = ymd(from); zt = ymd(to); zu = (until == "") ? zt : ymd(until)
  if (rule == "") return event_span(z0, dur, zf, zt, out, 0)
  num = substr(rule, 1, length(rule) - 1) + 0; unit = substr(rule, length(rule))
  skips = " " skips " "
  if (unit == "d" || unit == "w") {
    step = num * ((unit == "w") ? 7 : 1)
    k = (zf - dur - z0 > 0) ? int((zf - dur - z0) / step) : 0
    for (; (s = z0 + k * step) <= zt && s <= zu; k++)
      if (!index(skips, " " iso(s) " ")) n = event_span(s, dur, zf, zt, out, n)
    return n
  }
  months = num * ((unit == "y") ? 12 : 1)
  mi = (substr(from, 1, 4) - substr(first, 1, 4)) * 12 + substr(from, 6, 2) - substr(first, 6, 2) - 1 - int(dur / 28)
  k = (mi > 0) ? int(mi / months) : 0
  for (; (s = ymd(add_months(first, k * months))) <= zt && s <= zu; k++)
    if (s + dur >= zf && !index(skips, " " iso(s) " ")) n = event_span(s, dur, zf, zt, out, n)
  return n
}
function event_skips(m,   n, a, i, out) {
  out = ""; n = split(m, a, "\t")
  for (i = 1; i <= n; i++) if (substr(a[i], 1, 5) == "skip ") out = out " " substr(a[i], 6)
  return out
}
AWK
}

# event_lines <from> <to>: the events' days from one date to another, as "<sort key>US<date> event path:line: text".
# The key sorts a day's events by start time, the whole-day ones first, then by path and line.
event_lines() {
  line_records no | awk -F '\037' -v from="$1" -v to="$2" "$(awk_dates)$(awk_markers)$(awk_events)"'
    $3 != "event" || !event_readable($8, $9) { next }
    {
      if (event_when(mval($5, "at"), $6) != "") next
      rule = mval($5, "every"); until = mval($5, "until")
      if (rule != "" && ($6 != "" || !event_rule_ok(rule))) rule = ""
      if (rule == "" || !is_day(until)) until = ""
      n = event_days(EV_FIRST, EV_LAST, rule, until, (rule == "") ? "" : event_skips($5), from, to, day)
      for (i = 1; i <= n; i++)
        print day[i] " event " ((EV_START == "") ? "-" : EV_START) " " $1 ":" $2 "\037" day[i] " event " $1 ":" $2 ": " $10
    }'
}

# event_problems: the check problems of events (docs/format.md, Events 6), as "- path:line: problem". A task's (at …)
# that can't be read is reported with the task (task_records).
event_problems() {
  line_records no | awk -F '\037' "$(awk_dates)$(awk_markers)$(awk_events)"'
    function report(p) { print "- " $1 ":" $2 ": " p }
    !event_readable($8, $9) { next }
    {
      m = $5; rule = mval(m, "every"); back = 0
      if ($3 == "event") {
        p = event_when(mval(m, "at"), $6)
        if (p != "") report(p)
        if (rule != "") {
          if ($6 != "") report("an event comes back only from a note: a day page is a record, so move (every " rule ") to a note")
          else if (!event_rule_ok(rule)) report("an event comes back on an interval, such as (every 1w), not (every " rule ")")
          else back = 1
        }
      } else if ($3 == "task" && mhas(m, "at") && rule != "")
        report("(every " rule ") with an (at …) in a task box: an event that comes back has no box, so take out the box or the (at …)")
      n = split(m, a, "\t")
      for (i = 1; i <= n; i++) {
        key = a[i]; sub(/ .*/, "", key)
        if (key != "until" && key != "skip") continue
        if (!back) { report("(" key " …) belongs on an event that comes back: one in a note with (at …) and (every …)"); continue }
        v = substr(a[i], length(key) + 2)
        if (!is_day(v)) report("cannot read the date in (" a[i] ")")
      }
    }'
}
