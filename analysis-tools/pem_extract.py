#!/usr/bin/env python

import hashlib
import re
import sys
from cryptography import x509
from cryptography.hazmat.backends import default_backend


class PEMExtractor(object):
    """Hunt for PEM files within another file or file-like object."""

    _pem_re = re.compile(
        rb'-----BEGIN ([^-]+)-----'
        rb'[A-Za-z0-9+/\n\r]+=*[\r\n]*'
        rb'-----END \1-----')

    def __init__(self, source, block_size=5*1024*1024):
        self.block_size = block_size
        if isinstance(source, str):
            self.source = open(source, 'rb')
        else:
            try:
                getattr(source, 'read')
            except AttributeError:
                raise ValueError(
                    'source must be a filename or file-like object.')
            self.source = source

    def _get_hashes(self, pem_data):
        """Extract hash and fingerprint using cryptography library."""
        try:
            cert = x509.load_pem_x509_certificate(pem_data, default_backend())
            fingerprint = cert.fingerprint(x509.SHA256().algorithm).hex(':').upper()
            # SHA1 hash of the subject name is a common OpenSSL format for directory indexing
            subject_hash = hashlib.sha1(cert.subject.public_bytes(default_backend())).hexdigest()[:8]
            return subject_hash, fingerprint
        except Exception:
            # Not a valid X509 cert, maybe just a key or CSR
            return hashlib.sha1(pem_data).hexdigest()[:8], hashlib.sha256(pem_data).hexdigest().upper()

    def walk(self, callback, unique=True):
        chunk = b''
        seen = set()
        while True:
            tail = 0
            tmp = self.source.read(self.block_size)
            if not tmp:
                break
            chunk += tmp
            for m in self._pem_re.finditer(chunk):
                tail = max(tail, m.end())
                cert_data = m.group()
                cert_hash, fingerprint = self._get_hashes(cert_data)
                
                if not unique or fingerprint not in seen:
                    callback(cert_data, cert_hash, fingerprint)
                    seen.add(fingerprint)
            chunk = chunk[tail:]

    def save_certs(self):
        def save_single_cert(cert_data, cert_hash, fingerprint):
            filename = '{}.pem'.format(cert_hash)
            with open(filename, 'wb') as fp:
                fp.write(cert_data)
            print('Wrote {} (Fingerprint: {})'.format(filename, fingerprint))
        self.walk(save_single_cert)


if __name__ == '__main__':
    try:
        source = sys.argv[1]
    except IndexError:
        source = sys.stdin.buffer
    extractor = PEMExtractor(source)
    extractor.save_certs()
