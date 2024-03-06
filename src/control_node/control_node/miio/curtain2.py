import enum
import logging
from typing import Any, Dict

import click

from miio import MiotDevice
from miio.click_common import EnumType, command, format_output

_LOGGER = logging.getLogger(__name__)

MODEL_CURTAIN_GM35XM = 'gerwin.curtain.gm35xm'

_MAPPINGS = {
    MODEL_CURTAIN_GM35XM: {
        "motor_control": {"siid": 2, "piid": 2},
        "current_position": {"siid": 2, "piid": 3},  # Range: [0, 100, 1]
        "target_position": {"siid": 2, "piid": 4},  # Range: [0, 100, 1]
        "motor-reverse": {"siid": 2, "piid": 5},
    },
}


class MotorControl(enum.Enum):
    Pause = 2
    Open = 1
    Close = 0


class CurtainMiot(MiotDevice):
    _mappings = _MAPPINGS

    @command(
        click.argument("target_position", type=int),
        default_output=format_output("Set target position to {target_position}"),
    )
    def set_target_position(self, target_position: int):
        """Set target position."""
        if target_position < 0 or target_position > 100:
            raise ValueError(
                "Value must be between [0, 100] value, was %s" % target_position
            )
        return self.set_property("target_position", target_position)