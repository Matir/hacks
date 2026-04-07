#!/usr/bin/env python3

import argparse
import sys
import json
import hashlib
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Set, Optional, IO, Union, Tuple, Pattern, Iterable
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec, ed25519, ed448

class PEMCompareError(Exception):
    """Base exception for PEMCompare errors."""
    pass

def format_name(name: x509.Name) -> str:
    """Formats an x509.Name into a standard string representation."""
    return ", ".join([f"{attr.oid._name or attr.oid.dotted_string}={attr.value}" for attr in name])

class PemCertificate:
    def __init__(self, cert: x509.Certificate, pem_str: str) -> None:
        self.cert: x509.Certificate = cert
        self.pem_str: str = pem_str
        self.der: bytes = cert.public_bytes(serialization.Encoding.DER)
        self.sha256: str = hashlib.sha256(self.der).hexdigest()

    def __hash__(self) -> int:
        return hash(self.sha256)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PemCertificate):
            return False
        return self.sha256 == other.sha256

    def get_fingerprints(self) -> Dict[str, str]:
        return {
            "sha1": hashlib.sha1(self.der).hexdigest(),
            "sha256": self.sha256
        }

    def get_spki_fingerprints(self) -> Dict[str, str]:
        spki_bytes: bytes = self.cert.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return {
            "sha1": hashlib.sha1(spki_bytes).hexdigest(),
            "sha256": hashlib.sha256(spki_bytes).hexdigest()
        }

    def get_extensions_data(self) -> Dict[str, Any]:
        extensions: Dict[str, Any] = {}
        try:
            for ext in self.cert.extensions:
                name: str = ext.oid._name or ext.oid.dotted_string
                val: Any = ext.value
                if isinstance(val, x509.SubjectAlternativeName):
                    sans: List[str] = []
                    sans.extend(val.get_values_for_type(x509.DNSName))
                    sans.extend(val.get_values_for_type(x509.UniformResourceIdentifier))
                    sans.extend(val.get_values_for_type(x509.RFC822Name))
                    for ip in val.get_values_for_type(x509.IPAddress):
                        sans.append(str(ip))
                    extensions[name] = sans
                elif isinstance(val, x509.BasicConstraints):
                    extensions[name] = {
                        "ca": val.ca,
                        "path_length": val.path_length
                    }
                elif isinstance(val, x509.SubjectKeyIdentifier):
                    extensions[name] = ":".join(f"{b:02X}" for b in val.digest)
                elif isinstance(val, x509.AuthorityKeyIdentifier):
                    if val.key_identifier:
                        extensions[name] = ":".join(f"{b:02X}" for b in val.key_identifier)
                    else:
                        extensions[name] = str(val)
                elif isinstance(val, x509.KeyUsage):
                    usages: List[str] = []
                    try:
                        attrs = ['digital_signature', 'content_commitment', 'key_encipherment', 
                                 'data_encipherment', 'key_agreement', 'key_cert_sign', 
                                 'crl_sign', 'encipher_only', 'decipher_only']
                        for attr in attrs:
                            if getattr(val, attr, False):
                                usages.append(attr)
                    except ValueError: pass
                    extensions[name] = usages
                elif isinstance(val, x509.ExtendedKeyUsage):
                    extensions[name] = [oid._name if hasattr(oid, '_name') else str(oid) for oid in val]
                else:
                    try:
                        extensions[name] = str(val)
                    except:
                        extensions[name] = f"OID: {ext.oid.dotted_string}"
        except Exception as e:
            extensions["_error"] = str(e)
        return extensions

    def to_dict(self) -> Dict[str, Any]:
        cert: x509.Certificate = self.cert
        pk: Any = cert.public_key()
        pk_info: Dict[str, Any] = {"algorithm": pk.__class__.__name__}
        if isinstance(pk, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey, dsa.DSAPublicKey)):
            pk_info["bits"] = pk.key_size

        return {
            "version": cert.version.name,
            "serial_number": hex(cert.serial_number),
            "subject": {attr.oid._name or attr.oid.dotted_string: attr.value for attr in cert.subject},
            "issuer": {attr.oid._name or attr.oid.dotted_string: attr.value for attr in cert.issuer},
            "not_before": cert.not_valid_before_utc.isoformat(),
            "not_after": cert.not_valid_after_utc.isoformat(),
            "fingerprints": {
                **self.get_fingerprints(),
                "spki": self.get_spki_fingerprints()
            },
            "signature_algorithm": cert.signature_algorithm_oid._name or cert.signature_algorithm_oid.dotted_string,
            "public_key": pk_info,
            "extensions": self.get_extensions_data(),
            "pem": self.pem_str
        }

    def _format_extension_value(self, val: Any) -> str:
        if isinstance(val, list):
            return ", ".join(str(v).replace("_", " ").title() if "_" in str(v) else str(v) for v in val)
        if isinstance(val, dict):
            return ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in val.items())
        return str(val)

    def print_text(self, 
                   fp: IO[str] = sys.stdout,
                   verbose: bool = False,
                   san: bool = False,
                   with_fingerprint: Optional[str] = None,
                   pem: bool = False) -> None:
        cert: x509.Certificate = self.cert
        output: List[str] = []
        
        subject_str: str = format_name(cert.subject)
        if verbose or san:
            output.append(f"Subject: {subject_str}")
        else:
            output.append(subject_str)

        if verbose:
            output.append(f"  Issuer: {format_name(cert.issuer)}")
            output.append(f"  Serial Number: {hex(cert.serial_number)}")
            output.append(f"  Validity:")
            output.append(f"    Not Before: {cert.not_valid_before_utc} (UTC)")
            output.append(f"    Not After : {cert.not_valid_after_utc} (UTC)")
            output.append(f"  Signature Algorithm: {cert.signature_algorithm_oid._name or cert.signature_algorithm_oid.dotted_string}")
            
            exts: Dict[str, Any] = self.get_extensions_data()
            if exts:
                output.append("  Extensions:")
                for name, val in exts.items():
                    if name == "_error":
                        output.append(f"    Error: {val}")
                        continue
                    output.append(f"    {name}:")
                    output.append(f"      {self._format_extension_value(val)}")

        if san and not verbose:
            exts_san: Dict[str, Any] = self.get_extensions_data()
            if "subjectAltName" in exts_san:
                output.append(f"  SAN: {', '.join(exts_san['subjectAltName'])}")

        if with_fingerprint:
            fprints: Dict[str, str] = self.get_fingerprints()
            output.append(f"  Fingerprint ({with_fingerprint.upper()}): {fprints[with_fingerprint]}")

        print("\n".join(output), file=fp)
        
        if pem:
            print(self.pem_str, file=fp)

