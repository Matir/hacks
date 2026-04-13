import subprocess
import os
import json
from typing import List, Optional

def ripgrep_search(pattern: str, path: str = ".", extra_args: Optional[List[str]] = None) -> str:
    """Performs a fast textual search across the codebase using ripgrep.

    Args:
        pattern: The regex pattern to search for.
        path: The directory or file to search in.
        extra_args: Additional arguments to pass to rg (e.g., ["-i", "-A", "2"]).

    Returns:
        The standard output of the ripgrep command.
    """
    cmd = ["rg", "--column", "--line-number", "--no-heading", "--color", "never", pattern, path]
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout if result.stdout else result.stderr
    except FileNotFoundError:
        return "Error: ripgrep (rg) not found in PATH."

def semgrep_scan(path: str = ".", config: str = "p/security-audit") -> str:
    """Scans the codebase for security patterns using semgrep.

    Args:
        path: The directory or file to scan.
        config: The semgrep configuration/rules to use (e.g., "p/security-audit", "p/python").

    Returns:
        The JSON output of the semgrep scan as a string.
    """
    cmd = ["semgrep", "--json", "--config", config, path]
    
    try:
        # Run semgrep with a timeout to avoid hanging
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: semgrep scan timed out."
    except FileNotFoundError:
        return "Error: semgrep not found in PATH."

def _get_ts_language(language: str):
    """Helper to get tree-sitter language objects."""
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_go
    import tree_sitter_c_sharp
    
    languages = {
        "python": tree_sitter_python.language(),
        "javascript": tree_sitter_javascript.language(),
        "go": tree_sitter_go.language(),
        "csharp": tree_sitter_c_sharp.language(),
    }
    return languages.get(language)

