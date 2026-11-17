#!/bin/sh
# scripts/formula.sh <tarball> [output]: writes the Homebrew formula (packaging/pkm.rb, or output) with the release URL and
# the sha256 of the tarball that make dist built. The tarball's name, pkm-<version>.tar.gz, gives the version.
set -eu

tarball=${1:?usage: sh scripts/formula.sh <tarball> [output]}
out=${2:-}
here=$(cd "$(dirname "$0")/.." && pwd)
[ -n "$out" ] || out=$here/packaging/pkm.rb

base=$(basename "$tarball")
case $base in
  pkm-*.tar.gz) ;;
  *) echo "The tarball is named pkm-<version>.tar.gz, got: $base" >&2; exit 2 ;;
esac
version=${base#pkm-}
version=${version%.tar.gz}
if command -v sha256sum >/dev/null 2>&1; then
  sum=$(sha256sum "$tarball" | cut -d ' ' -f 1)
else
  sum=$(shasum -a 256 "$tarball" | cut -d ' ' -f 1)
fi
url="https://github.com/Zejnilovic/scripts-pkms/releases/download/v$version/pkm-$version.tar.gz"

sed -e "s|^  url \".*\"|  url \"$url\"|" -e "s|^  sha256 \".*\"|  sha256 \"$sum\"|" "$here/packaging/pkm.rb" > "$out.tmp"
mv "$out.tmp" "$out"
echo "wrote $out for pkm $version"