class CertificateFilter:
    def __init__(self, filter_spec: str) -> None:
        if ":" in filter_spec:
            parts: List[str] = filter_spec.split(":", 2)
            if len(parts) == 3:
                self.field: str = parts[0].lower()
                self.mode: str = parts[1].lower()
                self.pattern: str = parts[2]
            else:
                self.field = parts[0].lower()
                self.mode = "contains"
                self.pattern = parts[1]
        else:
            match = re.match(r"^([^=+~]+)([=+~])(.*)$", filter_spec)
            if match:
                self.field = match.group(1).lower()
                op = match.group(2)
                self.pattern = match.group(3)
                if op == "=": self.mode = "exact"
                elif op == "+": self.mode = "contains"
                elif op == "~": self.mode = "regex"
            else:
                raise ValueError(f"Invalid filter specification: {filter_spec}")

        if self.mode in ("exact", "="):
            self.mode = "exact"
        elif self.mode in ("contains", "+"):
            self.mode = "contains"
        elif self.mode in ("regex", "~", "r"):
            self.mode = "regex"
            try:
                self.compiled_re: Pattern[str] = re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{self.pattern}': {e}")
        else:
            raise ValueError(f"Invalid filter mode: {self.mode}")

    def matches(self, pem_cert: PemCertificate) -> bool:
        values: List[str] = []
        if self.field == "cn":
            cn_attrs: List[x509.NameAttribute] = pem_cert.cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            values = [attr.value for attr in cn_attrs]
        elif self.field == "san":
            exts: Dict[str, Any] = pem_cert.get_extensions_data()
            if "subjectAltName" in exts:
                values = exts["subjectAltName"]
        elif self.field == "subject":
            values = [format_name(pem_cert.cert.subject)]
        elif self.field == "issuer":
            values = [format_name(pem_cert.cert.issuer)]
        elif self.field == "fingerprint":
            fprints: Dict[str, str] = pem_cert.get_fingerprints()
            values = [fprints["sha1"], fprints["sha256"]]
        elif self.field == "sha1":
            values = [pem_cert.get_fingerprints()["sha1"]]
        elif self.field == "sha256":
            values = [pem_cert.sha256]
        elif self.field == "serial":
            values = [hex(pem_cert.cert.serial_number)]
        else:
            raise ValueError(f"Invalid filter field: {self.field}")

        for val in values:
            if self.mode == "exact":
                if val == self.pattern: return True
            elif self.mode == "contains":
                if self.pattern.lower() in val.lower(): return True
            elif self.mode == "regex":
                if self.compiled_re.search(val): return True
        return False

