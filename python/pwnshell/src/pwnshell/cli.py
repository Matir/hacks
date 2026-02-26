import sys
import os
import argparse
from pathlib import Path
from pwn import *
from IPython import embed
from IPython.terminal.prompts import Prompts, Token
from traitlets.config import Config

# Handle tomllib/tomli import
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

class PwnPrompts(Prompts):
    def in_prompt_tokens(self):
        return [
            (Token.Prompt, 'pwn'),
            (Token.Prompt, ' > '),
        ]

def load_config(config_path=None):
    """Search for and load a TOML configuration file."""
    search_paths = []
    
    # 1. From flag
    if config_path:
        search_paths.append(Path(config_path))
    
    # 2. From environment variable
    env_config = os.environ.get('PWNSHELL_CONFIG')
    if env_config:
        search_paths.append(Path(env_config))
    
    # 3. From standard locations
    search_paths.append(Path.home() / ".config" / "pwnshell.toml")
    search_paths.append(Path.home() / ".pwnshell.toml")

    for path in search_paths:
        if path.exists() and path.is_file():
            try:
                with path.open("rb") as f:
                    return tomllib.load(f)
            except Exception as e:
                print(f"Error loading config from {path}: {e}", file=sys.stderr)
                break
    return {}

def main():
    parser = argparse.ArgumentParser(description="A sophisticated shell for pwnage")
    parser.add_argument("-c", "--config", help="Path to the configuration file")
    parser.add_argument("-s", "--script", help="Python script to run before starting the shell")
    args = parser.parse_args()

    # Load configuration
    config_data = load_config(args.config)

    # Configure IPython
    c = Config()
    c.TerminalInteractiveShell.prompts_class = PwnPrompts
    c.TerminalInteractiveShell.highlighting_style = 'monokai'
    c.InteractiveShellEmbed.confirm_exit = False

    # Setup the namespace with pwntools
    namespace = globals().copy()
    namespace.update({
        'config': config_data,
    })

    # Run setup script if provided
    if args.script:
        script_path = Path(args.script)
        if script_path.exists():
            try:
                with script_path.open("r") as f:
                    # Execute in the namespace so variables persist
                    exec(f.read(), namespace)
            except Exception as e:
                print(f"Error executing script {args.script}: {e}", file=sys.stderr)
        else:
            print(f"Error: Script {args.script} not found.", file=sys.stderr)
    
    banner = """
    [pwnshell] A sophisticated shell for pwnage
    pwntools and common utilities are pre-loaded.
    """
    if config_data:
        banner += f"\n    Loaded configuration from: {args.config or os.environ.get('PWNSHELL_CONFIG') or 'default path'}"
    if args.script:
        banner += f"\n    Executed setup script: {args.script}"

    embed(config=c, user_ns=namespace, banner1=banner)
    return 0

if __name__ == "__main__":
    sys.exit(main())
