#!/usr/bin/env bash

cd "$(dirname "$0")" || exit

mkdir -p alist
cd alist || exit

VERSION=${ALIST_VERSION:-"v3.29.1"}

if [ ! -f alist ]; then
    echo Will Install ${VERSION}
    wget -q https://github.com/alist-org/alist/releases/download/${VERSION}/alist-linux-amd64.tar.gz
    tar xzvf alist-linux-amd64.tar.gz
fi

rm -rf data/ test_dir/
./alist admin set 123456
./alist restart
