# Take a wordlist and exec gpg

import hashlib
import sys
import os
import subprocess

from typing import Iterator


def get_hashes(cand: str) -> Iterator[str]:
    yield cand
    for h in (hashlib.sha1, hashlib.md5, hashlib.sha256, hashlib.sha512):
        yield h(cand.encode()).hexdigest()


def is_valid_utf8(var: bytes) -> bool:
    try:
        var.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def close_no_fail(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass


def try_decrypt_file(fname: str, passphrase: str) -> bool:
    passphrase_rd, passphrase_wr = os.pipe()
    status_rd, status_wr = os.pipe()
    # gpg --pinentry-mode=loopback --no-symkey-cache --ignore-mdc-error --batch -d accounts.gpg
    cmd = [
        "gpg",
        "--pinentry-mode", "loopback",
        "--no-symkey-cache",
        "--ignore-mdc-error",
        "--batch",
        "--passphrase-fd", "{:d}".format(passphrase_rd),
        "--status-fd", "{:d}".format(status_wr),
        "-d",
        fname
    ]
    try:
        proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(passphrase_rd, status_wr),
                )
        os.write(passphrase_wr, passphrase.encode())
        os.close(passphrase_wr)
        os.close(status_wr)
        os.close(passphrase_rd)
        decok = False
        typeok = False
        with os.fdopen(status_rd, "rb") as status:
            for line in status:
                #print(line)
                decok = decok or b"DECRYPTION_OKAY" in line
                if b"PLAINTEXT " in line:
                    pieces = line.split(b" ")
                    if (pieces[2] in (b"62", b"74", b"75") and
                        is_valid_utf8(pieces[4])):
                        typeok = True
                proc.poll()
        if proc.wait():
            return False
        return decok and typeok
    finally:
        close_no_fail(passphrase_rd)
        close_no_fail(passphrase_wr)
        close_no_fail(status_rd)
        close_no_fail(status_wr)


def main():
    if len(sys.argv) != 3:
        print("Usage: %s <wordlist> <gpgfile>" % sys.argv[0])
        sys.exit(1)
    i = 0
    with open(sys.argv[1], "r") as fp:
        for line in fp:
            line = line.strip()
            for h in get_hashes(line):
                i += 1
                if try_decrypt_file(sys.argv[2], h):
                    print(h)
                    break
    print('Tried {} values.'.format(i))


if __name__ == "__main__":
    main()
