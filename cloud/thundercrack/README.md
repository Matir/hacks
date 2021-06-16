# Thundercrack

## Overview

This is a tool for spinning up hashcat on Google Cloud Compute Instances.  It
supports launching with GPU accelerators attached (fast cracking).

It performs the following steps:

1. Create instance.
2. Download and install latest hashcat and dependencies.
3. Upload hash list/wordlist to system.
4. Start cracking in tmux session.

It *currently* does not support downloading/waiting for results.  The instance
does *not* stop when cracking is complete.  You must stop it.

### Requirements

You must have a paid GCP account to get GPU accelerated instances.  See
[GCP Documentation](https://cloud.google.com/compute/docs/gpus) for available
types.  Because of the cost of the GPUs, this script runs on *CPU* by default,
so you *must* specify a GPU type if you want CUDA cracking.

You will need service account credentials in JSON format for the account to
launch the GCP instance.

Thanks to [Type Hints](https://www.python.org/dev/peps/pep-0484/), Python >= 3.5
are supported. `mypy` is used for type checking.

## Common Flags

* `--credentials`: Path to the JSON credentials for a service account to use to
  start the instance.
* `hashcat_arguments`: Arguments passed to hashcat.  At a minimum, you should
  pass `-m <N>` where N is the hash type you're trying to crack (see
  [Hashcat Documentation](https://hashcat.net/wiki/doku.php?id=hashcat)).

## Examples

Crack the md5crypt hashes in the testdata directory using a single NVIDIA Tesla
T4:

```
python3 ./thundercrack.py --credentials ./thundercrack.json \
  --gpu nvidia-tesla-p4 --wordlist ./testdata/rockyou_short \
  --hashfile ./testdata/passwd.md5crypt -m 500
```

Hashcat is in `/root/hashcat`, and the working directory is `/root/`, so you can
use relative paths for files already on the server.

```
python3 ./thundercrack.py --credentials ./thundercrack.json \
  --gpu nvidia-tesla-p4 --wordlist ./testdata/rockyou_short \
  --hashfile ./testdata/passwd.md5crypt \
  -m 500 -r hashcat/rules/best64.rule
```

## TODO

- [ ] Support downloading results and stopping instance on completion.
- [ ] Support automatically connecting to remote tmux session.
- [ ] Support starting another job on an existing instance.
- [ ] Support uploading rules files.
- [ ] Switch to [TAP](https://github.com/swansonk14/typed-argument-parser) for
  arg parsing.
