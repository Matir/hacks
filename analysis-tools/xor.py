#!/usr/bin/env python
# -*- coding: utf-8 -*-
#xor file
import sys
from itertools import cycle


class Xor():

    def xor(self, original_file, new_file, xor_var, chunk_size=65536):
        """XOR a file with a key, using memory-efficient chunking."""
        key_cycle = cycle(xor_var)
        
        try:
            with open(original_file, 'rb') as f_in, \
                 open(new_file, 'wb') as f_out:
                
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    
                    # XOR the chunk with the cyclic key
                    result = bytes([b ^ next(key_cycle) for b in chunk])
                    f_out.write(result)
        except FileNotFoundError:
            print(f"Error: File '{original_file}' not found.", file=sys.stderr)

    def hexToByte(self, hexStr):
        hexStr = ''.join(hexStr.split(" "))
        return bytes.fromhex(hexStr)


if __name__ == '__main__':
    try:
        transform = Xor()
        original_file = sys.argv[1]
        new_file = sys.argv[2]
        xor_key = transform.hexToByte(sys.argv[3])
        transform.xor(original_file, new_file, xor_key)
    except IndexError:
        print('Usage: xor.py <input_file> <output_file> <"XOR hex bytes">')
        sys.exit(1)
    except ValueError:
        print('Error: Invalid hex bytes provided.')
        sys.exit(1)
