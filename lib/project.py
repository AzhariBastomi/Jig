"""
project.py — Project classification helpers.

"Project" = kumpulan test yang saling eksklusif (tm81 / flash / ota).
"Universal" = test yang bisa ditambahkan ke project mana saja.
"""

_PROJECT_PREFIXES: dict[str, list[str]] = {
    "tm81":  ["tm81:"],
    "flash": ["flash:"],
    "ota":   ["tm81_ota:"],
}
_PROJECT_SINGLES: dict[str, list[str]] = {}


def module_project(module_name: str) -> "str | None":
    """Return project name jika modul project-specific, else None (universal)."""
    for proj, prefixes in _PROJECT_PREFIXES.items():
        if any(module_name.startswith(p) for p in prefixes):
            return proj
    for proj, singles in _PROJECT_SINGLES.items():
        if module_name in singles:
            return proj
    return None


def detect_project(test_names: list) -> "str | None":
    """Deteksi project aktif dari daftar modul yang ada."""
    for name in test_names:
        proj = module_project(name)
        if proj:
            return proj
    return None
