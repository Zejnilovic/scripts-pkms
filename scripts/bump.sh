#!/usr/bin/env bash
# Starts a new version: updates VERSION, pkm_version in lib/pkm/core.sh,
# and adds an "(unreleased)" CHANGELOG.md heading with a TODO to replace.
# Works with bash 3.2 (macOS) and Git Bash (Windows).
#
# Usage: bash scripts/bump.sh <major.minor.patch>
#   patch  fixes
#   minor  new commands, options or templates
#   major  renamed or removed commands, options or output formats, or changes that need manual steps in vaults

set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
new="${1:-}"

case "$new" in
  -h|--help|"") sed -n '2,10p' "$0"; [ -n "$new" ]; exit $? ;;
esac
if ! printf '%s\n' "$new" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Version must look like 1.2.3, got: $new" >&2; exit 2
fi

current=$(tr -d '[:space:]' < "$root/VERSION")
# Compare numerically, part by part.
greater=$(awk -v a="$new" -v b="$current" 'BEGIN {
  split(a, x, "."); split(b, y, ".")
  for (i = 1; i <= 3; i++) { if (x[i] + 0 > y[i] + 0) { print 1; exit } if (x[i] + 0 < y[i] + 0) { print 0; exit } }
  print 0 }')
if [ "$greater" != 1 ]; then
  echo "New version $new must be greater than the current $current." >&2; exit 2
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

printf '%s\n' "$new" > "$root/VERSION"

sed "s/^pkm_version=.*/pkm_version=$new/" "$root/lib/pkm/core.sh" > "$tmp" \
  && cat "$tmp" > "$root/lib/pkm/core.sh"

# Insert the new heading before the first section ("## Released" once a version is released).
awk -v v="$new" '
  function entry() { print "## " v " (unreleased)"; print ""; print "- TODO: describe the change" }
  !done && /^## / { entry(); print ""; done = 1 }
  { print }
  END { if (!done) { print ""; entry() } }
' "$root/CHANGELOG.md" > "$tmp" && cat "$tmp" > "$root/CHANGELOG.md"

echo "Bumped $current -> $new: VERSION, lib/pkm/core.sh and CHANGELOG.md."
echo "Next: replace the TODO in CHANGELOG.md with what changed."
