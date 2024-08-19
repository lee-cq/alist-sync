#!/usr/bin/env bash

cd "${1:-$(dirname "$0")}" || exit

echo "INSTALL ALIST. PWD: $(pwd)"

__AIST_ADMIN_PASSWORD="${_ALIST_ADMIN_PASSWORD:-123456}"

mkdir -p alist
cd alist || exit

VERSION=${ALIST_VERSION:-"3.31.0"}

platform=$(uname -s | tr '[:upper:]' '[:lower:]')
case $platform in
linux | darwin) fix=".tar.gz" ;;
win* | mingw64*)
    fix=".zip"
    platform="windows"
    ;;
esac

case $(uname -m) in
x86_64) cpu="amd64" ;;
i386 | i686) cpu="386" ;;
aarch64 | arm64) cpu="arm64" ;;
esac
filename="alist-${platform}-${cpu}${fix}"
# download_url="https://github.com/alist-org/alist/releases/download/v3.36.0/alist-windows-amd64.zip"
export download_url="https://github.com/alist-org/alist/releases/download/v${VERSION}/${filename}"

if [[ ! -f "alist" && ! -f "alist.exe" ]]; then
    set -e
    echo "Will Install ${download_url}"
    curl -SLkO "$download_url"
    if [ "${fix}" == ".zip" ]; then
        unzip "$filename"
    else
        tar xzvf "$filename"
    fi
    set +e
fi

rm -rf data/ test_dir/
./alist admin set "${__AIST_ADMIN_PASSWORD}"
./alist restart
