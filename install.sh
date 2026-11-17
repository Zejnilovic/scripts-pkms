#!/bin/sh
# install.sh [--prefix DIR]: installs pkm from the folder this script is in: an unpacked release tarball or a clone. It
# downloads nothing. The files go to DIR/lib/pkm-<version>/ (DIR defaults to $HOME/.local), and DIR/bin/pkm links to them.
# It says whether DIR/bin is on PATH, runs pkm doctor, and exits with doctor's exit status.
set -eu

prefix=$HOME/.local
while [ $# -gt 0 ]; do
  case $1 in
    --prefix)
      [ $# -ge 2 ] || { echo "--prefix needs a folder" >&2; exit 2; }
      prefix=$2; shift 2 ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "Usage: sh install.sh [--prefix DIR]" >&2; exit 2 ;;
  esac
done
case $prefix in
  /*) ;;
  *) prefix=$(pwd)/$prefix ;;
esac

here=$(cd "$(dirname "$0")" && pwd)
if [ ! -f "$here/bin/pkm" ] || [ ! -d "$here/lib" ] || [ ! -d "$here/share" ] || [ ! -f "$here/VERSION" ]; then
  echo "install.sh must sit next to bin/, lib/, share/ and VERSION: an unpacked tarball or a clone of pkm." >&2
  exit 2
fi
version=$(cat "$here/VERSION")
target=$prefix/lib/pkm-$version

rm -rf "$target"
mkdir -p "$target" "$prefix/bin"
cp -R "$here/bin" "$here/lib" "$here/share" "$here/VERSION" "$target/"
ln -sf "$target/bin/pkm" "$prefix/bin/pkm"

echo "pkm $version is installed in $target"
echo "The command is $prefix/bin/pkm"
case ":$PATH:" in
  *":$prefix/bin:"*) echo "$prefix/bin is on your PATH." ;;
  *) echo "$prefix/bin is not on your PATH: add it, for example with: export PATH=\"$prefix/bin:\$PATH\"" ;;
esac
"$prefix/bin/pkm" doctor