def get_ast_summary(file_path: str, language: str = "python") -> str:
    """Generates a simplified AST summary of a file using tree-sitter.

    Args:
        file_path: Path to the file to analyze.
        language: Programming language of the file (python, javascript, go, csharp).

    Returns:
        A text representation of the top-level AST nodes (functions, classes, etc.).
    """
    import tree_sitter
    ts_lang = _get_ts_language(language)
    
    if not ts_lang:
        return f"Error: Language '{language}' not supported for AST analysis."

    try:
        with open(file_path, "rb") as f:
            content = f.read()
            
        parser = tree_sitter.Parser()
        parser.set_language(ts_lang)
        tree = parser.parse(content)
        
        summary = []
        root_node = tree.root_node
        
        for node in root_node.children:
            if node.type in ("function_definition", "class_definition", "method_definition"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode('utf-8') if name_node else "anonymous"
                summary.append(f"{node.type.replace('_', ' ').capitalize()}: {name}")
                
        return "\n".join(summary) if summary else "No top-level definitions found."
        
    except Exception as e:
        return f"Error analyzing AST: {str(e)}"

def get_symbol_definition(symbol_name: str, path: str = ".") -> str:
    """Finds the definition of a function or class across the project.

    Args:
        symbol_name: The name of the function or class to find.
        path: The directory to search in.

    Returns:
        The file path and a snippet of the definition if found.
    """
    patterns = [f"def {symbol_name}", f"class {symbol_name}", f"async def {symbol_name}"]
    results = []
    
    for pattern in patterns:
        res = ripgrep_search(f"\\b{pattern}\\b", path, extra_args=["-C", "5"])
        if res and "Error" not in res:
            results.append(res)
            
    return "\n---\n".join(results) if results else f"Definition for '{symbol_name}' not found."

def find_references(symbol_name: str, path: str = ".") -> str:
    """Finds all references (call sites, usages) of a symbol in the project.

    Args:
        symbol_name: The name of the symbol to find.
        path: The directory to search in.

    Returns:
        A list of occurrences.
    """
    # Use ripgrep to find all usages, but exclude definitions
    extra_args = ["--line-number", "--column", "-v", f"def {symbol_name}|class {symbol_name}"]
    return ripgrep_search(f"\\b{symbol_name}\\b", path, extra_args=extra_args)

def get_scope_info(file_path: str, line_number: int, language: str = "python") -> str:
    """Identifies the variables and parameters available at a specific line.

    Args:
        file_path: Path to the file.
        line_number: The line number to analyze.
        language: Programming language.

    Returns:
        A description of the local scope.
    """
    import tree_sitter
    ts_lang = _get_ts_language(language)
    if not ts_lang:
        return f"Error: Language '{language}' not supported."

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        parser = tree_sitter.Parser()
        parser.set_language(ts_lang)
        tree = parser.parse(content)
        
        # Simple implementation: Find the parent function/method and extract parameters
        # In a real implementation, we'd walk up and find assignments too.
        # Tree-sitter line numbers are 0-indexed.
        target_line = line_number - 1
        
        def find_enclosing_function(node):
            if node.type in ("function_definition", "method_definition"):
                if node.start_point[0] <= target_line <= node.end_point[0]:
                    return node
            for child in node.children:
                res = find_enclosing_function(child)
                if res:
                    return res
            return None

        func_node = find_enclosing_function(tree.root_node)
        if not func_node:
            return "Global scope or no enclosing function found."

        name_node = func_node.child_by_field_name("name")
        func_name = name_node.text.decode('utf-8') if name_node else "anonymous"
        
        params_node = func_node.child_by_field_name("parameters")
        params = []
        if params_node:
            # Simple parameter extraction
            for p in params_node.children:
                if p.type in ("identifier", "typed_parameter", "parameter_declaration"):
                    params.append(p.text.decode('utf-8'))

        return f"Function: {func_name}\nParameters: {', '.join(params) if params else 'None'}"

    except Exception as e:
        return f"Error analyzing scope: {str(e)}"

def trace_variable_semantic(variable_name: str, file_path: str, language: str = "python") -> str:
    """Traces a variable through a file using AST awareness.

    Args:
        variable_name: Name of the variable.
        file_path: Path to the file.
        language: Programming language.

    Returns:
        A list of categorized usages.
    """
    import tree_sitter
    ts_lang = _get_ts_language(language)
    if not ts_lang:
        return f"Error: Language '{language}' not supported."

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        parser = tree_sitter.Parser()
        parser.set_language(ts_lang)
        tree = parser.parse(content)
        
        usages = []
        def walk(node):
            if node.type == "identifier" and node.text.decode('utf-8') == variable_name:
                parent = node.parent
                category = "USAGE"
                if parent.type in ("assignment", "variable_declaration"):
                    category = "ASSIGNMENT/DEFINITION"
                elif parent.type == "argument_list":
                    category = "SINK ARGUMENT"
                
                usages.append(f"Line {node.start_point[0] + 1}: {category}")
            
            for child in node.children:
                walk(child)
        
        walk(tree.root_node)
        return "\n".join(usages) if usages else f"Variable '{variable_name}' not found."

    except Exception as e:
        return f"Error tracing variable: {str(e)}"

def trace_variable(variable_name: str, file_path: str) -> str:
    """Finds all occurrences of a variable in a file to trace its flow."""
    return ripgrep_search(f"\\b{variable_name}\\b", file_path, extra_args=["--line-number", "--column"])

def bash_tool(command: str, timeout: int = 30) -> str:
    """Executes a bash command or script and returns the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if not output:
            output.append(f"Command exited with code {result.returncode} (No output)")
        else:
            output.append(f"Exit Code: {result.returncode}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Error executing command: {str(e)}"

async def web_fetch(url: str) -> str:
    """Fetches the content of a web page and returns its text.
    Use this to read specific articles, documentation, or CVE details.

    Args:
        url: The URL of the web page to fetch.

    Returns:
        The text content of the page (cleaned of HTML tags).
    """
    import aiohttp
    from bs4 import BeautifulSoup
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return f"Error: Failed to fetch page, status code {response.status}"
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text and clean up whitespace
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)
                
                # Truncate to avoid context overflow
                return text[:10000]
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

def query_cwe_database(query: str) -> str:
    """Queries the built-in CWE knowledge base for descriptions and examples."""
    try:
        data_path = os.path.join(os.path.dirname(__file__), "data", "cwe_db.json")
        with open(data_path, "r", encoding="utf-8") as f:
            cwe_data = json.load(f)
        results = []
        q = query.lower()
        for item in cwe_data:
            if (q in item["cwe_id"].lower() or q in item["title"].lower() or q in item["description"].lower()):
                results.append(f"### {item['cwe_id']}: {item['title']}\n{item['description']}\n")
                if "examples" in item:
                    for ex in item["examples"]:
                        results.append(f"**Vulnerable Example ({ex['language']}):**\n```\n{ex['vulnerable_code']}\n```\n")
        return "\n".join(results) if results else f"No results found for query: {query}"
    except Exception as e:
        return f"Error querying CWE database: {str(e)}"
