## Description

OS Command Injection (also known as Shell Injection) occurs when an application directs an operating system command to be executed, incorporating unsanitized data from an untrusted source (such as user input, cookies, or HTTP headers) into the command string. Because the command is interpreted by a shell (like `/bin/sh` or `cmd.exe`), attackers can use shell metacharacters—such as `;`, `&`, `|`, or backticks—to break out of the intended command and execute arbitrary system-level instructions.

This vulnerability typically occurs when developers attempt to use system utilities (like `ping`, `nslookup`, or `mail`) to perform tasks rather than using the native APIs provided by the programming language.

## Impact

The impact of OS Command Injection is almost always **Critical**.
*   **Remote Code Execution (RCE):** Attackers can execute any command with the privileges of the application process.
*   **Full System Compromise:** Attackers can install persistent backdoors, create new administrative users, or pivot to other systems on the internal network.
*   **Data Exfiltration:** Attackers can read sensitive configuration files (like `/etc/passwd` or environment variables containing API keys) and database records.
*   **Service Disruption:** Attackers can stop services, delete files, or encrypt the system (Ransomware).

## Remediation

The most effective way to prevent OS Command Injection is to **avoid calling OS commands directly**.

### 1. Use Native APIs
Instead of calling a shell command to perform a task, use the library or built-in functions provided by the language.
*   *Instead of:* Calling `rm -rf /tmp/files`, use `os.remove()` in Python or `fs.unlink()` in Node.js.
*   *Instead of:* Calling `mkdir`, use `os.mkdir()`.

### 2. Avoid the Shell (Parameterization)
If you must execute an external program, do not invoke the system shell. Most languages provide APIs that allow you to pass the command and its arguments as a **list/array**. This ensures the OS treats the input as literal data rather than executable shell code.
*   **Python:** Use `subprocess.run(["ls", folder_path], shell=False)`.
*   **Java:** Use `ProcessBuilder`.
*   **Node.js:** Use `child_process.spawn()`.

### 3. Input Validation (Whitelisting)
If input must be used, validate it against a strict whitelist. For example, if an input is supposed to be a number or a alphanumeric filename, reject any input containing shell characters (`;`, `&`, `|`, `$`, `>`, etc.).

## Examples

### Python

**Vulnerable Example:**
Using `shell=True` allows the shell to interpret metacharacters in the `address` variable.
```python
import subprocess

def check_server(address):
    # If address is "8.8.8.8; cat /etc/passwd", the password file is leaked.
    command = "ping -c 1 " + address
    subprocess.run(command, shell=True)
```

**Secure Example:**
By passing a list and setting `shell=False` (the default), the input is treated as a single argument to the `ping` utility, not a shell command.
```python
import subprocess

def check_server(address):
    # The shell is not invoked; ";" is treated as part of the address string.
    subprocess.run(["ping", "-c", "1", address], shell=False)
```

### Node.js

**Vulnerable Example:**
The `exec` function invokes a shell, making it susceptible to injection.
```javascript
const { exec } = require('child_process');

function listFiles(directory) {
  // Input like "; rm -rf /" would be catastrophic
  exec(`ls -l ${directory}`, (err, stdout) => {
    console.log(stdout);
  });
}
```

**Secure Example:**
`spawn` does not use a shell by default and handles arguments safely.
```javascript
const { spawn } = require('child_process');

function listFiles(directory) {
  const ls = spawn('ls', ['-l', directory]);
  ls.stdout.on('data', (data) => {
    console.log(data.toString());
  });
}
```