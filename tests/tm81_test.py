"""
tests/tm81_test.py — Single entry point untuk semua test TM81.

Test didefinisikan di json/tm81_test.json.
Factory _make_tm81_item() membuat AutoTest per entry, dengan run_fn
yang memanggil command class dari commands/tm81/.

Format di tasks.json: "tm81:<name>"
  misal: "tm81:ping", "tm81:get_version", dst.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib
import json

from test_base import TestBase


# Ini dipakai discover_tests() untuk menemukan file ini
TITLE       = "TM81 Test"
TYPE        = "auto"
COMMAND     = "TM81"
DESCRIPTION = "Test suite untuk device TM81 (via IrDA/CH340)"


class TM81Test(TestBase):
    """Placeholder agar discover_tests() bisa menemukan modul ini."""
    TITLE       = "TM81 Test"
    TYPE        = "auto"
    COMMAND     = "TM81"
    DESCRIPTION = "Test suite untuk device TM81 (via IrDA/CH340)"
