# shellcheck shell=bash
# lib/pkm/config.sh: the settings of pkm. settings_list is the one list of every setting: its key, its scope, its
# default and what it means. docs/settings.md repeats it, and a test keeps the two equal. Sourced by bin/pkm.
# Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# settings_list: one line per setting: key|scope|default|meaning. The scope is vault (.pkm/config), user (the user's
# pkm config) or both (the vault's value wins over the user's). A key with <type> or <name> stands for each key of
# that shape. A default of - means none.
settings_list() {
  cat <<'EOF'
format|vault|1|The layout version of the vault. pkm reads format=1 only.
shared|vault|no|yes when several people write into the vault, so each writer gets their own day pages.
close|vault|week|The cycle the close runs on: week, or the name of a cycle_<name> setting.
cycle_<name>|vault|-|A cycle of your own: <N>w from a weekday (1w only) or a date, or <N>m from a day of the month (1-28) or a date.
cross_vault|vault|no|yes lets an agent working in another of your vaults read this one, for a brief across vaults.
templates|vault|templates|The folder of this vault's own templates, relative to the vault.
folder_<type>|vault|notes|The folder that new notes of this type go in.
due_soon_days|both|7|The tasks due within this many days, after the overdue ones, come first in pkm tasks.
waiting_days|both|7|A task waiting for longer than this many days comes after the due soon ones in pkm tasks.
limit|both|30|The most listed lines a command prints before the footer; --limit sets it for one run.
writer|user|-|The name of the person who writes on this machine, for a shared vault.
vault|user|-|The vault to use when none is given and none is above the current folder.
vault_<name>|user|-|A named vault, chosen with -V <name>.
EOF
}

# setting_known <key>: prints scope|default of the setting the key belongs to. Prints nothing and fails for a key
# pkm doesn't know.
setting_known() {
  local settings k s d base
  settings=$(settings_list)
  while IFS='|' read -r k s d _; do
    case $k in
      *"<"*)
        base=${k%%<*}
        case $1 in
          "$base"?*) printf '%s|%s\n' "$s" "$d"; return 0 ;;
        esac ;;
      *)
        if [ "$1" = "$k" ]; then printf '%s|%s\n' "$s" "$d"; return 0; fi ;;
    esac
  done <<EOF
$settings
EOF
  return 1
}

# setting_scope <key>: vault, user or both. An unknown key counts as a vault setting.
setting_scope() {
  local info
  info=$(setting_known "$1") || { printf '%s\n' vault; return 0; }
  printf '%s\n' "${info%%|*}"
}

# file_value <file> <key>: the last value of key in a settings file, without spaces at the ends. Empty when the file
# or the key is missing.
file_value() {
  [ -f "$1" ] || return 0
  sed -n "s/^[[:space:]]*$2[[:space:]]*=[[:space:]]*//p" "$1" | tail -n 1 | sed 's/[[:space:]]*$//'
}

# file_keys <file>: the keys set in a settings file, one per line.
file_keys() {
  [ -f "$1" ] || return 0
  sed -n 's/^[[:space:]]*\([A-Za-z0-9_-][A-Za-z0-9_-]*\)[[:space:]]*=.*/\1/p' "$1"
}

# user_config_file: the user's pkm config, in ${XDG_CONFIG_HOME:-$HOME/.config}/pkm/config.
user_config_file() {
  if [ -n "${XDG_CONFIG_HOME:-}" ]; then printf '%s\n' "$XDG_CONFIG_HOME/pkm/config"
  else printf '%s\n' "$HOME/.config/pkm/config"; fi
}

# user_templates_dir: the user's own templates, next to the user's config.
user_templates_dir() {
  printf '%s/templates\n' "$(dirname "$(user_config_file)")"
}

# user_config_value <key>: the last value of key in the user config, with a leading ~/ taken to be $HOME. Empty when
# the key or the file is missing.
user_config_value() {
  local value
  value=$(file_value "$(user_config_file)" "$1")
  if [ "${value%%/*}" = "~" ]; then value=$HOME/${value#*/}; fi
  printf '%s\n' "$value"
}

# config_with_source <key> <default>: "value<TAB>source" for a setting, from the file its scope allows: the vault's
# .pkm/config for a vault setting, the user's config for a user setting, and for both the vault's value first. Else
# the default. The source is vault, user or default.
config_with_source() {
  local scope value source=default
  scope=$(setting_scope "$1")
  value=""
  if [ "$scope" = vault ] || [ "$scope" = both ]; then
    value=$(file_value .pkm/config "$1")
    [ -z "$value" ] || source=vault
  fi
  if [ -z "$value" ] && { [ "$scope" = user ] || [ "$scope" = both ]; }; then
    value=$(file_value "$(user_config_file)" "$1")
    [ -z "$value" ] || source=user
  fi
  printf '%s\t%s\n' "${value:-$2}" "$source"
}

# config <key> <default>: the value of a setting (see config_with_source).
config() {
  config_with_source "$1" "$2" | cut -f1
}

# config_problems <file> <vault|user>: one line per problem in a settings file, as path:line: text. Checks each line
# is key=value, the key is a setting of this file's kind, and the value is one that setting accepts.
config_problems() {
  local file=$1 owner=$2 n=0 raw line key value info scope cycles reason
  [ -f "$file" ] || return 0
  cycles=$(file_keys "$file")
  while IFS= read -r raw || [ -n "$raw" ]; do
    n=$((n + 1))
    line=$(printf '%s' "$raw" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    case $line in
      ''|'#'*) continue ;;
      *=*) ;;
      *) echo "$file:$n: not a key=value line: $line"; continue ;;
    esac
    key=$(printf '%s' "${line%%=*}" | sed 's/[[:space:]]*$//')
    value=$(printf '%s' "${line#*=}" | sed 's/^[[:space:]]*//')
    info=$(setting_known "$key") || { echo "$file:$n: unknown setting: $key (pkm config lists them)"; continue; }
    scope=${info%%|*}
    if [ "$owner" = vault ] && [ "$scope" = user ]; then echo "$file:$n: $key belongs in the user config, not in the vault"; continue; fi
    if [ "$owner" = user ] && [ "$scope" = vault ]; then echo "$file:$n: $key belongs in the vault's .pkm/config"; continue; fi
    case $key in
      shared|cross_vault)
        case $value in yes|no) ;; *) echo "$file:$n: $key is yes or no, got: $value" ;; esac ;;
      format)
        [ "$value" = 1 ] || echo "$file:$n: format is 1, got: $value" ;;
      cycle_*)
        reason=$(cycle_name_problem "${key#cycle_}")
        [ -z "$reason" ] || echo "$file:$n: $key: $reason"
        cycle_value_parse "$value" > /dev/null || echo "$file:$n: $key is <N>w from a weekday (1w only) or a date, or <N>m from a day 1-28 or a date, got: $value" ;;
      limit|due_soon_days|waiting_days)
        case $value in
          ''|*[!0-9]*) echo "$file:$n: $key is a whole number of 1 or more, got: $value" ;;
          *) [ "$value" -ge 1 ] || echo "$file:$n: $key is a whole number of 1 or more, got: $value" ;;
        esac ;;
      close)
        if [ "$value" != week ] && ! printf '%s\n' "$cycles" | grep -qx "cycle_${value}"; then
          echo "$file:$n: close must be week or a cycle_$value set in this file, got: $value"
        fi ;;
    esac
  done < "$file"
}
