# shellcheck shell=bash
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"
# lib/pkm/state.sh: what pkm remembers between runs, in .pkm/state: since=<date> <HH:MM>, where the next since last starts
# and the time it was seen. An older state with only a date still reads. Only since --seen writes it. Sourced by bin/pkm.
# Defines functions only.

# state_since: the date in .pkm/state, or nothing when there is none.
state_since() {
  local value
  value=$(file_value .pkm/state since)
  printf '%s\n' "${value%% *}"
}

# state_since_time: the time in .pkm/state (HH:MM), or nothing when the state has only a date.
state_since_time() {
  local value
  value=$(file_value .pkm/state since)
  case $value in
    *" "*) printf '%s\n' "${value#* }" ;;
  esac
}

# state_write_since <date> <HH:MM>: writes .pkm/state with that date and time, through a temporary file.
state_write_since() {
  mkdir -p .pkm || die 1 "Can't make .pkm in the vault."
  printf 'since=%s %s\n' "$1" "$2" > ".pkm/state.tmp.$$" && mv ".pkm/state.tmp.$$" .pkm/state
}
