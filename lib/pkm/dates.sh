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

