# CWE-77: Improper Neutralization of Special Elements used in a Command ('Command Injection')

## Description

Command Injection vulnerabilities occur when an application passes unvalidated or improperly sanitized user input to a system shell. An attacker can use shell metacharacters (such as `;`, `&`, `|`, `&&`, `||`, `` ` ``, or `$()`) to append or inject their own arbitrary commands into the intended command string.

Unlike Code Injection, where the attacker injects code that is executed by the application's runtime environment (e.g., Python, PHP), Command Injection involves the execution of commands directly on the operating system. This usually happens when developers use functions designed to execute external programs or scripts via the shell.

## Impact

The impact of Command Injection is almost always **Critical**. Potential consequences include:

*   **Remote Code Execution (RCE):** Attackers can execute any command with the privileges of the application process.
*   **Full System Compromise:** Attackers may gain a persistent shell, install malware, or create new administrative users.
*   **Data Exfiltration:** Attackers can read sensitive files (e.g., `/etc/passwd`, configuration files with credentials) and send them to remote servers.
*   **Lateral Movement:** The compromised server can be used as a jumping point to attack other internal systems within the network.
*   **Denial of Service (DoS):** Attackers can execute commands that crash the system or consume all available resources.

## Remediation

### 1. Avoid Calling OS Commands Directly
The best defense is to avoid invoking shell commands whenever possible. Most programming languages provide native APIs or libraries that perform the same tasks without involving a shell (e.g., using a library to manipulate files instead of calling `rm` or `mkdir`).

### 2. Use Argument Lists (No Shell)
If you must call an external command, use functions that accept arguments as a list or array rather than a single concatenated string. This bypasses the shell interpreter entirely, ensuring that input is treated as data, not as executable code.

### 3. Input Validation (Allow-listing)
If input must be passed to a command, validate it against a strict allow-list of expected characters or values. For example, if an input is supposed to be an IP address, ensure it matches a strict regex for IPv4/IPv6.

### 4. Escaping and Sanitization
As a last resort, use library-provided functions to escape shell metacharacters. However, this is error-prone and platform-dependent (Windows `cmd.exe` vs. Linux `sh/bash`).

## Examples

### Python

**Vulnerable Code**
Using `shell=True` with string formatting allows an attacker to inject commands.
```python
import os
import subprocess

def check_server_status(hostname):
    # DANGER: hostname is concatenated into a shell command
    command = "ping -c 1 " + hostname
    subprocess.run(command, shell=True)

# Attacker input: "8.8.8.8; cat /etc/passwd"
```

**Secure Code**
Passing arguments as a list and setting `shell=False` (the default) prevents injection.
```python
import subprocess

def check_server_status(hostname):
    # SAFE: Arguments are passed as a list; no shell is invoked.
    subprocess.run(["ping", "-c", "1", hostname], shell=False)
```

### Node.js

**Vulnerable Code**
`child_process.exec` spawns a shell by default.
```javascript
const { exec } = require('child_process');

function listFiles(directoryName) {
    // DANGER: directoryName is not sanitized
    exec(`ls -l ${directoryName}`, (error, stdout, stderr) => {
        console.log(stdout);
    });
}
// Attacker input: " . ; rm -rf /"
```

**Secure Code**
`child_process.execFile` does not spawn a shell.
```javascript
const { execFile } = require('child_process');

function listFiles(directoryName) {
    // SAFE: execFile treats arguments as literals, not shell commands
    execFile('ls', ['-l', directoryName], (error, stdout, stderr) => {
        console.log(stdout);
    });
}
```