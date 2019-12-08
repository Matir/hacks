#!/usr/bin/env python3

# Find config options set in A that is not in B.

import sys


def main(argv):
    try:
        parent = open(argv[1])
        child = open(argv[2])
    except IndexError:
        sys.stderr.write(
                'Usage: {} <parentfile> <childfile>\n'.format(argv[0]))
        sys.exit(1)
    except IOError as ex:
        sys.stderr.write('Error: {}\n'.format(ex))
        sys.exit(1)
    parent_config = load_config(parent)
    child_config = load_config(child)
    child_missing = parent_config - child_config
    if not child_missing:
        print('Child contains all elements in parent.')
        return
    print('Child is missing:')
    print('\n'.join(sorted(child_missing)))


def load_config(fp):
    config_yes = set()
    for line in fp:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        try:
            key, val = line.split('=', 1)
        except ValueError:
            sys.stderr.write('Unexpected line: {}\n'.format(line))
            sys.exit(1)
        if val != 'y':
            continue
        config_yes.add(key)
    return config_yes


if __name__ == '__main__':
    main(sys.argv)
