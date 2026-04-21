import os
import pytest
from trashdig.tools.get_ast_summary import get_ast_summary
from trashdig.config import Config
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_workspace(tmp_path):
    c = MagicMock(spec=Config)
    c.workspace_root = str(tmp_path)
    c.resolve_workspace_path.side_effect = lambda x: os.path.abspath(x)
    
    with patch("trashdig.config.get_config", return_value=c), \
         patch("trashdig.tools.get_ast_summary._config_module.get_config", return_value=c):
        yield c

def test_get_ast_summary_python_real(tmp_path):
    code = """
def hello(name: str):
    print(f"Hello {name}")

class Greeter:
    def __init__(self, greeting="Hi"):
        self.greeting = greeting
    
    def greet(self, name):
        print(f"{self.greeting} {name}")
"""
    f = tmp_path / "sample.py"
    f.write_text(code)
    
    result = get_ast_summary(str(f), "python")
    
    assert "Function definition: hello" in result
    assert "Class definition: Greeter" in result
    assert "Function definition: __init__" in result
    assert "Function definition: greet" in result

def test_get_ast_summary_js_real(tmp_path):
    code = """
function add(a, b) {
    return a + b;
}

const multiply = (a, b) => a * b;

class Calculator {
    subtract(a, b) {
        return a - b;
    }
}
"""
    f = tmp_path / "sample.js"
    f.write_text(code)
    
    result = get_ast_summary(str(f), "javascript")
    
    # JavaScript uses "Function declaration" for 'function add'
    assert "Function declaration: add" in result
    assert "Arrow function: multiply" in result
    assert "Class declaration: Calculator" in result
    # Method definition for class methods
    assert "Method definition: subtract" in result

def test_get_ast_summary_go_real(tmp_path):
    code = """
package main

import "fmt"

func main() {
    fmt.Println("Hello")
}

func (c *Calc) Add(a, b int) int {
    return a + b
}

type User struct {
    Name string
}
"""
    f = tmp_path / "sample.go"
    f.write_text(code)
    
    result = get_ast_summary(str(f), "go")
    
    # Go uses "Function declaration"
    assert "Function declaration: main" in result
    assert "Method declaration: Add" in result

def test_get_ast_summary_csharp_real(tmp_path):
    code = """
using System;

namespace Test {
    public class Program {
        public static void Main(string[] args) {
            Console.WriteLine("Hello");
        }
    }
}
"""
    f = tmp_path / "sample.cs"
    f.write_text(code)
    
    result = get_ast_summary(str(f), "csharp")
    
    # C# uses "Class declaration"
    assert "Class declaration: Program" in result
    assert "Method declaration: Main" in result

def test_get_ast_summary_unsupported_lang():
    result = get_ast_summary("test.py", "unsupported")
    assert "not supported" in result

def test_get_ast_summary_no_definitions(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("# Just a comment\nx = 1")
    
    result = get_ast_summary(str(f), "python")
    assert result == "No top-level definitions found."

def test_get_ast_summary_error():
    # Test with a file that doesn't exist
    res = get_ast_summary("nonexistent.py", "python")
    assert "Error analyzing AST" in res
