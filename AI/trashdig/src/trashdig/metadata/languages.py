from dataclasses import dataclass, field

import tree_sitter
import tree_sitter_c
import tree_sitter_c_sharp
import tree_sitter_cpp
import tree_sitter_go
import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_php
import tree_sitter_python
import tree_sitter_ruby
import tree_sitter_rust


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
    # Node types that represent a variable/symbol identifier
    identifier_types: set[str] = field(default_factory=lambda: {"identifier"})
    # Node types that represent an argument list in a call
    argument_types: set[str] = field(default_factory=lambda: {"argument_list"})


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
    definition_types={"function_definition", "function_declaration", "arrow_function", "method_definition", "class_definition", "class_declaration"},
    scope_types={"function_definition", "function_declaration", "arrow_function", "method_definition", "class_definition", "class_declaration"},
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

C_METADATA = LanguageMetadata(
    name="c",
    extensions=[".c", ".h"],
    definition_types={"function_definition", "struct_specifier", "enum_specifier"},
    scope_types={"function_definition", "compound_statement"},
    assignment_types={"assignment_expression", "declaration"},
    parameter_types={"parameter_declaration"},
    sinks={
        "system",
        "popen",
        "execl",
        "execle",
        "execlp",
        "execv",
        "execve",
        "execvp",
        "strcpy",
        "strcat",
        "sprintf",
        "gets",
        "scanf",
    },
    method_sinks=set(),
    definition_patterns=[r"\b{name}\s*\("],
    attr_separators={"."},
)

CPP_METADATA = LanguageMetadata(
    name="cpp",
    extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hh"],
    definition_types={
        "function_definition",
        "struct_specifier",
        "class_specifier",
        "enum_specifier",
    },
    scope_types={"function_definition", "compound_statement", "class_specifier", "namespace_definition"},
    assignment_types={"assignment_expression", "declaration"},
    parameter_types={"parameter_declaration"},
    sinks={
        "system",
        "popen",
        "execl",
        "execle",
        "execlp",
        "execv",
        "execve",
        "execvp",
        "strcpy",
        "strcat",
        "sprintf",
        "gets",
        "scanf",
    },
    method_sinks=set(),
    definition_patterns=[r"\b{name}\s*\("],
    attr_separators={".", "->", "::"},
)

JAVA_METADATA = LanguageMetadata(
    name="java",
    extensions=[".java"],
    definition_types={
        "method_declaration",
        "class_declaration",
        "constructor_declaration",
        "interface_declaration",
    },
    scope_types={"method_declaration", "class_declaration", "block"},
    assignment_types={"assignment_expression", "variable_declarator", "local_variable_declaration"},
    parameter_types={"formal_parameter"},
    sinks={
        "exec",
        "ProcessBuilder",
        "execute",
        "executeQuery",
        "executeUpdate",
        "load",
        "loadLibrary",
    },
    method_sinks={"execute", "executeQuery", "executeUpdate", "query"},
    definition_patterns=[r"\b{name}\s*\("],
    attr_separators={"."},
)

RUBY_METADATA = LanguageMetadata(
    name="ruby",
    extensions=[".rb", ".rake", "Rakefile", "Gemfile"],
    definition_types={"method", "class", "module", "singleton_method"},
    scope_types={"method", "class", "module", "do_block", "block"},
    assignment_types={"assignment", "operator_assignment"},
    parameter_types={"method_parameters", "parameters"},
    sinks={"eval", "system", "exec", "spawn", "send", "public_send", "query", "execute"},
    method_sinks={"query", "execute", "send", "public_send"},
    definition_patterns=[r"\bdef\s+{name}\b"],
    attr_separators={"."},
)

RUST_METADATA = LanguageMetadata(
    name="rust",
    extensions=[".rs"],
    definition_types={"function_item", "struct_item", "enum_item", "impl_item", "trait_item"},
    scope_types={"function_item", "block", "impl_item", "mod_item"},
    assignment_types={"let_declaration", "assignment_expression"},
    parameter_types={"parameter"},
    sinks={"new", "spawn", "execute", "query", "eval"},
    method_sinks={"execute", "query", "spawn"},
    definition_patterns=[r"\bfn\s+{name}\b"],
    attr_separators={".", "::"},
    argument_types={"arguments"},
)

PHP_METADATA = LanguageMetadata(
    name="php",
    extensions=[".php", ".phtml", ".php3", ".php4", ".php5", ".phps"],
    definition_types={
        "function_definition",
        "method_declaration",
        "class_declaration",
        "interface_declaration",
    },
    scope_types={"function_definition", "method_declaration", "compound_statement"},
    assignment_types={"assignment_expression"},
    parameter_types={"formal_parameter"},
    sinks={
        "eval",
        "exec",
        "system",
        "shell_exec",
        "passthru",
        "proc_open",
        "popen",
        "query",
        "execute",
        "mysql_query",
        "mysqli_query",
        "mysqli_prepare",
    },
    method_sinks={"query", "execute", "prepare"},
    definition_patterns=[r"\bfunction\s+{name}\b"],
    attr_separators={"->", "::"},
    identifier_types={"variable_name", "name", "identifier"},
    argument_types={"arguments", "argument_list"},
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
    "c": C_METADATA,
    "cpp": CPP_METADATA,
    "c++": CPP_METADATA,
    "java": JAVA_METADATA,
    "ruby": RUBY_METADATA,
    "rb": RUBY_METADATA,
    "rust": RUST_METADATA,
    "rs": RUST_METADATA,
    "php": PHP_METADATA,
}


def get_language_metadata(lang: str) -> LanguageMetadata | None:
    """Returns the metadata for the given language string."""
    return _METADATA_MAP.get(lang.lower())


_LANGUAGE_CACHE: dict[str, tree_sitter.Language] = {}


def get_ts_language(lang: str | LanguageMetadata) -> tree_sitter.Language | None:
    """Gets the tree-sitter language object for the given language string or metadata."""
    # Canonicalize the name using metadata aliases
    lang_name = lang.name if hasattr(lang, "name") else str(lang).lower()
    meta = get_language_metadata(lang_name)
    if not meta:
        return None

    canonical_name = meta.name
    if canonical_name in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[canonical_name]

    # Map of canonical names to language constructor functions
    lang_factories = {
        "python": tree_sitter_python.language,
        "go": tree_sitter_go.language,
        "javascript": tree_sitter_javascript.language,
        "csharp": tree_sitter_c_sharp.language,
        "c": tree_sitter_c.language,
        "cpp": tree_sitter_cpp.language,
        "java": tree_sitter_java.language,
        "ruby": tree_sitter_ruby.language,
        "rust": tree_sitter_rust.language,
        "php": tree_sitter_php.language_php,
    }

    factory = lang_factories.get(canonical_name)
    if factory:
        ts_lang = tree_sitter.Language(factory())
        _LANGUAGE_CACHE[canonical_name] = ts_lang
        return ts_lang

    return None


def make_parser(lang: str | LanguageMetadata) -> tree_sitter.Parser | None:
    """Creates a tree-sitter parser with a cached Language for the given language."""
    ts_lang = get_ts_language(lang)
    if ts_lang is None:
        return None
    return tree_sitter.Parser(ts_lang)
