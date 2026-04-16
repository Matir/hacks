from dataclasses import dataclass, field
from typing import Any


@dataclass
class LanguageMetadata:
    """Metadata about a programming language for AST analysis."""
    
    name: str
    extensions: list[str]
    # Node types that define a function, method, or class
    definition_types: set[str] = field(default_factory=set)
    # Node types that define a scope
    scope_types: set[str] = field(default_factory=set)
    # Node types for variable assignments
    assignment_types: set[str] = field(default_factory=set)
    # Node types for formal parameters
    parameter_types: set[str] = field(default_factory=set)
    # Dangerous sinks (functions/methods)
    sinks: set[str] = field(default_factory=set)
    # Sinks that are typically methods on objects
    method_sinks: set[str] = field(default_factory=set)
    # Symbols to skip during taint tracing (e.g. self, cls)
    skip_symbols: set[str] = field(default_factory=set)
    # Regex patterns to find function/method definitions (use {name} as placeholder)
    definition_patterns: list[str] = field(default_factory=list)
    # Attribute separators (e.g. '.', '::', '->')
    attr_separators: set[str] = field(default_factory=set)


PYTHON_METADATA = LanguageMetadata(
    name="python",
    extensions=[".py"],
    definition_types={"function_definition", "method_definition", "class_definition"},
    scope_types={"function_definition", "method_definition", "class_definition"},
    assignment_types={"assignment"},
    parameter_types={"identifier", "typed_parameter", "parameter_declaration", "default_parameter", "list_splat_pattern", "dictionary_splat_pattern"},
    sinks={
        "executemany", "executescript", "raw", "RawSQL",
        "system", "popen", "run", "call", "check_call", "check_output", "Popen",
        "eval", "exec", "compile",
        "render_template_string", "from_string",
        "loads", "load",
        "write",
    },
    method_sinks={"execute", "query", "write"},
    skip_symbols={"self", "cls"},
    definition_patterns=[r"\bdef {name}\b", r"\basync def {name}\b"],
    attr_separators={"."},
)

JAVASCRIPT_METADATA = LanguageMetadata(
    name="javascript",
    extensions=[".js", ".jsx", ".ts", ".tsx"],
    definition_types={"function_definition", "function_declaration", "arrow_function", "method_definition", "class_definition"},
    scope_types={"function_definition", "function_declaration", "arrow_function", "method_definition", "class_definition"},
    assignment_types={"assignment", "variable_declaration", "lexical_declaration"},
    parameter_types={"identifier", "formal_parameter"},
    sinks={
        "eval", "exec", "execSync", "execFile", "spawnSync",
        "innerHTML", "outerHTML", "write", "query", "execute",
        "dangerouslySetInnerHTML",
    },
    method_sinks={"query", "execute", "write"},
    definition_patterns=[r"\bfunction {name}\b", r"\b{name}\s*=\s*(?:async\s+)?function", r"\b{name}\s*:\s*function"],
    attr_separators={"."},
)

GO_METADATA = LanguageMetadata(
    name="go",
    extensions=[".go"],
    definition_types={"function_declaration", "method_declaration", "type_declaration", "struct_type"},
    scope_types={"function_declaration", "method_declaration"},
    assignment_types={"assignment_statement", "short_variable_declaration"},
    parameter_types={"parameter_declaration"},
    sinks={"Exec", "Command", "Query", "Execute"},
    method_sinks={"Query", "Exec", "Execute"},
    definition_patterns=[r"\bfunc\s+(?:\([^)]+\)\s+)?{name}\b"],
    attr_separators={"."},
)

CSHARP_METADATA = LanguageMetadata(
    name="csharp",
    extensions=[".cs"],
    definition_types={"method_declaration", "local_function_statement", "class_declaration"},
    scope_types={"method_declaration", "class_declaration", "local_function_statement"},
    assignment_types={"assignment_expression", "variable_declaration"},
    parameter_types={"parameter"},
    sinks={"Execute", "ExecuteNonQuery", "ExecuteReader", "ExecuteScalar", "Start"},
    method_sinks={"Execute", "ExecuteNonQuery", "ExecuteReader", "ExecuteScalar"},
    definition_patterns=[r"\b{name}\s*\("],
    attr_separators={".", "::"},
)

_METADATA_MAP = {
    "python": PYTHON_METADATA,
    "py": PYTHON_METADATA,
    "javascript": JAVASCRIPT_METADATA,
    "typescript": JAVASCRIPT_METADATA,
    "js": JAVASCRIPT_METADATA,
    "ts": JAVASCRIPT_METADATA,
    "go": GO_METADATA,
    "csharp": CSHARP_METADATA,
    "cs": CSHARP_METADATA,
}


def get_language_metadata(lang: str) -> LanguageMetadata | None:
    """Returns the metadata for the given language string."""
    return _METADATA_MAP.get(lang.lower())
