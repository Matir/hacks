#!/usr/bin/env python

import string
import sys


class ROTAlpha():

    def rot_alpha(self, data, rot):
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        upper = ''.join([uppercase[(i + rot) % 26] for i in range(26)])
        lower = ''.join([lowercase[(i + rot) % 26] for i in range(26)])
        table = str.maketrans(uppercase + lowercase, upper + lower)
        print(data.translate(table))


if __name__ == '__main__':
    try:
        data = sys.argv[1]
        rot = sys.argv[2]
        rot = int(rot, 0)
        table = ROTAlpha()
        table.rot_alpha(data, rot)
    except IndexError:
        print('Usage: rot_alpha.py <alpha data> <int to rotate>')
        sys.exit(1)
