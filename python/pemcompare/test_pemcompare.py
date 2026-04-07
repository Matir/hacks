import unittest
import sys
import io
import json
import argparse
import os
import tempfile
import re
from unittest.mock import patch, MagicMock
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa
import datetime
from ipaddress import IPv4Address

# Import the script components
from pemcompare import (
    PemCertificate, PEMCompare, CertificateFilter, main, 
    PEMCompareError, parse_args, load_pem_certificates
)

def generate_test_cert_pem(common_name: str, 
                           sans: list = None, 
                           key_type: str = "rsa",
                           key_usage: list = None,
                           extended_key_usage: list = None) -> bytes:
    if key_type == "rsa":
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    elif key_type == "ec":
        key = ec.generate_private_key(ec.SECP256R1())
    elif key_type == "dsa":
        key = dsa.generate_private_key(key_size=2048)
    else:
        raise ValueError("Unsupported key type for test generation")

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Org"),
    ])
    builder = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    )
    if sans:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(s) for s in sans]),
            critical=False
        )
    if key_usage:
        builder = builder.add_extension(
            x509.KeyUsage(**{k: True for k in key_usage}, 
                         content_commitment=False, 
                         data_encipherment=False, 
                         key_agreement=False, 
                         key_cert_sign=False, 
                         crl_sign=False, 
                         encipher_only=False, 
                         decipher_only=False),
            critical=True
        )
    if extended_key_usage:
        builder = builder.add_extension(
            x509.ExtendedKeyUsage(extended_key_usage),
            critical=False
        )
    
    cert = builder.sign(key, hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.PEM)

def generate_kitchen_sink_cert() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sink.com")])
    builder = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
    
    # SAN with IP
    builder = builder.add_extension(x509.SubjectAlternativeName([x509.IPAddress(IPv4Address("127.0.0.1"))]), critical=False)
    # Basic Constraints
    builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
    # Key Usage (lots of flags)
    builder = builder.add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=True, data_encipherment=True, key_agreement=True, key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
    # SKI and AKI
    builder = builder.add_extension(x509.SubjectKeyIdentifier(b'\x01\x02\x03\x04'), critical=False)
    builder = builder.add_extension(x509.AuthorityKeyIdentifier(b'\x05\x06\x07\x08', None, None), critical=False)
    # Unrecognized
    builder = builder.add_extension(x509.UnrecognizedExtension(x509.ObjectIdentifier("1.2.3.4"), b"custom"), critical=False)
    
    cert = builder.sign(key, hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.PEM)

