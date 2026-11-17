# shellcheck shell=bash
# lib/pkm/globals.sh: every global the modules share. bin/pkm sets them before a command runs; this file declares them
# so shellcheck can see where each one is set, and a misspelled name is caught. The := form keeps a value already set.
# Sourced by each module of lib/pkm/. Defines no functions.
: "${pkm_home:=}" "${now:=}" "${today:=}" "${clock:=}" "${tmp:=}" "${vault:=}" "${vault_option:=}" "${vault_name:=}"
: "${conflict_markers:=}" "${pkm_version:=}" "${translit:=}"
