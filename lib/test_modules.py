"""
test_modules.py - Test item definitions.
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class TestResult(Enum):
    PENDING  = auto()
    RUNNING  = auto()
    OK       = auto()
    NG       = auto()


class TestType(Enum):
    PROGRESS = "progress"
    MANUAL   = "manual"
    AUTO     = "auto"


@dataclass
class TestItem:
    title:       str
    command:     str
    description: str = ""
    run_fn:      object = field(default=None)          # callable() -> "OK"|"NG", opsional
    no_retry:    bool = field(default=False)           # True = skip outer retry
    test_type:   TestType = field(default=TestType.AUTO, init=False)
    result:      TestResult = field(default=TestResult.PENDING, init=False)
    last_error:  str = field(default="", init=False)

    def reset(self):
        self.result     = TestResult.PENDING
        self.last_error = ""

    def is_done(self):
        return self.result in (TestResult.OK, TestResult.NG)


@dataclass
class ProgressBarTest(TestItem):
    steps:   int = 5
    step_ms: int = 300

    def __post_init__(self):
        self.test_type = TestType.PROGRESS


@dataclass
class ManualTest(TestItem):
    def __post_init__(self):
        self.test_type = TestType.MANUAL


@dataclass
class AutoTest(TestItem):
    def __post_init__(self):
        self.test_type = TestType.AUTO


def build_default_tests():
    return [
        ProgressBarTest(title="LED Test", command="TEST_LED",
                        description="Cycles all LEDs and reads back confirmation",
                        steps=8, step_ms=250),
        ManualTest(title="Button Test", command="TEST_BTN",
                   description="Press the physical button and confirm with OK/NG"),
        AutoTest(title="Voltage Test", command="TEST_VOLT",
                 description="Reads supply voltage from ADC"),
        ProgressBarTest(title="Memory Test", command="TEST_MEM",
                        description="Write/read cycle on EEPROM",
                        steps=10, step_ms=200),
        AutoTest(title="Communication Test", command="TEST_COMM",
                 description="Loopback ping to device UART"),
    ]
