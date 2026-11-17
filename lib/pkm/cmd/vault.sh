# shellcheck shell=bash
# lib/pkm/cmd/vault.sh: pkm vault (the vault's folder) and pkm vaults (the named vaults of the user config).
# Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_vault() {
  printf '%s\n' "$vault"
}

cmd_vaults() {
  local file name path state
  file=$(user_config_file)
  [ -f "$file" ] || return 0
  awk -F= '/^[[:space:]]*vault_[A-Za-z0-9_-]+[[:space:]]*=/ {
    name = $1; sub(/^[[:space:]]*vault_/, "", name); sub(/[[:space:]]+$/, "", name)
    path = substr($0, index($0, "=") + 1); sub(/^[[:space:]]+/, "", path); sub(/[[:space:]]+$/, "", path)
    print name "\t" path }' "$file" > "$tmp/named-vaults"
  while IFS=$'\t' read -r name path; do
    if [ "${path%%/*}" = "~" ]; then path=$HOME/${path#*/}; fi
    if [ -d "$path/.pkm" ]; then state=ok; else state=missing; fi
    printf '%s\t%s\t%s\n' "$name" "$path" "$state"
  done < "$tmp/named-vaults"
}
