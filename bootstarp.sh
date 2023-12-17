#!/bin/bash

cd "$(dirname "$0")" || exit 1

all_clear() {
    echo ".pytest_cache"
    find . -type d -name ".pytest_cache" -exec rm -rf {} \; 2>/dev/null
    echo  "__pycache__"
    find . -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null
    echo ".cache"
    rm -rf alist_sync/.cache alist_sync.egg-info
}

case $1 in
install ) 
    pip install -U pip
    pip install -e .
    pip install  git+https://github.com/lee-cq/alist-sdk --no-cache-dir --force-reinstall
    ;;

alist-init ) 
    pkill alist
    rm -rf tests/alist
    tests/init_alist.sh
    ;;

alist-version )
    cd tests/alist  || {
        echo "未初始化 -  执行 alist-init"
        exit 2
    }
    ./alist version
    ;;

alist-run )
    cd tests/alist  || {
        echo "未初始化 -  执行 alist-init"
        exit 2
    }
    ./alist restart
    ;;

alist-stop ) 
    ./tests/alist/alist stop || pkill alist
    ;;

clear )  
    all_clear 
    ;;

test ) 
    whereis pytest || pip install pytest
    clear
    pkill alist
    all_clear
    shift 1
    pytest -v "$@"
    ;;
* )
    echo "Usage: $0 {install|alist-init|alist-version|alist-run|alist-stop|clear|test}"
    exit 1
    ;;
esac