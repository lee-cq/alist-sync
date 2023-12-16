#!/usr/bin/env bash

cd "$(dirname "$0")" || exit

mkdir -p alist
cd alist || exit

VERSION=${ALIST_VERSION:-"v3.29.1"}


platform=$(uname -s | tr '[:upper:]' '[:lower:]')
case $platform in
  linux | darwin)    fix=".tar.gz"    ;;
  windows*)          fix=".zip"       ;;
esac

case $(uname -m) in
  x86_64)                 cpu="amd64"        ;;
  i386 | i686)            cpu="386"          ;;
  aarch64 | arm64)        cpu="arm64"        ;;
esac
filename="alist-${platform}-${cpu}${fix}"
export download_url="https://github.com/alist-org/alist/releases/download/${VERSION}/${filename}"

if [ ! -f alist ]; then
  set -e
  echo "Will Install ${download_url}"
  wget -q "$download_url"
  tar xzvf "$filename"
  set +e
fi

rm -rf data/ test_dir/
./alist admin set 123456
./alist restart
