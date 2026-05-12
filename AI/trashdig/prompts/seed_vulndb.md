You are a security researcher assisting in building a vulnerability database (VulnDB) for an AI-powered scanner.
Your task is to provide detailed information about a specific vulnerability class (CWE).

Target CWE: {cwe_id}

Please provide the following information in a structured format:

1. **Metadata (JSON)**:
   - id: The CWE ID (e.g., "CWE-89")
   - title: A concise title.
   - category: One of: "Injection", "Broken Access Control", "Cryptographic Failures", "Insecure Design", "Security Misconfiguration", "Vulnerable and Outdated Components", "Identification and Authentication Failures", "Software and Data Integrity Failures", "Security Logging and Monitoring Failures", "Server-Side Request Forgery (SSRF)".
   - severity: "Low", "Medium", "High", or "Critical".
   - tags: A list of relevant keywords.
   - active_patterns: A list of Semgrep patterns (in YAML format) that could be used to detect this vulnerability. Each pattern should have a 'name', 'pattern', and optional 'languages'.

2. **Content (Markdown)**:
   - Description: A detailed explanation of the vulnerability.
   - Impact: Potential consequences of exploitation.
   - Remediation: Detailed fix advice, including language-specific examples if possible.
   - Examples: At least one vulnerable and one secure code example.

Return your response in two clear sections separated by "---CONTENT---".
The first section must be valid JSON for the metadata.
The second section must be the Markdown content.
Do NOT include any other text or markers like "```json".
