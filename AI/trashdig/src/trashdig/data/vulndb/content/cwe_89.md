## Description
SQL Injection (SQLi) occurs when an application receives untrusted data and includes it in a database query without proper sanitization or parameterization. Because SQL queries are constructed as strings, an attacker can provide input that includes SQL syntax (e.g., `' OR '1'='1`), effectively altering the query's logic. This allows the attacker to "break out" of the intended data field and execute arbitrary commands against the database.

SQLi vulnerabilities generally fall into three categories:
1.  **In-band SQLi (Classic):** The attacker uses the same communication channel to launch the attack and gather results (e.g., Error-based or Union-based).
2.  **Inferential SQLi (Blind):** The attacker observes the application's response (e.g., generic error pages or time delays) to reconstruct the database structure.
3.  **Out-of-band SQLi:** The attacker triggers the database to make a request to an external server they control (e.g., DNS or HTTP requests).

## Impact
The impact of SQL Injection is often catastrophic, as it grants attackers direct access to the application's most sensitive data. Potential consequences include:
*   **Confidentiality:** Unauthorized viewing of user data, credentials, and intellectual property.
*   **Integrity:** Unauthorized modification or deletion of records, leading to data corruption or financial fraud.
*   **Availability:** Dropping tables or overwhelming the database with complex queries to cause a Denial of Service (DoS).
*   **Authentication Bypass:** Logging in as administrative users without knowing their passwords.
*   **Remote Code Execution (RCE):** In some configurations (e.g., MSSQL `xp_cmdshell`), an attacker can transition from database access to full operating system compromise.

## Remediation
The primary defense against SQL Injection is ensuring that user input is never treated as executable code.

### 1. Use Parameterized Queries (Prepared Statements)
This is the most effective defense. Prepared statements ensure that the database treats the user input strictly as data, not as part of the SQL command.

### 2. Use Object-Relational Mapping (ORM)
Modern ORMs (like Django ORM, Hibernate, or Entity Framework) use parameterized queries by default. However, developers must avoid using "raw" query functions provided by these ORMs with unsanitized input.

### 3. Input Validation
Implement strict allow-lists for user input. If a field expects an integer, ensure it is an integer before passing it to any database logic.

### 4. Principle of Least Privilege
Configure the database user account used by the application to have only the minimum permissions required. For example, the application user should not have `DROP TABLE` or `GRANT` permissions.

## Examples

### Vulnerable Code (Python)
In this example, the developer uses an f-string to build a query, allowing an attacker to manipulate the string structure.
```python
import sqlite3

def get_user_profile(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # VULNERABLE: Direct string interpolation
    query = f"SELECT username, email FROM users WHERE id = '{user_id}'"
    cursor.execute(query)
    return cursor.fetchone()

# Attacker input for user_id: '1' OR '1'='1'
```

### Secure Code (Python)
The secure version uses placeholders (`?`) and passes the input as a separate tuple, which the database driver handles safely.
```python
import sqlite3

def get_user_profile(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # SECURE: Using parameterized queries
    query = "SELECT username, email FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()
```

### Vulnerable Code (Java/JDBC)
```java
String customerName = request.getParameter("customerName");
String query = "SELECT account_balance FROM accounts WHERE customer_name = '" + customerName + "'";
Statement statement = connection.createStatement();
ResultSet rs = statement.executeQuery(query); // VULNERABLE
```

### Secure Code (Java/JDBC)
```java
String customerName = request.getParameter("customerName");
String query = "SELECT account_balance FROM accounts WHERE customer_name = ?";
PreparedStatement pstmt = connection.prepareStatement(query);
pstmt.setString(1, customerName); // SECURE: Data is bound to a parameter
ResultSet rs = pstmt.executeQuery();
```