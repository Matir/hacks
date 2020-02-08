import os
import os.path
import struct
import sys
import zipfile
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA

# We prefer cStringIO if possible
try:
  from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO

_CRX_HEADER_FORMAT = '<4sIII'

def crx_extract(fname):
  basename, ext = os.path.splitext(os.path.basename(fname))
  try:
    os.mkdir(basename)
  except OSError:
    sys.stderr.write('Unable to make directory %s\n' % basename)
    os._exit(1)

  try:
    fp = open(fname, "r")
  except:
    raise

  try:
    pk, sig = _crx_get_header(fp)
  except CRXException:
    raise

  # Pull all remaining data into a StringIO
  buf = StringIO(fp.read())
  if not _crx_verify(pk, sig, buf.read()):
    raise CRXException("Key verification failed!")

  buf.seek(0)
  _crx_zf_extract(buf)

def _crx_get_header(fp):
  # Read the early header
  hdr_len = struct.calcsize(_CRX_HEADER_FORMAT)
  magic, version, pklen, siglen = struct.unpack(
      _CRX_HEADER_FORMAT, fp.read(hdr_len))
  if magic != 'Cr24':
    raise CRXException('Invalid magic signature in crx file.')
  if version != 2:
    raise CRXException('Can only read version 2 crx files.')

  # Read signature and public key
  sig_format = '%ds%ds' % (pklen, siglen)
  pksig_len = struct.calcsize(sig_format)
  pk, sig = struct.unpack(sig_format, fp.read(pksig_len))

  return pk, sig

def _crx_zf_extract(buf):
  with zipfile.ZipFile(buf, 'r') as zf:
    _crx_zf_sanitize(zf)
    zf.extractall(basename)

def _crx_zf_sanitize(zf):
  # Make sure no files contain malicious paths
  for name in zf.namelist():
    print 'File: %s' % name
    name = os.path.normpath(name)
    if name.startswith(('/', '../')):
      raise CRXException('Bad path in ZipFile: %s' % name)

def _crx_verify(pk, sig, buf):
  rsa = RSA.importKey(pk)
  msg_sha = SHA.new(buf)
  digest = msg_sha.hexdigest()
  digest = int(digest, 16)
  sig = ''.join(['%02x' % ord(x) for x in sig])
  sig = int(sig, 16)
  return rsa.verify(digest, (sig,))

def main(argv):
  try:
    fname = argv[1]
  except IndexError:
    sys.stderr.write('Usage: %s <filename>\n' % argv[0])
    os._exit(os.EX_USAGE)
  crx_extract(fname)


class CRXException(Exception):
  pass

if __name__ == '__main__':
  main(sys.argv)