class TestPemCertificate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pem_rsa = generate_test_cert_pem("rsa.com", ["www.rsa.com"], 
                                            key_usage=["digital_signature", "key_encipherment"],
                                            extended_key_usage=[ExtendedKeyUsageOID.SERVER_AUTH])
        cls.cert_rsa_obj = x509.load_pem_x509_certificate(cls.pem_rsa)
        cls.pem_cert_rsa = PemCertificate(cls.cert_rsa_obj, cls.pem_rsa.decode('ascii'))

        cls.pem_ec = generate_test_cert_pem("ec.com", key_type="ec")
        cls.cert_ec_obj = x509.load_pem_x509_certificate(cls.pem_ec)
        cls.pem_cert_ec = PemCertificate(cls.cert_ec_obj, cls.pem_ec.decode('ascii'))

        cls.pem_dsa = generate_test_cert_pem("dsa.com", key_type="dsa")
        cls.cert_dsa_obj = x509.load_pem_x509_certificate(cls.pem_dsa)
        cls.pem_cert_dsa = PemCertificate(cls.cert_dsa_obj, cls.pem_dsa.decode('ascii'))

        cls.pem_sink = generate_kitchen_sink_cert()
        cls.pem_cert_sink = PemCertificate(x509.load_pem_x509_certificate(cls.pem_sink), cls.pem_sink.decode('ascii'))

    def test_identity(self):
        alt = PemCertificate(self.cert_rsa_obj, self.pem_rsa.decode('ascii'))
        self.assertEqual(self.pem_cert_rsa, alt)
        self.assertNotEqual(self.pem_cert_rsa, self.pem_cert_ec)
        self.assertNotEqual(self.pem_cert_rsa, "not a cert")
        self.assertEqual(hash(self.pem_cert_rsa), hash(alt))

    def test_fingerprints(self):
        fprints = self.pem_cert_rsa.get_fingerprints()
        self.assertEqual(len(fprints["sha256"]), 64)
        self.assertEqual(len(fprints["sha1"]), 40)

    def test_spki_fingerprints(self):
        fprints = self.pem_cert_rsa.get_spki_fingerprints()
        self.assertIn("sha256", fprints)
        self.assertIn("sha1", fprints)

    def test_get_extensions_data(self):
        exts = self.pem_cert_rsa.get_extensions_data()
        self.assertIn("subjectAltName", exts)
        self.assertIn("keyUsage", exts)
        self.assertIn("extendedKeyUsage", exts)
        self.assertIn("digital_signature", exts["keyUsage"])
        self.assertIn("serverAuth", exts["extendedKeyUsage"])
        
        sink_exts = self.pem_cert_sink.get_extensions_data()
        self.assertIn("127.0.0.1", sink_exts["subjectAltName"])
        self.assertTrue(sink_exts["basicConstraints"]["ca"])
        # Verify SKI and AKI hex format
        self.assertEqual(sink_exts["subjectKeyIdentifier"], "01:02:03:04")
        self.assertEqual(sink_exts["authorityKeyIdentifier"], "05:06:07:08")
        self.assertTrue(any("1.2.3.4" in str(v) for v in sink_exts.values()))

    def test_to_dict(self):
        d = self.pem_cert_rsa.to_dict()
        self.assertEqual(d["subject"]["commonName"], "rsa.com")
        self.assertEqual(d["public_key"]["algorithm"], "RSAPublicKey")
        self.assertEqual(d["public_key"]["bits"], 2048)
        
        d_ec = self.pem_cert_ec.to_dict()
        self.assertEqual(d_ec["public_key"]["algorithm"], "ECPublicKey")
        self.assertEqual(d_ec["public_key"]["bits"], 256)

        d_dsa = self.pem_cert_dsa.to_dict()
        self.assertEqual(d_dsa["public_key"]["algorithm"], "DSAPublicKey")

    def test_print_text_all_flags(self):
        f = io.StringIO()
        self.pem_cert_sink.print_text(fp=f, verbose=True, san=True, with_fingerprint="sha256", pem=True)
        out = f.getvalue()
        self.assertIn("Subject: commonName=sink.com", out)
        self.assertIn("Issuer: commonName=sink.com", out)
        self.assertIn("Serial Number:", out)
        self.assertIn("Extensions:", out)
        self.assertIn("Ca: True", out)
        self.assertIn("01:02:03:04", out)
        self.assertIn("05:06:07:08", out)
        self.assertIn("Fingerprint (SHA256):", out)
        self.assertIn("-----BEGIN CERTIFICATE-----", out)

    def test_print_text_minimal(self):
        f = io.StringIO()
        self.pem_cert_rsa.print_text(fp=f, verbose=False, san=False)
        self.assertEqual(f.getvalue().strip(), "commonName=rsa.com, organizationName=Test Org")

class TestCertificateFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pem = generate_test_cert_pem("filter.com", ["alt.filter.com"])
        cls.cert = PemCertificate(x509.load_pem_x509_certificate(cls.pem), cls.pem.decode('ascii'))

    def test_filter_parsing_modes(self):
        self.assertEqual(CertificateFilter("cn=val").mode, "exact")
        self.assertEqual(CertificateFilter("cn+val").mode, "contains")
        self.assertEqual(CertificateFilter("cn~val").mode, "regex")
        self.assertEqual(CertificateFilter("cn:exact:val").mode, "exact")
        self.assertEqual(CertificateFilter("cn:val").mode, "contains")

    def test_filter_fields(self):
        fprints = self.cert.get_fingerprints()
        self.assertTrue(CertificateFilter("cn=filter.com").matches(self.cert))
        self.assertTrue(CertificateFilter(f"sha256={fprints['sha256']}").matches(self.cert))
        self.assertTrue(CertificateFilter(f"sha1={fprints['sha1']}").matches(self.cert))
        self.assertTrue(CertificateFilter(f"serial={hex(self.cert.cert.serial_number)}").matches(self.cert))
        self.assertTrue(CertificateFilter("issuer+Test Org").matches(self.cert))
        self.assertTrue(CertificateFilter(f"fingerprint={fprints['sha256']}").matches(self.cert))
        self.assertTrue(CertificateFilter("subject+filter.com").matches(self.cert))
        self.assertTrue(CertificateFilter("san+alt.filter").matches(self.cert))

    def test_filter_errors(self):
        with self.assertRaises(ValueError):
            CertificateFilter("cn~[invalid")
        with self.assertRaises(ValueError):
            CertificateFilter("invalid_mode:field:pattern")
        with self.assertRaises(ValueError):
            CertificateFilter("too:many:colons:here")
        
        f = CertificateFilter("cn=val")
        f.field = "invalid_field"
        with self.assertRaises(ValueError):
            f.matches(self.cert)

