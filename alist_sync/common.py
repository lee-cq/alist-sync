import hashlib

import logging

logger = logging.getLogger("alist-sync.common")


def sha1(s):
    return hashlib.sha1(str(s).encode()).hexdigest()


def sha1_6(s):
    hs = sha1(s)[:6]
    logger.debug("sha1[:6]: %s -> %s", s, hs)
    return hs


if __name__ == '__main__':
    sha1("123456")
