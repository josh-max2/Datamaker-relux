"""CLI entry point. Forwards to src.extract.

Usage:
    uv run python main.py [path/to/fdd.pdf]

If no path is given, defaults to data/crumbl_yale.pdf (the validation fixture).
Per-PDF outputs land in output/{pdf_stem}/.
"""
from src.extract import main

if __name__ == "__main__":
    main()
