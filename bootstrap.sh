#!/bin/bash

cd "$(dirname "$0")" || exit 1

all_clear() {
    echo ".pytest_cache"
    find . -type d -name ".pytest_cache" -exec rm -rf {} \; 2>/dev/null
    echo "__pycache__"
    find . -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null
    echo ".cache"
    rm -rf alist_sync/.alist-sync-cache alist_sync.egg-info
    echo "alist-test-dir"
    rm -rf alist/test_* alist/data alist/daemon
}

case $1 in
install)
    pip install -U pip
    pip install -e .
    pip install git+https://github.com/lee-cq/alist-sdk --no-cache-dir --force-reinstall
    ;;

alist)
    cd alist || {
        echo "Error: tests/alist not find "
        exit 1
    }
    shift
    ./alist "$@"
    ;;

alist-init)
    pkill alist
    rm -rf alist/*
    sh tools/init_alist.sh alist/
    ;;

clear)
    all_clear
    ;;

test)
    whereis pytest || pip install pytest
    clear
    ./alist/alist stop || pkill alist
    all_clear
    shift 1
    pytest -v "$@"
    ;;

debugger)
    all_clear
    clear
    python3 tests/debugger.py
    ;;

*)
    echo "Usage: $0 {install|alist-init|clear|debugger|test}"
    exit 1
    ;;
esac
