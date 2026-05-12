## Description

CWE-22, Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal'), occurs when an application uses external input to construct a pathname that is intended to identify a file or directory located underneath a restricted parent directory, but the application does not properly neutralize special elements present in the input that can modify the pathname to access resources that are outside of the restricted directory.  This allows attackers to access arbitrary files and directories on the server, including application source code, configuration files, and other sensitive information.

## Impact

Successful exploitation of a path traversal vulnerability can lead to:

*   **Information Disclosure:** Reading sensitive files like `/etc/passwd`, application configuration files, or source code.
*   **Remote Code Execution:** In some cases, an attacker might be able to upload malicious files to the server (e.g., through a file upload vulnerability combined with path traversal) and then execute them.
*   **Denial of Service:** Writing to or deleting critical system files.
*   **Privilege Escalation:** If the application runs with elevated privileges, the attacker might be able to access resources that they normally wouldn't have access to.

## Remediation

The primary goal is to prevent attackers from manipulating the path to access files or directories outside the intended scope.  Here are some effective remediation techniques:

1.  **Input Validation (Whitelist):**

    *   **Preferred Method:** If possible, use a whitelist to define the valid inputs. For example, instead of allowing users to specify a file path, provide a list of acceptable file names and let the user select from this list.  This prevents any possibility of path traversal.

2.  **Canonicalization:**

    *   Use functions that resolve the canonical path of both the input and the base directory to ensure they are within the expected boundaries.  Compare the canonical paths to verify the input remains within the allowed directory.

3.  **Path Sanitization (Blacklist - Use with caution):**

    *   If whitelisting is not feasible, use a blacklist to remove or encode dangerous characters like `..`, `.`, `/`, `\`, and `%00` (null byte).
    *   **Important:**  Blacklists are often incomplete and can be bypassed.  Encode the characters instead of removing them.
    *   **Caution:** Be aware of platform differences. Windows uses backslashes (`\`) as path separators, while Unix-like systems use forward slashes (`/`).  Handle both correctly.

4.  **Principle of Least Privilege:**

    *   Ensure the application runs with the minimum privileges necessary to perform its functions. This limits the damage an attacker can do if they successfully exploit a path traversal vulnerability.

5.  **Code Examples (Illustrative):**

    **Python (using `os.path.abspath` and `os.path.join`):**

    ```python
    import os

    def secure_file_access(base_dir, user_input):
        """Safely accesses a file within a specified directory."""

        # Sanitize input
        filename = os.path.basename(user_input) # remove leading path components
        file_path = os.path.join(base_dir, filename)

        # Get the absolute paths
        base_path = os.path.abspath(base_dir)
        resolved_path = os.path.abspath(file_path)

        # Check if the resolved path starts with the base path
        if not resolved_path.startswith(base_path):
            raise Exception("Access Denied: Path traversal attempt detected.")

        try:
            with open(resolved_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return "File not found."

    # Vulnerable example:
    # base_dir = "/var/www/data/"
    # user_input = "../../../etc/passwd"
    # file_content = insecure_file_access(base_dir, user_input) # access /etc/passwd

    # Secure example:
    base_dir = "/var/www/data/"
    user_input = "safe_file.txt"
    file_content = secure_file_access(base_dir, user_input) # access /var/www/data/safe_file.txt
    print(file_content)
    ```

    **PHP (using `realpath` and `strpos`):**

    ```php
    <?php

    function secure_file_access($base_dir, $user_input) {
        $path = realpath($base_dir . '/' . $user_input);

        if (strpos($path, realpath($base_dir)) !== 0) {
            die("Path traversal detected!");
        }

        if (file_exists($path)) {
            return file_get_contents($path);
        } else {
            return "File not found.";
        }
    }

    // Vulnerable Example
    // $base_dir = "/var/www/data";
    // $user_input = "../../../etc/passwd"; // Traversal attempt
    // echo secure_file_access($base_dir, $user_input);

    // Secure Example
    $base_dir = "/var/www/data";
    $user_input = "safe_file.txt"; // Traversal attempt
    echo secure_file_access($base_dir, $user_input);

    ?>
    ```

    **Java (using `Paths.get` and `startsWith`):**

    ```java
    import java.io.IOException;
    import java.nio.file.Files;
    import java.nio.file.Path;
    import java.nio.file.Paths;

    public class PathTraversalExample {

        public static String secureFileAccess(String baseDir, String userInput) throws IOException {
            Path basePath = Paths.get(baseDir).toAbsolutePath().normalize();
            Path filePath = Paths.get(baseDir, userInput).toAbsolutePath().normalize();

            if (!filePath.startsWith(basePath)) {
                throw new IOException("Path traversal detected!");
            }

            if (Files.exists(filePath)) {
                return new String(Files.readAllBytes(filePath));
            } else {
                return "File not found.";
            }
        }

        public static void main(String[] args) {
            try {
                // Vulnerable example
                // String baseDir = "/var/www/data";
                // String userInput = "../../../etc/passwd";
                // String fileContent = secureFileAccess(baseDir, userInput);
                // System.out.println(fileContent);

                // Secure Example
                String baseDir = "/var/www/data";
                String userInput = "safe_file.txt";
                String fileContent = secureFileAccess(baseDir, userInput);
                System.out.println(fileContent);
            } catch (IOException e) {
                System.err.println("Error: " + e.getMessage());
            }
        }
    }
    ```

## Examples

**Vulnerable Code (PHP):**

```php
<?php
$file = $_GET['file'];
include($file); // Vulnerable to path traversal
?>
```

In this example, the `file` parameter from the GET request is directly used in the `include()` function. An attacker could provide a malicious value like `../../../../etc/passwd` to read sensitive system files.

**Secure Code (PHP):**

```php
<?php
$allowed_files = array("home", "about", "contact");
$file = $_GET['file'];

if (in_array($file, $allowed_files)) {
    include("pages/" . $file . ".php");
} else {
    echo "Invalid file.";
}
?>
```

This code is more secure because it uses a whitelist (`$allowed_files`) to ensure that only predefined files can be included. This eliminates the risk of path traversal. It's important to construct the full path after validation to ensure that manipulations of valid file names (e.g., `home/.`) cannot bypass the check.