#!/usr/bin/env python
import math
import sys


class Combinations():

    def combs(self, total, choice):
        try:
            return math.comb(total, choice)
        except AttributeError:
            # Fallback for Python < 3.8
            if choice < 0 or choice > total:
                return 0
            if choice == 0 or choice == total:
                return 1
            if choice > total // 2:
                choice = total - choice
            
            numerator = 1
            for i in range(total, total - choice, -1):
                numerator *= i
            denominator = math.factorial(choice)
            return numerator // denominator
       

if __name__ == '__main__':
    try:
        total = sys.argv[1]
        choice = sys.argv[2]
        total = int(total, 0)
        choice = int(choice, 0)
        ops = Combinations()
        result = ops.combs(total, choice)
        print(result)
    except IndexError:
        print('Usage: combinations.py <int of total> <int to choice>')
