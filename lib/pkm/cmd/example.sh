# shellcheck shell=bash
# lib/pkm/cmd/example.sh: pkm example [<name>] [<folder>]: copies an example vault into a new folder, to try pkm on a
# vault that has a few weeks in it. The examples ship with pkm: share/pkm/examples in an installed pkm (make install
# and make dist copy them there from docs/examples), docs/examples in a clone. Nothing is downloaded, and nothing that
# exists is written into. Sourced by bin/pkm. Defines functions only.
# shellcheck source=../globals.sh
. "$pkm_home/lib/pkm/globals.sh"

# example_root: the folder that holds the example vaults.
example_root() {
  if [ -d "$pkm_home/share/pkm/examples" ]; then printf '%s\n' "$pkm_home/share/pkm/examples"
  elif [ -d "$pkm_home/docs/examples" ]; then printf '%s\n' "$pkm_home/docs/examples"
  else die 2 "This pkm has no example vaults: install it from a release or a clone."; fi
}

# example_names: the example vaults, one name per line: the folders with a .pkm/config.
example_names() {
  local root dir
  root=$(example_root)
  for dir in "$root"/*; do
    [ -f "$dir/.pkm/config" ] && printf '%s\n' "${dir##*/}"
  done
}

cmd_example() {
  local name=${1:-work} root target names others when
  [ $# -le 2 ] || die 2 "Usage: pkm example [<name>] [<folder>]"
  root=$(example_root)
  names=$(example_names)
  printf '%s\n' "$names" | grep -qxF -- "$name" \
    || die 2 "pkm example: there is no example $name; the examples are $(printf '%s\n' "$names" | paste -sd ' ' - | sed 's/ /, /g')."
  target=${2:-pkm-example-$name}
  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "$target"
    die 1 "$target already exists, and pkm won't write into it: name a new folder, as in pkm example $name <folder>."
  fi
  # tar copies the vault without the cache and state pkm keeps in .pkm, which a clone's docs/examples may have.
  mkdir -p "$target" || die 2 "pkm example: could not make $target."
  if ! (cd "$root/$name" && tar -cf - --exclude ./.pkm/cache --exclude ./.pkm/state .) | (cd "$target" && tar -xf -); then
    die 2 "pkm example: could not copy to $target."
  fi
  when=$(file_value "$target/.pkm/config" now)
  others=$(printf '%s\n' "$names" | grep -vxF -- "$name" | sed 's/^/pkm example /' | paste -sd ',' - | sed 's/,/, /g')
  echo "$target"
  echo "The $name example vault${when:+, as on $when (its .pkm/config sets now)}. Try, in that folder:"
  echo "  cd $target"
  if [ "$(file_value "$target/.pkm/config" shared)" = yes ]; then
    echo "  # It is shared: pkm day and pkm add need writer=<name> in your user config, $(user_config_file)"
  else
    echo "  pkm day          # the day's page"
  fi
  echo "  pkm tasks        # the open tasks: overdue, due soon, waiting, the rest"
  echo "  pkm overview     # the areas, projects and notes"
  echo "  pkm close        # what the week leaves open"
  [ -z "$others" ] || echo "Other examples: $others."
  echo "It is a copy: change it, or delete the folder when you're done."
}
