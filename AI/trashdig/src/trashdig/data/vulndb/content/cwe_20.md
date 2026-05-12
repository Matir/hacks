# CWE-20: Improper Input Validation

### Description
CWE-20 occurs when a software application receives input from an upstream component or untrusted source but does not validate, or incorrectly validates, that the input has the properties required to process it safely and correctly. Input validation is a fundamental security requirement. When an application fails to verify that input conforms to expected formats (such as length, type, syntax, or range), it allows attackers to provide unexpected data that can lead to unintended code execution, crashes, or data manipulation.

This vulnerability is often a "root cause" for many other security issues, including Command Injection, Cross-Site Scripting (XSS), SQL Injection, and Path Traversal.

### Impact
The impact of improper input validation varies significantly depending on how the unvalidated data is used within the application:
*   **Remote Code Execution (RCE):** If the input is passed to system commands or dynamic evaluation functions.
*   **Denial of Service (DoS):** If the input triggers high resource consumption (e.g., extremely large numbers or long strings causing buffer overflows or infinite loops).
*   **Data Corruption:** If invalid data is written to a database or configuration file.
*   **Bypassing Security Controls:** If the input is used to make authorization or authentication decisions.
*   **Injection Attacks:** Serving as the entry point for SQLi, XSS, or LDAP injection.

### Remediation
The most effective way to address CWE-20 is through a strict "allow-list" approach rather than a "deny-list" approach.

1.  **Use an Allow-list:** Define exactly what is permitted (e.g., specific characters, data types, or value ranges) and reject everything else.
2.  **Type Checking:** Ensure the data is of the expected type (e.g., Integer, Boolean, String).
3.  **Length Validation:** Enforce minimum and maximum length constraints.
4.  **Range Validation:** For numeric input, verify it falls within a safe logical range.
5.  **Syntax and Format Validation:** Use regular expressions or specialized parsers to ensure the data matches expected patterns (e.g., email formats, zip codes).
6.  **Library-based Validation:** Use established validation libraries (like Marshmallow for Python, Joi for Node.js, or Hibernate Validator for Java) to centralize validation logic.

### Examples

#### Vulnerable Code (Python)
In this example, the application takes a username from a query parameter and uses it directly in a system command without any validation.

```python
import os
from flask import Flask, request

app = Flask(__name__)

@app.route('/check_user')
def check_user():
    username = request.args.get('username')
    # VULNERABLE: Direct use of unvalidated input in a shell command
    os.system(f"id {username}")
    return "Check completed"
```

#### Secure Code (Python)
The secure version validates the input against an allow-list (only alphanumeric characters) and uses a safer API for execution.

```python
import subprocess
import re
from flask import Flask, request, abort

app = Flask(__name__)

@app.route('/check_user')
def check_user():
    username = request.args.get('username')
    
    # SECURE: Validate that the input matches an expected pattern (alphanumeric only)
    if not username or not re.match(r"^[a-zA-Z0-9]+$", username):
        abort(400, "Invalid username format")
    
    # SECURE: Use subprocess.run with a list to prevent shell injection
    result = subprocess.run(["id", username], capture_output=True, text=True)
    return f"User info: {result.stdout}"
```