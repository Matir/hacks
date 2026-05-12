## Description

**CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')** occurs when an application includes untrusted data in a web page without proper validation or encoding. This allows an attacker to inject malicious scripts into the web pages viewed by other users. When the victim's browser loads the page, the malicious script executes within the context of that user's session.

Cross-site Scripting (XSS) is generally divided into three main types:
1.  **Reflected XSS:** The malicious script is "reflected" off a web application to the victim's browser. It is typically delivered via a link (e.g., in a URL parameter) and is not stored on the server.
2.  **Stored (Persistent) XSS:** The malicious script is permanently stored on the target server (e.g., in a database, in a comment field, or user profile). When a user navigates to the affected page, the script executes.
3.  **DOM-based XSS:** The vulnerability exists in client-side code rather than server-side code. The script is executed when the application contains client-side JavaScript that processes data from an untrusted source in an unsafe way, usually by writing the data to a dangerous Sink (like `innerHTML`).

## Impact

The impact of XSS is broad because the script runs in the context of the user’s browser. Potential consequences include:
*   **Session Hijacking:** Stealing session cookies (especially if the `HttpOnly` flag is missing), allowing the attacker to take over the user's account.
*   **Phishing and Credential Theft:** Injecting fake login forms to steal usernames and passwords.
*   **Data Exfiltration:** Accessing sensitive data displayed on the page or accessible via the DOM.
*   **Malware Distribution:** Redirecting users to malicious websites or triggering drive-by downloads.
*   **Site Defacement:** Changing the visual appearance of the website to spread misinformation or damage reputation.

## Remediation

To prevent XSS, developers must ensure that untrusted data is never treated as executable code by the browser.

### 1. Context-Aware Output Encoding
This is the primary defense. Convert special characters into their HTML entity equivalents before rendering them in the browser. The encoding must match the context:
*   **HTML Body:** `<` becomes `&lt;`, `>` becomes `&gt;`.
*   **HTML Attributes:** Encode all non-alphanumeric characters.
*   **JavaScript:** Use Unicode escapes (e.g., `\u003C`) when placing data inside `<script>` blocks.

### 2. Use Safe APIs
In JavaScript, avoid sinks that interpret strings as HTML. 
*   **Unsafe:** `element.innerHTML = user_input;`
*   **Safe:** `element.textContent = user_input;`

### 3. Content Security Policy (CSP)
Implement a strong CSP header to restrict where scripts can be loaded from and prevent the execution of inline scripts. 
Example: `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none';`

### 4. Enable HttpOnly Cookies
Set the `HttpOnly` flag on session cookies to prevent them from being accessed via `document.cookie`, which mitigates the impact of session hijacking even if an XSS vulnerability exists.

## Examples

### Vulnerable Example (PHP)
In this example, the user input from the URL parameter `name` is printed directly into the HTML, allowing for Reflected XSS.

```php
<?php
$name = $_GET['name'];
// VULNERABLE: Direct output of user input
echo "<h1>Welcome, " . $name . "</h1>";
?>
```
*Payload:* `?name=<script>alert(document.cookie)</script>`

### Secure Example (PHP)
By using `htmlspecialchars`, the input is neutralized.

```php
<?php
$name = $_GET['name'];
// SECURE: HTML entities are encoded
echo "<h1>Welcome, " . htmlspecialchars($name, ENT_QUOTES, 'UTF-8') . "</h1>";
?>
```

### Vulnerable Example (JavaScript DOM)
```javascript
const urlParams = new URLSearchParams(window.location.search);
const userNote = urlParams.get('note');
// VULNERABLE: innerHTML parses the string as HTML
document.getElementById('display').innerHTML = userNote;
```

### Secure Example (JavaScript DOM)
```javascript
const urlParams = new URLSearchParams(window.location.search);
const userNote = urlParams.get('note');
// SECURE: textContent treats the input strictly as text
document.getElementById('display').textContent = userNote;
```