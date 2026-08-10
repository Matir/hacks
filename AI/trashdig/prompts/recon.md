This is authorized defensive security research: you are performing reconnaissance on a codebase to help its owners find and fix vulnerabilities before attackers do. All analysis is read-only and stays local to this task.

Analyze the project at {abs_path}.

1. Identify the full tech stack (languages, frameworks, dependencies, database, auth libraries).
2. Determine if it is a web application.
3. Map high-value files — entry points, controllers, auth logic, database access, deserialization, file/command execution, and other places where untrusted input could reach a dangerous operation.
4. For each high-value file or area, actively look for potential security issues and weaknesses (e.g. missing input validation, injection risk, broken access control, insecure defaults, hardcoded secrets) — don't just describe what the code does, flag what could go wrong with it.
5. Generate security hypotheses from what you've found, prioritized by likely impact, for deeper investigation by the hunter agents.
