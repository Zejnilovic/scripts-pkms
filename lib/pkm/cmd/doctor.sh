# shellcheck shell=bash
# lib/pkm/cmd/doctor.sh: pkm doctor: the tools pkm uses, with their versions, and the settings in both config files.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# doctor_tool <command> <package> <required|optional> <what for>: one line for the tool; a missing required tool
# sets doctor_failed and adds its package to doctor_missing.
doctor_tool() {
  local version
  if command -v "$1" >/dev/null 2>&1; then
    version=$("$1" --version 2>/dev/null | head -n 1)
    printf 'found    %-5s %-26s %s\n' "$1" "$version" "$4"
  else
    printf 'missing  %-5s %-26s %s\n' "$1" "-" "$4"
    if [ "$3" = required ]; then doctor_failed=1; doctor_missing="$doctor_missing $2"; fi
  fi
}

cmd_doctor() {
  doctor_failed=0 doctor_missing=""
  doctor_tool bash bash optional "the shell pkm runs in"
  doctor_tool rg ripgrep required "searching notes, and the list of files in the vault"
  doctor_tool jq jq required "reading JSON from boards and other tools"
  doctor_tool git git optional "a history of every change, to review and undo"
  doctor_tool curl curl optional "check --urls: whether the web addresses in the notes answer"
  # The vault's config is read from the vault, which may be above the current folder; outside a vault there is none.
  local found
  found=$( (find_vault && printf '%s' "$vault") 2>/dev/null) || found=""
  if [ -n "$found" ]; then config_problems "$found/.pkm/config" vault > "$tmp/settings-problems"; else : > "$tmp/settings-problems"; fi
  config_problems "$(user_config_file)" user >> "$tmp/settings-problems"
  if [ -s "$tmp/settings-problems" ]; then
    sed 's/^/problem  /' "$tmp/settings-problems"
    doctor_failed=1
  else
    echo "settings  .pkm/config and the user config are fine (pkm config shows them)"
  fi
  if [ -n "$found" ] && [ -n "$(file_value "$found/.pkm/config" now)" ]; then
    echo "clock     now=$(file_value "$found/.pkm/config" now) in .pkm/config fixes the clock: pkm works as if it were then"
  fi
  if [ -n "$doctor_missing" ]; then echo "Install what's missing, for example: brew install$doctor_missing"; fi
  [ "$doctor_failed" = 0 ] || return 1
}
