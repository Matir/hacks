#!/usr/bin/env python
import math
import sys


class Permutations():

    def perms(self, total, choice):
        try:
            return math.perm(total, choice)
        except AttributeError:
            # Fallback for Python < 3.8
            if choice < 0 or choice > total:
                return 0
            result = 1
            for x in range(0, choice):
                result *= total-x
            return result
       

if __name__ == '__main__':
    try:
        total = sys.argv[1]
        choice = sys.argv[2]
        total = int(total, 0)
        choice = int(choice, 0)
        ops = Permutations()
        result = ops.perms(total, choice)
        print(result)
    except IndexError:
        print('Usage: permutations.py <int of total> <int to choice>')
