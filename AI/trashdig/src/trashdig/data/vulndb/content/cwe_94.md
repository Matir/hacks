# CWE-94: Improper Control of Generation of Code ('Code Injection')

### Description

CWE-94 occurs when an application includes untrusted data in a code segment that is subsequently executed by the application's runtime environment. Unlike OS Command Injection (CWE-78), which involves executing shell commands, Code Injection involves injecting code in the same programming language as the application (e.g., Python, PHP, JavaScript). 

This typically happens when developers use powerful "evaluator" functions—intended to evaluate strings as expressions or code—directly on user-supplied input without sufficient validation. This vulnerability is common in environments where dynamic code execution is a built-in feature of the language.

### Impact

The impact of Code Injection is almost always **Critical**. If an attacker successfully injects code, they typically achieve:

*   **Remote Code Execution (RCE):** The attacker can run arbitrary instructions within the application process.
*   **Full System Compromise:** The attacker may gain the same permissions as the application user, allowing them to read sensitive files, modify data, or install persistent backdoors.
*   **Data Exfiltration:** Attackers can access databases, environment variables (containing API keys), and internal source code.
*   **Lateral Movement:** The compromised server can be used as a jumping-off point to attack other internal network resources.

### Remediation

The most effective remediation is to **avoid dynamic code execution entirely**. 

1.  **Eliminate Dangerous Functions:** Avoid using `eval()`, `exec()`, `passthru()`, or the `Function` constructor in JavaScript with any data that could be influenced by a user.
2.  **Use Static Lookups:** Instead of evaluating a string to call a function or access a variable, use a predefined dictionary or map to route user input to specific logic.
3.  **Strict Allow-listing:** If you must accept dynamic input to determine logic, validate it against a strict allow-list of permitted values.
4.  **Use Safer Alternatives:** 
    *   In **Python**, use `ast.literal_eval()` if you only need to parse strings into basic Python data structures (like dictionaries or lists), as it does not execute code.
    *   In **JavaScript**, use `JSON.parse()` instead of `eval()` for parsing data.
5.  **Sandbox Execution:** If dynamic execution is a core feature (e.g., a code-learning platform), use highly restricted sandboxes or containers with no network access and minimal filesystem permissions.

### Examples

#### Python

**Vulnerable Example**
In this Flask application, the user provides a formula which is executed directly. An attacker could pass `__import__('os').system('id')` to execute system commands.

```python
from flask import request

@app.route("/calculate")
def calculate():
    formula = request.args.get('formula')
    # DANGEROUS: eval() interprets the string as Python code
    return str(eval(formula))
```

**Secure Example**
Use a mapping to handle specific operations, ensuring no arbitrary code is ever evaluated.

```python
from flask import request

@app.route("/calculate")
def calculate():
    op = request.args.get('op')
    val1 = int(request.args.get('v1', 0))
    val2 = int(request.args.get('v2', 0))

    # SAFE: Logic is restricted to predefined operations
    allowed_ops = {
        'add': lambda x, y: x + y,
        'sub': lambda x, y: x - y
    }

    if op in allowed_ops:
        result = allowed_ops[op](val1, val2)
        return str(result)
    return "Invalid Operation", 400
```

#### PHP

**Vulnerable Example**
```php
<?php
// DANGEROUS: User input is passed directly to eval
$user_code = $_GET['id'];
eval("\$data = get_data_for_" . $user_code . "();");
?>
```

**Secure Example**
```php
<?php
// SAFE: Use a switch statement or allow-list to control execution flow
$user_id = $_GET['id'];

switch ($user_id) {
    case 'profile':
        get_data_for_profile();
        break;
    case 'settings':
        get_data_for_settings();
        break;
    default:
        die("Invalid ID");
}
?>
```