class TestPEMCompareAPI(unittest.TestCase):
    def setUp(self):
        self.c1 = PemCertificate(x509.load_pem_x509_certificate(generate_test_cert_pem("c1")), "p1")
        self.c2 = PemCertificate(x509.load_pem_x509_certificate(generate_test_cert_pem("c2")), "p2")

    def test_union(self):
        pc = PEMCompare(sources=[[self.c1], [self.c1, self.c2]], operation='union')
        self.assertEqual(len(pc.run()), 2)

    def test_intersection(self):
        pc = PEMCompare(sources=[[self.c1, self.c2], [self.c1]], operation='intersection')
        self.assertEqual(pc.run(), [self.c1])
        # Empty intersection
        pc2 = PEMCompare(sources=[[self.c1], [self.c2]], operation='intersection')
        self.assertEqual(pc2.run(), [])
        # No sources
        pc3 = PEMCompare(sources=[], operation='intersection')
        pc3.run()
        self.assertEqual(pc3.results, [])

    def test_difference(self):
        # Symmetric
        pc = PEMCompare(sources=[[self.c1], [self.c2]], operation='difference')
        res = pc.run()
        self.assertIn(self.c1, res)
        self.assertIn(self.c2, res)
        
        # Missing
        pc_m = PEMCompare(sources=[[self.c1, self.c2], [self.c2]], operation='difference', diff_mode='missing')
        self.assertEqual(pc_m.run(), [self.c1])
        
        # Added
        pc_a = PEMCompare(sources=[[self.c1], [self.c1, self.c2]], operation='difference', diff_mode='added')
        self.assertEqual(pc_a.run(), [self.c2])

    def test_render_modes(self):
        pc = PEMCompare(sources=[[self.c1, self.c2]])
        pc.run()
        f = io.StringIO()
        pc.render(fp=f, verbose=True)
        self.assertIn("Subject: commonName=c1", f.getvalue())
        self.assertIn("\n\nSubject: commonName=c2", f.getvalue())
        
        f2 = io.StringIO()
        pc.render(fp=f2, json_mode=True)
        self.assertIn('"commonName": "c1"', f2.getvalue())

    def test_source_normalization(self):
        pem = generate_test_cert_pem("stream")
        buf = io.BytesIO(pem)
        pc = PEMCompare(sources=[buf])
        self.assertEqual(len(pc.run()), 1)

    def test_errors(self):
        pc = PEMCompare(sources=[[self.c1], [self.c2]], operation=None)
        with self.assertRaises(PEMCompareError):
            pc.run()
        
        # Difference with 3 sources
        pc3 = PEMCompare(sources=[[self.c1], [self.c2], [self.c1]], operation='difference')
        with self.assertRaises(PEMCompareError):
            pc3.run()
        
        # Unknown operation
        pc4 = PEMCompare(sources=[[self.c1], [self.c2]], operation='unknown')
        with self.assertRaises(PEMCompareError):
            pc4.run()

class TestIntegration(unittest.TestCase):
    def test_load_with_junk(self):
        p1 = generate_test_cert_pem("j1")
        p2 = generate_test_cert_pem("j2")
        junk = b"junk\n" + p1 + b"\nmore junk\n" + p2 + b"\nend"
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(junk)
            path = tmp.name
        try:
            certs = load_pem_certificates(path)
            self.assertEqual(len(certs), 2)
        finally:
            os.remove(path)

    def test_load_errors(self):
        with self.assertRaises(PEMCompareError):
            load_pem_certificates(123)
        with self.assertRaises(PEMCompareError):
            load_pem_certificates("/nonexistent/file/path/12345.pem")

    def test_cli_integration(self):
        pem = generate_test_cert_pem("cli")
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as fin:
            fin.write(pem)
            in_path = fin.name
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as fout:
            out_path = fout.name
        try:
            with patch('sys.argv', ['pemcompare.py', in_path, '-o', out_path]):
                main()
            with open(out_path, 'r') as f:
                self.assertIn("commonName=cli", f.read())
        finally:
            os.remove(in_path)
            os.remove(out_path)

    def test_parse_args(self):
        with patch('sys.argv', ['pemcompare.py', 'f1.pem', '-o', 'out.json']):
            args = parse_args()
            self.assertTrue(args.json)
        
        with patch('sys.argv', ['pemcompare.py', 'f1.pem', '-o', 'OUT.JSON']):
            args = parse_args()
            self.assertTrue(args.json)

        with patch('argparse.ArgumentParser.error') as mock_error:
            with patch('sys.argv', ['pemcompare.py', 'f1.pem', 'f2.pem']):
                parse_args()
                mock_error.assert_called()

    def test_main_errors(self):
        # Trigger OSError in main
        with patch('sys.argv', ['pemcompare.py', 'f1.pem', '-o', '/nonexistent/path/out.txt']):
            with patch('pemcompare.load_pem_certificates', return_value=[]):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 1)

        # Trigger PEMCompareError in main
        with patch('sys.argv', ['pemcompare.py', 'f1.pem']):
            with patch('pemcompare.PEMCompare.run', side_effect=PEMCompareError("test")):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 1)

        # Trigger unexpected Exception in main
        with patch('sys.argv', ['pemcompare.py', 'f1.pem']):
            with patch('pemcompare.PEMCompare.run', side_effect=RuntimeError("unexpected")):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
