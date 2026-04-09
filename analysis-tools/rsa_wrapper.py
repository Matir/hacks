#!/usr/bin/env python
# basic rsa functions
import sys
import zlib
import base64
from Crypto.PublicKey import RSA 
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15


class RSAWrapper():
  
  def keygen(self, size=2048):
    key = RSA.generate(size, e=65537) 
    public = key.publickey().export_key("PEM") 
    private = key.export_key("PEM") 
    return public, private

  def _get_cipher(self, key_pem):
    rsakey = RSA.import_key(key_pem)
    # Using SHA256 for OAEP is more modern
    return PKCS1_OAEP.new(rsakey, hashAlgo=SHA256)

  def encrypt(self, public_pem, plaintext):
    if isinstance(plaintext, str):
      plaintext = plaintext.encode('utf-8')
    
    cipher = self._get_cipher(public_pem)
    # Max size for OAEP: key_size_bytes - 2*hash_size - 2
    # For 2048-bit (256 bytes) and SHA-256 (32 bytes): 256 - 64 - 2 = 190
    max_chunk = cipher._key.size_in_bytes() - 2 * SHA256.digest_size - 2
    
    offset = 0
    encrypted = b""
    # Compress entire payload
    compressed = zlib.compress(plaintext)
    
    while offset < len(compressed):
      chunk = compressed[offset:offset+max_chunk]
      encrypted += cipher.encrypt(chunk)
      offset += max_chunk
      
    return base64.b64encode(encrypted)

  def decrypt(self, private_pem, ciphertext_b64):
    cipher = self._get_cipher(private_pem)
    # Ciphertext chunk size is always the key size in bytes
    chunk_size = cipher._key.size_in_bytes()
    
    ciphertext = base64.b64decode(ciphertext_b64)
    offset = 0
    decrypted_chunks = b""
    
    while offset < len(ciphertext):
      chunk = ciphertext[offset:offset+chunk_size]
      decrypted_chunks += cipher.decrypt(chunk)
      offset += chunk_size
      
    return zlib.decompress(decrypted_chunks)

  def sign(self, private_pem, plaintext):
    if isinstance(plaintext, str):
      plaintext = plaintext.encode('utf-8')
    rsakey = RSA.import_key(private_pem)
    hashed = SHA256.new(plaintext)
    return pkcs1_15.new(rsakey).sign(hashed)

  def verify(self, public_pem, signature, plaintext):
    if isinstance(plaintext, str):
      plaintext = plaintext.encode('utf-8')
    rsakey = RSA.import_key(public_pem)
    hashed = SHA256.new(plaintext)
    try:
      pkcs1_15.new(rsakey).verify(hashed, signature)
      return True
    except (ValueError, TypeError):
      return False
    

if __name__ == '__main__':
  try:
    message = sys.argv[1]
    rsa = RSAWrapper()
    public, private = rsa.keygen()
    
    print("Public Key is:\n{}\n".format(public.decode('ascii')))
    print("Private Key is:\n{}\n".format(private.decode('ascii')))

    encrypted_message = rsa.encrypt(public, message)
    print("Test message encrypted with public key is:\n{}\n".format(encrypted_message.decode('ascii')))

    decrypted_message = rsa.decrypt(private, encrypted_message)
    print("Testing decryption function to return original message:\n{}\n".format(decrypted_message.decode('utf-8')))

    signature = rsa.sign(private, message)
    print("Plaintext message signature (B64) is:\n{}\n".format(base64.b64encode(signature).decode('ascii')))

    verified = rsa.verify(public, signature, message)
    print("Verifying the plaintext against the signature results in:\n{}\n".format(verified))

  except IndexError:
    print("Usage: python rsa_wrapper.py <message>")
  except Exception as e:
    print(f"Error during RSA operation: {e}")
