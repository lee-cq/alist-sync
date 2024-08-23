#!/bin/bash

cd "$(dirname "$0")" || exit 1

set -a
. .env
set +a

# which python3 >/dev/null || alias python3=python

if uname | grep -iq "NT"; then
  PYTHONPATH="$(pwd);${PYTHONPATH}"
else
  PYTHONPATH="$(pwd):${PYTHONPATH}"
fi

export PYTHONPATH

all_clear() {
  echo ".pytest_cache"
  find . -type d -name ".pytest_cache" -exec rm -rf {} \; 2>/dev/null
  echo "__pycache__"
  find . -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null
  echo ".cache"
  rm -rf alist_sync/.alist-sync-cache alist_sync.egg-info
  echo "alist-test-dir"
  rm -rf alist/test_* alist/data alist/daemon
  echo "logs"
  rm -rf logs/*
}

case $1 in
install)
  pip install -U pip
  pip install -U git+https://github.com/lee-cq/alist-sdk --no-cache-dir --force-reinstall
  pip install -U git+https://github.com/lee-cq/logging-loki
  pip install -e .
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
  bash tools/init_alist.sh .
  ;;

clear)
  all_clear
  ;;

clear-log)
  rm -rf logs/*
  rm -rf alist/data/log/*
  ./bootstrap.sh alist restart
  ;;

test)
  whereis pytest || pip install pytest
  clear
  ./alist/alist stop || pkill alist
  all_clear
  shift 1
  pytest -v "$@"
  ;;

main)
  shift
  python -m alist_sync "$@"
  ;;

debugger)
  all_clear
  clear
  _type=$2
  shift 2
  python tests/debuger_${_type}.py "$@"
  ;;

*)
  echo "Usage: $0 {install|alist-init|clear|debugger|test}"
  exit 1
  ;;
esac
