"""
voltage_test.py - Manual voltage test, satu instance per entry di voltage.json.

Operator cek tegangan pakai multimeter, lalu klik OK/NG.
CLI:
    python voltage_test.py 3v3
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import json
from test_base import TestBase

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_voltage_json() -> dict:
    path = os.path.join(_ROOT, "json", "voltage.json")
    with open(path) as f:
        return json.load(f)


class VoltageTest(TestBase):
    TITLE       = "Voltage"
    TYPE        = "manual"
    COMMAND     = "VOLT"
    DESCRIPTION = ""

    # Di-set oleh factory
    ENTRY: dict = {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    entry_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not entry_name:
        print("Usage: python voltage_test.py <name>  (misal: 3v3, 1v8)")
        sys.exit(1)

    try:
        data = _load_voltage_json()
    except FileNotFoundError:
        print("voltage.json tidak ditemukan di json/"); sys.exit(1)

    entry = next((v for v in data.get("voltages", []) if v.get("name") == entry_name), None)
    if not entry:
        names = [v.get("name") for v in data.get("voltages", [])]
        print(f"Entry {entry_name!r} tidak ditemukan. Tersedia: {names}")
        sys.exit(1)

    print(f"[Voltage {entry.get('label', entry_name)}] -> MANUAL (operator konfirmasi)")
