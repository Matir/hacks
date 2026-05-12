## Description

Cross-Site Scripting (XSS) vulnerabilities occur when an application includes untrusted data in a new web page without proper validation or escaping. XSS allows attackers to inject malicious scripts (usually JavaScript) into web pages viewed by other users. When a user visits a page containing injected XSS code, their browser executes the script, potentially allowing the attacker to:

*   Steal cookies and session tokens, allowing them to impersonate the user.
*   Redirect the user to a malicious website.
*   Deface the website.
*   Install malware on the user's machine.
*   Collect sensitive information such as keystrokes.

XSS vulnerabilities are broadly classified into three types:

*   **Reflected XSS:** The malicious script is part of the request (e.g., in a URL parameter). The server then reflects this script back to the user, who unknowingly executes it.
*   **Stored XSS:** The malicious script is stored on the server (e.g., in a database) and then displayed to other users. This is the most dangerous type of XSS because it does not require the attacker to trick users into clicking a malicious link.
*   **DOM-based XSS:** The vulnerability exists in client-side code (JavaScript). The malicious script is injected into the DOM (Document Object Model) of the page, causing the JavaScript to execute the script. This type of XSS does not require the server to be involved.

## Impact

A successful XSS attack can have severe consequences, including:

*   **Account Compromise:** Attackers can steal user credentials (cookies, session tokens) and hijack user accounts.
*   **Data Theft:** Attackers can steal sensitive information displayed on the page, such as personal data, financial information, or proprietary business data.
*   **Malware Distribution:** Attackers can inject malicious code that installs malware on users' machines.
*   **Website Defacement:** Attackers can modify the content of the website, damaging the website's reputation.
*   **Redirection to Malicious Sites:** Users can be redirected to phishing sites or sites that distribute malware.

## Remediation

Preventing XSS vulnerabilities requires careful attention to input validation, output encoding, and other security best practices.

**General Recommendations:**

*   **Input Validation:** Sanitize and validate all user input on the server-side before storing or using it. This includes checking the data type, length, format, and character set. Reject any input that does not conform to expectations.
*   **Output Encoding/Escaping:** Encode all user-supplied data before displaying it in a web page. The appropriate encoding method depends on the context in which the data is being used (e.g., HTML, URL, JavaScript).
*   **Content Security Policy (CSP):** Implement CSP to restrict the sources from which the browser can load resources, such as scripts and stylesheets. This can help to prevent XSS attacks by limiting the attacker's ability to inject malicious code.
*   **HTTPOnly Cookie Attribute:** Set the `HttpOnly` attribute on cookies to prevent client-side scripts from accessing them. This can help to mitigate the impact of XSS attacks by preventing attackers from stealing session tokens.
*   **Regular Security Audits:** Conduct regular security audits to identify and address potential XSS vulnerabilities.

**Language-Specific Examples:**

*   **PHP:**

    *   Use `htmlspecialchars()` to escape HTML entities:
        ```php
        <?php
        $name = $_GET['name'];
        echo "Hello, " . htmlspecialchars($name, ENT_QUOTES, 'UTF-8') . "!";
        ?>
        ```
    *   Use `filter_var()` with appropriate filters for input validation:
        ```php
        <?php
        $email = filter_var($_POST['email'], FILTER_SANITIZE_EMAIL);
        if (filter_var($email, FILTER_VALIDATE_EMAIL)) {
            // Valid email address
        } else {
            // Invalid email address
        }
        ?>
        ```
*   **JavaScript:**

    *   Use `textContent` instead of `innerHTML` to avoid executing HTML:
        ```javascript
        const element = document.getElementById('myElement');
        element.textContent = userInput; // Safer than element.innerHTML = userInput;
        ```
    *   Use a templating engine with automatic escaping:
        ```javascript
        // Using a library like Handlebars or Mustache
        const template = Handlebars.compile("<div>Hello, {{name}}!</div>");
        const html = template({ name: userInput });
        document.getElementById('myElement').innerHTML = html;
        ```
*   **Python (with Flask):**

    *   Use Jinja2 templating engine, which automatically escapes output by default:
        ```python
        from flask import Flask, render_template, request

        app = Flask(__name__)

        @app.route('/')
        def index():
            name = request.args.get('name')
            return render_template('index.html', name=name)
        ```
        ```html
        <!-- index.html -->
        <div>Hello, {{ name }}!</div>
        ```
    *   If you need to output raw HTML (rare), use `Markup` from `markupsafe`:
         ```python
        from flask import Flask, render_template, request
        from markupsafe import Markup

        app = Flask(__name__)

        @app.route('/')
        def index():
            html_content = Markup("<h1>Hello, <script>alert('XSS')</script></h1>")
            return render_template('index.html', content=html_content)
        ```

## Examples

**Vulnerable Code (PHP - Reflected XSS):**

```php
<?php
  echo "Hello " . $_GET['name'];
?>
```

If a user visits `example.com/index.php?name=<script>alert('XSS')</script>`, the JavaScript code will be executed.

**Secure Code (PHP - with `htmlspecialchars()`):**

```php
<?php
  echo "Hello " . htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8');
?>
```

In this case, the `<script>` tag will be encoded as `&lt;script&gt;`, preventing the JavaScript from being executed.