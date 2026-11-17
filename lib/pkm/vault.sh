# shellcheck shell=bash
# lib/pkm/vault.sh: finds the vault a command works in, the folder that holds .pkm/.
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# use_vault <folder> <where the folder came from>: sets vault when the folder holds .pkm/, else exits 2.
# shellcheck disable=SC2034 # vault is read by bin/pkm and cmd/vault.sh
use_vault() {
  [ -d "$1/.pkm" ] || die 2 "No vault in $1: it has no .pkm folder (from $2)."
  vault=$(cd "$1" && pwd) || die 2 "Can't open $1 (from $2)."
}

# find_vault: sets vault. The first hit wins: -V <name> (a vault_<name>= line in the user config), --vault <folder>,
# PKM_VAULT, the nearest folder above the current one that holds .pkm/, then vault= in the user config.
# -V and --vault together are refused, and so is an explicit choice that isn't a vault.
find_vault() {
  local candidate dir
  if [ -n "$vault_name" ] && [ -n "$vault_option" ]; then die 2 "Use one of -V and --vault, not both."; fi
  if [ -n "$vault_name" ]; then
    case $vault_name in
      ''|*[!A-Za-z0-9_-]*) die 2 "A vault name has letters, digits, '-' and '_' only, got: $vault_name" ;;
    esac
    candidate=$(user_config_value "vault_$vault_name")
    [ -n "$candidate" ] || die 2 "No vault named $vault_name: add vault_$vault_name=<folder> to $(user_config_file)."
    use_vault "$candidate" "vault_$vault_name in $(user_config_file)"
    return 0
  fi
  if [ -n "$vault_option" ]; then use_vault "$vault_option" "--vault"; return 0; fi
  if [ -n "${PKM_VAULT:-}" ]; then use_vault "$PKM_VAULT" "PKM_VAULT"; return 0; fi
  dir=$PWD
  while :; do
    if [ -d "$dir/.pkm" ]; then vault=$dir; return 0; fi
    [ "$dir" != / ] || break
    dir=$(dirname "$dir")
  done
  candidate=$(user_config_value vault)
  if [ -n "$candidate" ]; then use_vault "$candidate" "vault= in $(user_config_file)"; return 0; fi
  die 2 "No vault found from $PWD: run pkm inside one, or pass --vault <folder>, set PKM_VAULT, or add vault=<folder> to $(user_config_file)."
}
