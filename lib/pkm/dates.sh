# shellcheck shell=bash
# lib/pkm/dates.sh: dates for the vault: YYYY-MM-DD arithmetic that works with GNU and BSD date, day words
# such as friday or +3d, and recurrence rules. Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

if date -d 2000-01-01 +%Y >/dev/null 2>&1; then gnu_date=1; else gnu_date=0; fi

# day_add <YYYY-MM-DD> <days>: the date that many days later, or earlier when negative.
day_add() {
  if [ "$gnu_date" = 1 ]; then
    date -d "$1 $2 days" +%Y-%m-%d
  else
    case $2 in -*) date -j -v"$2"d -f %Y-%m-%d "$1" +%Y-%m-%d ;; *) date -j -v+"$2"d -f %Y-%m-%d "$1" +%Y-%m-%d ;; esac
  fi
}

# day_fmt <YYYY-MM-DD> <format>, for example %G-W%V for the ISO week.
day_fmt() {
  if [ "$gnu_date" = 1 ]; then date -d "$1" "+$2"; else date -j -f %Y-%m-%d "$1" "+$2"; fi
}

# day_add_months <YYYY-MM-DD> <months>: the date that many months later, on the same day of the month or the month's last
# day (cycles.sh month_add). It does the arithmetic in awk, so GNU and BSD date agree.
day_add_months() {
  month_add "$1" "$2"
}

is_date() {
  case $1 in [0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]) day_fmt "$1" %Y >/dev/null 2>&1 ;; *) return 1 ;; esac
}

weekday_number() {
  case $1 in
    mon|monday) echo 1 ;; tue|tues|tuesday) echo 2 ;; wed|wednesday) echo 3 ;; thu|thur|thurs|thursday) echo 4 ;;
    fri|friday) echo 5 ;; sat|saturday) echo 6 ;; sun|sunday) echo 7 ;; *) return 1 ;;
  esac
}

# parse_day <word>: YYYY-MM-DD, today, tomorrow, +<n>d, +<n>w, or a weekday: the next one after today.
parse_day() {
  word=$(lowercase "$1")
  case $word in
    today) echo "$today" ;;
    tomorrow) day_add "$today" 1 ;;
    +*)
      n=${word#+} per=1
      case $n in *w) n=${n%w} per=7 ;; *d) n=${n%d} ;; esac
      case $n in ''|*[!0-9]*) return 1 ;; esac
      day_add "$today" $((n * per)) ;;
    *)
      if want=$(weekday_number "$word"); then
        i=1
        while [ "$i" -le 7 ]; do
          d=$(day_add "$today" "$i")
          [ "$(day_fmt "$d" %u)" = "$want" ] && { echo "$d"; return 0; }
          i=$((i + 1))
        done
      fi
      is_date "$word" && echo "$word" ;;
  esac
}

# valid_rule <rule>: day, weekday, weekdays by name ("monday, thursday"), month on <1-31>, or year on <MM-DD>.
valid_rule() {
  rule=$(lowercase "$1")
  case $rule in
    '') return 1 ;;
    day|weekday) return 0 ;;
    "month on "*) n=${rule#month on }; case $n in ''|*[!0-9]*) return 1 ;; esac; [ "$n" -ge 1 ] && [ "$n" -le 31 ] ;;
    "year on "*) case ${rule#year on } in [01][0-9]-[0-3][0-9]) return 0 ;; *) return 1 ;; esac ;;
    *) for w in $(printf '%s' "$rule" | tr ',' ' '); do [ "$w" = and ] || weekday_number "$w" > /dev/null || return 1; done ;;
  esac
}

