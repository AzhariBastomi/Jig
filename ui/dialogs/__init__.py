"""
ui/dialogs/ — package berisi semua dialog Tkinter.

Import seperti biasa:
    from ui.dialogs import CommissioningDialog, FlashSettingsDialog
"""

from .display_settings import DisplaySettingsDialog
from .add_test         import AddTestDialog
from .commissioning    import CommissioningDialog
from .flash_settings   import FlashSettingsDialog
from .ota_settings     import OTASettingsDialog

__all__ = [
    "DisplaySettingsDialog",
    "AddTestDialog",
    "CommissioningDialog",
    "FlashSettingsDialog",
    "OTASettingsDialog",
]
