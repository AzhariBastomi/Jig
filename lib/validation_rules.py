"""
lib/validation_rules.py — Strategy objects untuk validasi field sebelum test dijalankan.

Setiap 'rule' di tm81_test.json (mis. {"device_id": 1}, {"dev_addr": "nonzero_hex"})
diterjemahkan jadi objek ValidationRule lewat build_rule(). test_loader.py cukup
panggil rule.check(value) — tidak perlu tahu jenis rule-nya sama sekali.

Menambah jenis rule baru = menambah 1 class baru + satu baris di build_rule(),
tanpa mengubah loop validasi di test_loader.py (Open/Closed Principle).
"""


class ValidationRule:
    """Interface rule validasi. Semua rule konkret meng-override kedua method ini."""

    def check(self, value: str) -> bool:
        raise NotImplementedError

    def default_message(self, param: str) -> str:
        raise NotImplementedError


class MinLengthRule(ValidationRule):
    """Rule numerik di JSON (mis. 16) -> panjang string minimal segitu."""

    def __init__(self, n: int):
        self.n = n

    def check(self, value: str) -> bool:
        return len(value) >= self.n

    def default_message(self, param: str) -> str:
        return f"{param} belum diisi (butuh {self.n} karakter). Buka Commissioning Settings."


class NonzeroHexRule(ValidationRule):
    """Rule string "nonzero_hex" di JSON -> nilai hex tidak boleh 0."""

    def check(self, value: str) -> bool:
        try:
            return value != "" and int(value, 16) != 0
        except ValueError:
            return False

    def default_message(self, param: str) -> str:
        return f"{param} tidak boleh 0. Buka Commissioning Settings."


# Pesan custom per-parameter, override default_message() rule di atas.
# Tambah field baru yang butuh pesan khusus cukup nambah satu baris di sini —
# tidak perlu nambah cabang if di dalam logika validasi.
CUSTOM_MESSAGES = {
    "device_id": "device_id kosong — isi field 'Device ID / Serial No.' di UI",
}


def build_rule(raw) -> ValidationRule:
    """Factory: ubah nilai rule mentah dari JSON jadi objek ValidationRule."""
    if isinstance(raw, int):
        return MinLengthRule(raw)
    if raw == "nonzero_hex":
        return NonzeroHexRule()
    raise ValueError(f"Jenis validasi tidak dikenal: {raw!r}")


def validation_message(param: str, rule: ValidationRule) -> str:
    """Pesan NG yang ditampilkan ke operator — custom kalau ada, default kalau tidak."""
    return CUSTOM_MESSAGES.get(param, rule.default_message(param))
