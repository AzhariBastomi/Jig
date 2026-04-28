from app import DownloadTask
from worker import (
    BluetoothScanTask,
    SendCommandTask
)

TASK_REGISTRY = [BluetoothScanTask, SendCommandTask]

TASK_DEFAULTS = {
}

TASK_DESC = {
}