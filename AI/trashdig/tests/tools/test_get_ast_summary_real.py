import os
from unittest.mock import MagicMock, patch

import pytest

from trashdig.config import Config
from trashdig.tools.get_ast_summary import get_ast_summary


@pytest.fixture(autouse=True)
def mock_workspace(tmp_path):
    c = MagicMock(spec=Config)
    c.workspace_root = str(tmp_path)
    c.resolve_workspace_path.side_effect = os.path.abspath

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

def test_get_ast_summary_c_real(tmp_path):
    code = """
void hello(char *name) {
    printf("Hello %s", name);
}

struct User {
    char *name;
};
"""
    f = tmp_path / "sample.c"
    f.write_text(code)

    result = get_ast_summary(str(f), "c")

    assert "Function definition: hello" in result
    assert "Struct specifier: User" in result

def test_get_ast_summary_cpp_real(tmp_path):
    code = """
class Greeter {
public:
    void greet(std::string name) {
        std::cout << "Hello " << name << std::endl;
    }
};
"""
    f = tmp_path / "sample.cpp"
    f.write_text(code)

    result = get_ast_summary(str(f), "cpp")

    assert "Class specifier: Greeter" in result
    assert "Function definition: greet" in result

def test_get_ast_summary_java_real(tmp_path):
    code = """
public class Greeter {
    public void greet(String name) {
        System.out.println("Hello " + name);
    }
}
"""
    f = tmp_path / "sample.java"
    f.write_text(code)

    result = get_ast_summary(str(f), "java")

    assert "Class declaration: Greeter" in result
    assert "Method declaration: greet" in result

def test_get_ast_summary_ruby_real(tmp_path):
    code = """
class Greeter
  def greet(name)
    puts "Hello #{name}"
  end
end
"""
    f = tmp_path / "sample.rb"
    f.write_text(code)

    result = get_ast_summary(str(f), "ruby")

    assert "Class: Greeter" in result
    assert "Method: greet" in result

def test_get_ast_summary_rust_real(tmp_path):
    code = """
fn greet(name: &str) {
    println!("Hello {}", name);
}

struct User {
    name: String
}
"""
    f = tmp_path / "sample.rs"
    f.write_text(code)

    result = get_ast_summary(str(f), "rust")

    assert "Function item: greet" in result
    assert "Struct item: User" in result

def test_get_ast_summary_php_real(tmp_path):
    code = """
<?php
function greet($name) {
    echo "Hello $name";
}

class Greeter {
    public function hello($name) {
        echo "Hi $name";
    }
}
?>
"""
    f = tmp_path / "sample.php"
    f.write_text(code)

    result = get_ast_summary(str(f), "php")

    assert "Function definition: greet" in result
    assert "Method declaration: hello" in result
    assert "Class declaration: Greeter" in result

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
