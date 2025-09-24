#!/usr/bin/env python3
"""
Standalone script to run the Device Coordination Service.

This script can be used to run the coordination service independently
from the command line.
"""

import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bluesky_queueserver_api.coordination.service import main

if __name__ == "__main__":
    main()
