"""
Entry point for the GPLX Desktop Application.
Usage:
    python app_desktop.py
"""
import sys
import os

# Ensure src is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import GPLXApp

def main():
    app = GPLXApp()
    app.mainloop()

if __name__ == "__main__":
    main()
