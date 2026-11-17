# shellcheck shell=bash
# lib/pkm/cmd/init.sh: pkm init: sets up a vault in this folder, or in the one --vault names. It creates only
# .pkm/config, .pkm/.gitignore and .pkmignore, and refuses to overwrite any of them. Sourced by bin/pkm.
# Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

cmd_init() {
  local target existing="" f
  target=${vault_option:-$PWD}
  [ -d "$target" ] || die 2 "No folder $target to set up a vault in."
  target=$(cd "$target" && pwd)
  for f in .pkm/config .pkm/.gitignore .pkmignore; do
    [ ! -e "$target/$f" ] || existing="$existing $f"
  done
  [ -z "$existing" ] || die 1 "This folder is set up already ($existing): init never overwrites them. Edit them, or remove them to start again."
  mkdir -p "$target/.pkm" || die 2 "Can't create $target/.pkm"
  printf '%s\n' 'format=1' > "$target/.pkm/config"
  printf '%s\n' 'cache/' 'state' > "$target/.pkm/.gitignore"
  cat > "$target/.pkmignore" <<'EOF'
# Files and folders pkm leaves out of the vault, in gitignore syntax: one pattern per line.
# exports/      a folder, with everything in it
# *.pdf         files by their name, in any folder
# scans/*       everything in a folder, while still letting a ! line bring one file back
# !scans/a.md   brings back a file that a pattern above left out (not inside a folder left out with folder/)
# pkm reads only this file. .gitignore is not followed, so a folder kept out of git is still part of the vault.
EOF
  echo "The vault is set up in $target: .pkm/config, .pkm/.gitignore and .pkmignore."
}
