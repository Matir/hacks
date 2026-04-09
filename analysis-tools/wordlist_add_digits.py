#!/usr/bin/env python
#Adds 4digits to the end of the common word lists
import sys
import itertools


class WordlistAddDigits():

    def add_digits(self, wordlist_path, outfile_path):
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f, \
                 open(outfile_path, 'w', encoding='utf-8') as out:
                
                # Iterating line by line instead of reading all at once
                for line in f:
                    word = line.strip()
                    if not word:
                        continue
                    
                    # More efficient generation
                    for digits in itertools.product('0123456789', repeat=4):
                        out.write(word + ''.join(digits) + "\n")
        except FileNotFoundError:
            print(f"Error: File '{wordlist_path}' not found.", file=sys.stderr)


if __name__ == '__main__':
    try:
        wordlist = sys.argv[1]
        outfile = sys.argv[2]
        wordz = WordlistAddDigits()
        wordz.add_digits(wordlist, outfile)
    except IndexError:
        print('Usage: wordlist_add_digits.py wordlist.txt output.txt')
        sys.exit(1)
