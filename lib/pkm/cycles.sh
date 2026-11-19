# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/cycles.sh: the cycles of a vault and their periods. The week is built in: 1w from monday. A cycle of your own is
# set in .pkm/config as cycle_<name>=<N>w from <weekday|date> (a weekday only for 1w), or cycle_<name>=<N>m from <day 1-28
# or date>. A period runs from its first day to the day before the next period starts, and periods run both ways from
# the anchor. Day arithmetic is done in awk on civil dates (dates.sh awk_dates), so it does not depend on the time zone. Sourced by bin/pkm.
# Defines functions only.

# cycle_value_parse <value>: "unit n kind anchor" for a cycle's value, or nothing and a failure when the value is not one.
# kind is wday (a weekday, Monday 0), date (a day number's date, as written) or dom (a day of the month).
cycle_value_parse() {
  local v=$1 unit n anchor wd
  case $v in
    *w\ from\ *) unit=w ;;
    *m\ from\ *) unit=m ;;
    *) return 1 ;;
  esac
  n=${v%%[wm]*}
  case $n in ''|*[!0-9]*) return 1 ;; esac
  [ "$n" -ge 1 ] || return 1
  anchor=${v#* from }
  if is_date "$anchor"; then printf '%s %s date %s\n' "$unit" "$n" "$anchor"; return 0; fi
  if [ "$unit" = w ]; then
    [ "$n" = 1 ] || return 1
    wd=$(weekday_number "$(lowercase "$anchor")") || return 1
    printf 'w 1 wday %s\n' "$((wd - 1))"
    return 0
  fi
  case $anchor in ''|*[!0-9]*) return 1 ;; esac
  [ "$anchor" -ge 1 ] && [ "$anchor" -le 28 ] || return 1
  printf 'm %s dom %s\n' "$n" "$anchor"
}

# cycle_name_problem <name>: why a cycle name can't be used, or nothing when it can: lowercase letters, digits and
# hyphens, not week, last, today or yesterday, and not all digits.
cycle_name_problem() {
  case $1 in
    ''|*[!a-z0-9-]*) echo "a cycle name is lowercase letters, digits and hyphens: $1" ;;
    week|last|today|yesterday) echo "$1 is a reserved name: pick another cycle name" ;;
    *[!0-9]*) ;;
    *) echo "a cycle name is not all digits: $1" ;;
  esac
}

# cycle_names: the names of the cycles set in .pkm/config, sorted, one per line.
cycle_names() {
  file_keys .pkm/config | sed -n 's/^cycle_\(.\{1,\}\)$/\1/p' | LC_ALL=C sort
}

# cycle_known <name>: succeeds for week and for a cycle set in .pkm/config.
cycle_known() {
  [ "$1" = week ] && return 0
  [ -n "$(file_value .pkm/config "cycle_$1")" ]
}

# cycle_spec <name>: the parsed definition of a cycle (see cycle_value_parse). Fails for an unknown name.
cycle_spec() {
  local value
  if [ "$1" = week ]; then printf 'w 1 wday 0\n'; return 0; fi
  value=$(file_value .pkm/config "cycle_$1")
  [ -n "$value" ] || return 1
  cycle_value_parse "$value"
}

# cycle_period <name> <date>: "first last" of the period holding the date. Fails for an unknown cycle.
cycle_period() {
  local spec unit n kind val
  spec=$(cycle_spec "$1") || return 1
  read -r unit n kind val <<EOF
$spec
EOF
  awk -v unit="$unit" -v n="$n" -v kind="$kind" -v val="$val" -v d="$2" "$(awk_dates)"'
    BEGIN {
      z = ymd(d)
      if (unit == "w") {
        L = 7 * n
        if (kind == "wday") {
          wd = ((z + 3) % 7 + 7) % 7
          first = z - ((wd - val) % 7 + 7) % 7
        } else {
          a = ymd(val); first = a + fdiv(z - a, L) * L
        }
        last = first + L - 1
      } else {
        if (kind == "dom") { D = val + 0; base = 1970 * 12 }
        else { D = substr(val, 9, 2) + 0; base = (substr(val, 1, 4) + 0) * 12 + (substr(val, 6, 2) + 0) - 1 }
        civil(z)
        mi = CY * 12 + CM - 1
        cand = (CD >= D) ? mi : mi - 1
        smi = base + fdiv(cand - base, n) * n
        first = dnum(int(smi / 12), smi % 12 + 1, D)
        nmi = smi + n
        last = dnum(int(nmi / 12), nmi % 12 + 1, D) - 1
      }
      print iso(first) " " iso(last)
    }'
}

# cycle_period_last <name> <date>: the last day of the period holding the date.
cycle_period_last() {
  cycle_period "$1" "$2" | cut -d ' ' -f 2
}

# day_diff <from> <to>: the days from one date to another (negative when earlier).
day_diff() {
  awk -v a="$1" -v b="$2" "$(awk_dates)"' BEGIN { print ymd(b) - ymd(a) }'
}

# month_add <date> <months>: the date that many months later, on the same day of the month, or the last day of that month
# when it is shorter (January 31 plus one month is February 28).
month_add() {
  awk -v d="$1" -v n="$2" "$(awk_dates)"' BEGIN { print add_months(d, n) }'
}

# cycle_routine_due <name>: the due date of an undated cycle routine: the last day of the period holding today.
cycle_routine_due() {
  cycle_period_last "$1" "$today"
}
