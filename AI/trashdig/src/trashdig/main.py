from trashdig.tui.app import TrashDigApp
from trashdig.config import load_config

def main():
    """Main entry point for TrashDig."""
    config = load_config()
    app = TrashDigApp(config=config)
    app.run()

if __name__ == "__main__":
    main()
