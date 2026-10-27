#!/usr/bin/env python3
"""Rebuild the offline guide using the Python standard library."""
import sys
sys.dont_write_bytecode = True
from render_guide import main

if __name__ == '__main__':
    main()