# awk_dates: the awk functions for days, on civil dates, so they don't depend on the time zone or on GNU or BSD date.
# dnum(y, m, d) is the day number (0 on 1970-01-01), civil(z) sets CY, CM and CD, iso(z) is the date of a day number,
# ymd(s) the day number of a YYYY-MM-DD string, fdiv(a, b) the floor of a / b. is_day(s) is 1 for a calendar date
# written YYYY-MM-DD, wday(z) the weekday (Monday 1, Sunday 7), weekday_n(w) a weekday name's number (0 for none),
# add_months(s, n) the date n months later (the month's last day when it is shorter). day_word(w, page) reads a day word
# as parse_day does, with the page's date as today: YYYY-MM-DD, today, tomorrow, +<n>d, +<n>w, +<n> or a weekday (the
# next one after the page). It gives "" when the word can't be read. relative_word(w) is 1 for a word that needs a page.
awk_dates() {
  cat <<'AWK'
function fdiv(a, b) { return a >= 0 ? int(a / b) : -int((-a + b - 1) / b) }
function dnum(y, m, d,   yy, era, yoe, doy, doe) {
  yy = (m <= 2) ? y - 1 : y
  era = fdiv(yy, 400)
  yoe = yy - era * 400
  doy = int((153 * (m > 2 ? m - 3 : m + 9) + 2) / 5) + d - 1
  doe = yoe * 365 + int(yoe / 4) - int(yoe / 100) + doy
  return era * 146097 + doe - 719468
}
function civil(z,   era, doe, yoe, y, doy, mp) {
  z += 719468
  era = fdiv(z, 146097)
  doe = z - era * 146097
  yoe = int((doe - int(doe / 1460) + int(doe / 36524) - int(doe / 146096)) / 365)
  y = yoe + era * 400
  doy = doe - (365 * yoe + int(yoe / 4) - int(yoe / 100))
  mp = int((5 * doy + 2) / 153)
  CD = doy - int((153 * mp + 2) / 5) + 1
  CM = (mp < 10) ? mp + 3 : mp - 9
  CY = y + (CM <= 2)
}
function iso(z) { civil(z); return sprintf("%04d-%02d-%02d", CY, CM, CD) }
function ymd(s) { return dnum(substr(s, 1, 4) + 0, substr(s, 6, 2) + 0, substr(s, 9, 2) + 0) }
function is_day(s) { return s ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$/ && iso(ymd(s)) == s }
function wday(z) { return ((z + 3) % 7 + 7) % 7 + 1 }
function weekday_n(w) {
  if (w == "mon" || w == "monday") return 1
  if (w == "tue" || w == "tues" || w == "tuesday") return 2
  if (w == "wed" || w == "wednesday") return 3
  if (w == "thu" || w == "thur" || w == "thurs" || w == "thursday") return 4
  if (w == "fri" || w == "friday") return 5
  if (w == "sat" || w == "saturday") return 6
  if (w == "sun" || w == "sunday") return 7
  return 0
}
function add_months(s, n,   mi, ny, nm, first, dim, dd) {
  dd = substr(s, 9, 2) + 0
  mi = (substr(s, 1, 4) + 0) * 12 + substr(s, 6, 2) - 1 + n; ny = fdiv(mi, 12); nm = mi - ny * 12 + 1
  first = dnum(ny, nm, 1)
  dim = ((nm == 12) ? dnum(ny + 1, 1, 1) : dnum(ny, nm + 1, 1)) - first
  return iso(first + ((dd < dim) ? dd : dim) - 1)
}
function day_word_clean(w) { w = tolower(w); gsub(/[ \t]+/, " ", w); sub(/^ /, "", w); sub(/ $/, "", w); return w }
function day_word_offset(w,   per) {
  if (w !~ /^\+[0-9]+[dw]?$/) return -1
  per = (w ~ /w$/) ? 7 : 1; sub(/^\+/, "", w); sub(/[dw]$/, "", w)
  return (w + 0) * per
}
function relative_word(w) {
  w = day_word_clean(w)
  return w == "today" || w == "tomorrow" || day_word_offset(w) >= 0 || weekday_n(w) > 0
}
function day_word(w, page,   z, n) {
  w = day_word_clean(w)
  if (is_day(w)) return w
  if (!is_day(page)) return ""
  z = ymd(page)
  if (w == "today") return page
  if (w == "tomorrow") return iso(z + 1)
  n = day_word_offset(w); if (n >= 0) return iso(z + n)
  n = weekday_n(w); if (n > 0) return iso(z + (n - wday(z) + 6) % 7 + 1)
  return ""
}
AWK
}