def load_pem_certificates(source: Union[str, IO[bytes], List[PemCertificate]]) -> List[PemCertificate]:
    """Loads certificates from various source types."""
    if isinstance(source, list):
        if all(isinstance(c, PemCertificate) for c in source):
            return source
        raise PEMCompareError("Source list must contain PemCertificate objects.")
    
    data: bytes
    source_name: str = "stream"
    try:
        if isinstance(source, str):
            source_name = source
            with open(source, "rb") as f:
                data = f.read()
        elif hasattr(source, "read"):
            data = source.read()
        else:
            raise PEMCompareError(f"Unsupported source type: {type(source)}")
    except Exception as e:
        raise PEMCompareError(f"Error reading source {source_name}: {e}")

    certs: List[PemCertificate] = []
    if hasattr(x509, "load_pem_x509_certificates"):
        try:
            loaded_certs = x509.load_pem_x509_certificates(data)
            for cert in loaded_certs:
                pem_bytes = cert.public_bytes(serialization.Encoding.PEM)
                certs.append(PemCertificate(cert, pem_bytes.decode("ascii").strip()))
        except Exception as e:
            # Fallback will handle it
            pass
    
    if not certs:
        pattern = re.compile(b"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.DOTALL)
        for match in pattern.finditer(data):
            pem_data: bytes = match.group(0)
            try:
                cert = x509.load_pem_x509_certificate(pem_data)
                certs.append(PemCertificate(cert, pem_data.decode("ascii").strip()))
            except Exception as e:
                # In strict mode (library), we might want to raise, but let's maintain current skip-and-warn
                print(f"Warning: Skipping invalid certificate in {source_name}: {e}", file=sys.stderr)
    return certs

class PEMCompare:
    def __init__(self, 
                 sources: Union[List[str], List[IO[bytes]], List[List[PemCertificate]]],
                 operation: Optional[str] = None,
                 diff_mode: str = 'symmetric',
                 filters: Optional[List[Union[str, CertificateFilter]]] = None) -> None:
        self.raw_sources = sources
        self.operation = operation
        self.diff_mode = diff_mode
        self.filter_specs = filters or []
        self.results: List[PemCertificate] = []
        self._parsed_filters: List[CertificateFilter] = []
        
        # Parse filters
        for f in self.filter_specs:
            if isinstance(f, str):
                self._parsed_filters.append(CertificateFilter(f))
            else:
                self._parsed_filters.append(f)

    def run(self) -> List[PemCertificate]:
        # Load all sources
        all_file_certs = [load_pem_certificates(s) for s in self.raw_sources]
        
        if len(all_file_certs) == 1:
            result_certs = all_file_certs[0]
        else:
            if self.operation == 'union':
                seen: Set[str] = set()
                result_certs = []
                for file_certs in all_file_certs:
                    for cert in file_certs:
                        if cert.sha256 not in seen:
                            result_certs.append(cert)
                            seen.add(cert.sha256)
            elif self.operation == 'intersection':
                if not all_file_certs:
                    result_certs = []
                else:
                    sets: List[Set[PemCertificate]] = [set(file_certs) for file_certs in all_file_certs]
                    common_hashes: Set[PemCertificate] = sets[0].intersection(*sets[1:])
                    result_certs = [c for c in all_file_certs[0] if c in common_hashes]
            elif self.operation == 'difference':
                if len(all_file_certs) != 2:
                    raise PEMCompareError("Difference operation requires exactly two sources.")
                f1_certs: Set[PemCertificate] = set(all_file_certs[0])
                f2_certs: Set[PemCertificate] = set(all_file_certs[1])
                
                if self.diff_mode == 'missing':
                    diff_hashes = f1_certs - f2_certs
                    result_certs = [c for c in all_file_certs[0] if c in diff_hashes]
                elif self.diff_mode == 'added':
                    diff_hashes = f2_certs - f1_certs
                    result_certs = [c for c in all_file_certs[1] if c in diff_hashes]
                else:
                    d1: Set[PemCertificate] = f1_certs - f2_certs
                    d2: Set[PemCertificate] = f2_certs - f1_certs
                    result_certs = ([c for c in all_file_certs[0] if c in d1] + 
                                    [c for c in all_file_certs[1] if c in d2])
            else:
                raise PEMCompareError(f"Unknown or missing operation for multiple sources: {self.operation}")

        # Apply filters
        if self._parsed_filters:
            filtered_certs: List[PemCertificate] = []
            for cert in result_certs:
                if all(f.matches(cert) for f in self._parsed_filters):
                    filtered_certs.append(cert)
            result_certs = filtered_certs

        self.results = result_certs
        return self.results

    def render(self, 
               fp: IO[str] = sys.stdout, 
               json_mode: bool = False,
               verbose: bool = False,
               san: bool = False,
               with_fingerprint: Optional[str] = None,
               pem: bool = False) -> None:
        if json_mode:
            json_output: List[Dict[str, Any]] = [c.to_dict() for c in self.results]
            print(json.dumps(json_output, indent=2), file=fp)
        else:
            for i, cert in enumerate(self.results):
                cert.print_text(fp=fp, verbose=verbose, san=san, 
                                with_fingerprint=with_fingerprint, pem=pem)
                if verbose and i < len(self.results) - 1:
                    print(file=fp)

def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="PEM Certificate Comparison Tool")
    parser.add_argument("files", nargs="+", help="Input PEM files")
    parser.add_argument("-o", "--output", help="Output file path")
    
    op_group: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    op_group.add_argument("--union", action="store_true", help="Perform union of all files")
    op_group.add_argument("--intersection", action="store_true", help="Perform intersection of all files")
    op_group.add_argument("--difference", action="store_true", help="Perform difference of exactly two files")
    
    diff_group: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    diff_group.add_argument("--only-missing", action="store_true", help="Print certs in first file but not second")
    diff_group.add_argument("--only-added", action="store_true", help="Print certs in second file but not first")

    out_group: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group()
    out_group.add_argument("--json", action="store_true", help="Output as JSON array")
    
    pt_group: argparse._ArgumentGroup = parser.add_argument_group("Plaintext output options")
    pt_group.add_argument("--san", action="store_true", help="Print Subject Alternative Names")
    pt_group.add_argument("--with-fingerprint", choices=["sha1", "sha256"], help="Include fingerprint")
    pt_group.add_argument("--verbose", action="store_true", help="Print all X509 fields")
    pt_group.add_argument("--pem", action="store_true", help="Print PEM-encoded certificates")

    parser.add_argument("--filter", action="append", help="Filter results by field:mode:pattern")

    args: argparse.Namespace = parser.parse_args()

    if args.output and args.output.lower().endswith(".json"):
        if not (args.san or args.with_fingerprint or args.verbose or args.pem or args.json):
            args.json = True

    if args.json:
        if args.san or args.with_fingerprint or args.verbose or args.pem:
            parser.error("--json is mutually exclusive with --san, --with-fingerprint, --verbose, and --pem.")
            
    if len(args.files) > 1 and not (args.union or args.intersection or args.difference):
        parser.error("Multiple files provided but no operation flag specified.")

    return args

def main() -> None:
    args: argparse.Namespace = parse_args()
    
    # Map CLI to PEMCompare
    operation = None
    if args.union: operation = 'union'
    elif args.intersection: operation = 'intersection'
    elif args.difference: operation = 'difference'
    
    diff_mode = 'symmetric'
    if args.only_missing: diff_mode = 'missing'
    elif args.only_added: diff_mode = 'added'
    
    try:
        pc = PEMCompare(
            sources=args.files,
            operation=operation,
            diff_mode=diff_mode,
            filters=args.filter
        )
        pc.run()
        
        # Determine output stream
        fp: IO[str]
        if args.output:
            try:
                fp = open(args.output, "w")
            except OSError as e:
                print(f"Error opening output file {args.output}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            fp = sys.stdout

        try:
            pc.render(
                fp=fp,
                json_mode=args.json,
                verbose=args.verbose,
                san=args.san,
                with_fingerprint=args.with_fingerprint,
                pem=args.pem
            )
        finally:
            if args.output:
                fp.close()
                
    except (PEMCompareError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
