## Description

SQL Injection (SQLI) is a code injection technique that exploits security vulnerabilities in an application's software. These vulnerabilities occur when user-supplied input is improperly filtered for string literal escape characters embedded in SQL statements or when user input is not strongly typed and thereby unexpectedly executed. SQLI allows an attacker to interfere with the queries that an application makes to its database. An attacker can view data that they are normally unable to retrieve, they can modify or delete this data, cause authentication bypass, execute arbitrary OS commands on the database server, or they can escalate their privileges to administrative level.

SQL Injection is one of the most prevalent web application vulnerabilities, due to the widespread use of SQL databases, coupled with programming practices that fail to adequately sanitize user input.

## Impact

Successful SQL Injection attacks can have devastating consequences, including:

*   **Data Breach:** Unauthorized access to sensitive data, such as user credentials, financial records, and proprietary information.
*   **Data Manipulation:** Modifying or deleting data, leading to data corruption, financial loss, or reputational damage.
*   **Authentication Bypass:** Circumventing authentication mechanisms to gain unauthorized access to application functionality.
*   **Remote Code Execution:** In some cases, attackers can execute arbitrary code on the database server, leading to complete system compromise.
*   **Denial of Service:** Disrupting the availability of the application or database server.

## Remediation

Preventing SQL Injection requires a multi-layered approach:

1.  **Input Validation:** Always validate user input to ensure it conforms to expected formats and lengths. Reject any input that does not meet the validation criteria. This includes whitelist validation rather than blacklist validation.

2.  **Parameterized Queries (Prepared Statements):** The most effective way to prevent SQL Injection is to use parameterized queries (also known as prepared statements). Parameterized queries separate the SQL code from the data, preventing the database from interpreting user-supplied input as part of the SQL command.

    *   **Example (PHP):**

        ```php
        // Vulnerable code
        $username = $_POST['username'];
        $query = "SELECT * FROM users WHERE username = '$username'";
        $result = mysqli_query($conn, $query);

        // Secure code using prepared statements
        $username = $_POST['username'];
        $stmt = $conn->prepare("SELECT * FROM users WHERE username = ?");
        $stmt->bind_param("s", $username); // 's' indicates a string parameter
        $stmt->execute();
        $result = $stmt->get_result();
        ```

    *   **Example (Python):**

        ```python
        # Vulnerable code
        username = request.form['username']
        query = "SELECT * FROM users WHERE username = '%s'" % username
        cursor.execute(query)

        # Secure code using prepared statements
        username = request.form['username']
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        ```

    *   **Example (Java):**

        ```java
        // Vulnerable code
        String username = request.getParameter("username");
        String query = "SELECT * FROM users WHERE username = '" + username + "'";
        Statement statement = connection.createStatement();
        ResultSet resultSet = statement.executeQuery(query);

        // Secure code using prepared statements
        String username = request.getParameter("username");
        String query = "SELECT * FROM users WHERE username = ?";
        PreparedStatement preparedStatement = connection.prepareStatement(query);
        preparedStatement.setString(1, username);
        ResultSet resultSet = preparedStatement.executeQuery();
        ```

3.  **Escaping User-Supplied Data:** If parameterized queries are not feasible, carefully escape user-supplied data before including it in SQL queries. Use the database's built-in escaping functions (e.g., `mysqli_real_escape_string` in PHP, `quote_identifier` in Python's `psycopg2`). However, this approach is less secure than parameterized queries and should be avoided if possible.  Escaping should be the last line of defense, not the first.

4.  **Principle of Least Privilege:** Configure database user accounts with the minimum necessary privileges. Avoid using the `root` or `administrator` account for application database connections.

5.  **Web Application Firewall (WAF):** Deploy a WAF to filter out malicious SQL Injection attempts. A WAF can detect and block common SQL Injection patterns.

6.  **Regular Security Audits:** Conduct regular security audits and penetration testing to identify and address SQL Injection vulnerabilities in your applications.

7.  **Keep Software Up-to-Date:** Regularly update your database management system (DBMS) and application frameworks to patch known vulnerabilities.

## Examples

**Vulnerable Code (PHP):**

```php
<?php
  $id = $_GET['id'];
  $query = "SELECT * FROM products WHERE id = " . $id;
  $result = mysql_query($query); // Vulnerable to SQL injection
?>
```

**Vulnerable Code (Java):**

```java
String productId = request.getParameter("productId");
String query = "SELECT * FROM products WHERE product_id = '" + productId + "'";
Statement statement = connection.createStatement();
ResultSet rs = statement.executeQuery(query);
```

**Secure Code (PHP):**

```php
<?php
  $id = $_GET['id'];
  $stmt = $pdo->prepare("SELECT * FROM products WHERE id = :id");
  $stmt->bindParam(':id', $id, PDO::PARAM_INT);
  $stmt->execute();
  $result = $stmt->fetchAll();
?>
```

**Secure Code (Java):**

```java
String productId = request.getParameter("productId");
String query = "SELECT * FROM products WHERE product_id = ?";
PreparedStatement preparedStatement = connection.prepareStatement(query);
preparedStatement.setString(1, productId);
ResultSet rs = preparedStatement.executeQuery();
```