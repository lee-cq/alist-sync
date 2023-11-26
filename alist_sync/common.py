import hashlib


def sha1(s):
    return hashlib.sha1(str(s).encode()).hexdigest()


def sha1_6(s):
    return sha1(s)[:6]


if __name__ == '__main__':
    sha1("123456")
