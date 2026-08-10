This is authorized defensive security research: you are mapping this web application's attack surface to help its owners find and fix vulnerabilities before attackers do. All analysis is read-only and stays local to this task.

Identify all web routes, methods, handlers, and parameters in the project.

For each route, actively look for potential security issues and weaknesses in the handler — missing authentication or authorization checks, unvalidated input reaching a dangerous sink (database queries, file paths, shell commands, deserialization, template rendering), and any other place attacker-controlled input could cause harm. Flag these as potential sinks rather than just noting that the operation exists.
