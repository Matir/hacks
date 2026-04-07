# PEM Comparison Tool

A robust Python CLI tool for comparing and performing set operations (union, intersection, difference) on files containing one or more PEM-encoded X.509 certificates.

## Installation

You can install this tool using `pipx` or `uv` to make the `pemcompare` command available globally.

### Using pipx
```bash
pipx install .
```

### Using uv
```bash
uv tool install .
```

## Usage

```text
usage: pemcompare [-h] [-o OUTPUT] [--union | --intersection | --difference]
                  [--only-missing | --only-added] [--json] [--san]
                  [--with-fingerprint {sha1,sha256}] [--verbose] [--pem]
                  [--filter FILTER]
                  files [files ...]
```

### Operations
When more than one input file is provided, an operation flag must be specified to determine how to combine the certificate sets.

| Flag | Description |
| :--- | :--- |
| `--union` | Prints the union of all input files. Deduplicates identical certificates (based on full DER hash) across all sources. |
| `--intersection` | Prints the intersection of all input files. Only certificates present in **every** input file are included. |
| `--difference` | Performs a difference between exactly two files. Defaults to a symmetric difference (certs in File A OR File B, but not both). |

#### Difference Modifiers
Used specifically with the `--difference` operation on two files (File A and File B).

| Flag | Description |
| :--- | :--- |
| `--only-missing` | Prints certificates present in the first file but not the second (File A - File B). |
| `--only-added` | Prints certificates present in the second file but not the first (File B - File A). |

### Filtering
The `--filter` flag allows you to prune results based on specific certificate fields. Multiple filters are combined with a logical **AND**.

**Format**: `--filter <field>[mode]<pattern>` or `--filter <field>:[mode]:<pattern>`

| Field | Description |
| :--- | :--- |
| `cn` | Common Name of the subject. |
| `san` | Subject Alternative Names. |
| `subject` | Full subject name string. |
| `issuer` | Full issuer name string. |
| `fingerprint` | Matches either SHA-1 or SHA-256 certificate fingerprints. |
| `sha1` | SHA-1 certificate fingerprint. |
| `sha256` | SHA-256 certificate fingerprint. |
| `serial` | Hexadecimal serial number. |

| Mode | Alias | Description |
| :--- | :--- | :--- |
| `exact` | `=` | Case-sensitive exact match. |
| `contains` | `+` | Case-insensitive substring match (Default). |
| `regex` | `~` | Python regular expression match. |

**Examples**:
```bash
# Find certs with CN exactly "example.com" (colon-less)
pemcompare certs.pem --filter cn=example.com

# Find certs with CN containing "google" (using + alias)
pemcompare certs.pem --filter cn+google

# Find certs with a specific SHA-256 fingerprint (standard format)
pemcompare certs.pem --filter sha256:=:5f56fd801eb8ca035e3ebe7885ad2e7f6ed2b3b1fc7d6b53891fc81bfb80085a

# Find certs where SAN matches a regex (using ~ alias)
pemcompare certs.pem --filter "san~.*\.internal$"
```


### Output Options

| Flag | Description |
| :--- | :--- |
| `-o, --output FILE` | Writes output to the specified file instead of stdout. If the filename ends in `.json`, it automatically enables `--json` mode. |
| `--json` | Outputs a detailed JSON array of dictionaries. Includes all X.509 fields, full PEM encoding, and fingerprints (Cert & SPKI). **Mutually exclusive with other output flags.** |
| `--verbose` | Prints a detailed plaintext breakout similar to `openssl x509 -text`, including Issuer, Serial, Validity, and Extensions. |
| `--san` | Prints the Subject and any Subject Alternative Names (SANs). |
| `--pem` | Prints the raw PEM-encoded certificate block for each match. |
| `--with-fingerprint {sha1,sha256}` | Appends the specified certificate fingerprint to the plaintext output. |

### Default Behavior
- If only one file is provided, it prints the subject of every certificate in that file.
- If no output flags are provided, only the certificate `Subject` is printed.
- Identity and deduplication are always calculated using the SHA-256 hash of the full DER-encoded certificate.

## JSON Structure Details
The `--json` output includes a `fingerprints` object with the following structure:
- `sha1`: SHA-1 hash of the full certificate.
- `sha256`: SHA-256 hash of the full certificate.
- `spki`: An object containing `sha1` and `sha256` hashes of the **SubjectPublicKeyInfo** (the public key only).

## Examples

**Show certificates in file A that are not in file B:**
```bash
pemcompare fileA.pem fileB.pem --difference --only-missing
```

**Find common certificates across three files and output to a JSON file:**
```bash
pemcompare f1.pem f2.pem f3.pem --intersection -o results.json
```

**Print verbose details and PEM blocks for all unique certs in a directory:**
```bash
pemcompare *.pem --union --verbose --pem
```
