import enum
import logging
from typing import Any, Dict

import click

from miio import MiotDevice
from miio.click_common import EnumType, command, format_output

_LOGGER = logging.getLogger(__name__)

# Model: ZNCLDJ21LM (also known as "Xiaomiyoupin Curtain Controller (Wi-Fi)"
MODEL_CURTAIN_ZSDJ35 = "090615.curtain.zsdj35"

_MAPPINGS = {
    MODEL_CURTAIN_ZSDJ35: {
        # # Source https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:curtain:0000A00C:lumi-mcn005:1
        # -hagl05:1 Curtain
        "motor_control": {
            "siid": 2,
            "piid": 2,
        },  # 0 - Pause, 1 - Open, 2 - Close
        "mode": {"siid": 2, "piid": 5},
        "status": {"siid": 2, "piid": 3},
        "current_position": {"siid": 2, "piid": 6},  # Range: [0, 100, 1]
        "target_position": {"siid": 2, "piid": 7},  # Range: [0, 100, 1]
        # curtain_cfg
        "is_manual_enabled": {"siid": 4, "piid": 1},  #
        "polarity": {"siid": 4, "piid": 2},
        "is_position_limited": {"siid": 4, "piid": 3},
        "night_tip_light": {"siid": 4, "piid": 4},
        "run_time": {"siid": 4, "piid": 5},  # Range: [0, 255, 1]
        # motor_controller
        "adjust_value": {"siid": 5, "piid": 1},  # Range: [-100, 100, 1]
    }
}


class MotorControl(enum.Enum):
    Pause = 0
    Open = 1
    Close = 2


class Status(enum.Enum):
    Stopped = 0
    Opening = 1
    Closing = 2


class Polarity(enum.Enum):
    Positive = 0
    Reverse = 1


class CurtainMiot(MiotDevice):
    """Main class representing the lumi.curtain.hagl05 curtain."""


    _mappings = _MAPPINGS

    @command(
        default_output=format_output(
            "",
            "Device status: {result.status}\n"
            "Manual enabled: {result.is_manual_enabled}\n"
            "Motor polarity: {result.polarity}\n"
            "Position limit: {result.is_position_limited}\n"
            "Enabled night tip light: {result.night_tip_light}\n"
            "Run time: {result.run_time}\n"
            "Current position: {result.current_position}\n"
            "Target position: {result.target_position}\n"
            "Adjust value: {result.adjust_value}\n",
        )
    )
    @command(
        click.argument("motor_control", type=EnumType(MotorControl)),
        default_output=format_output("Set motor control to {motor_control}"),
    )
    def set_motor_control(self, motor_control: MotorControl):
        """Set motor control."""
        return self.set_property("motor_control", motor_control.value)

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

    @command(
        click.argument("manual_enabled", type=bool),
        default_output=format_output("Set manual control {manual_enabled}"),
    )
    def set_manual_enabled(self, manual_enabled: bool):
        """Set manual control of curtain."""
        return self.set_property("is_manual_enabled", manual_enabled)

    @command(
        click.argument("polarity", type=EnumType(Polarity)),
        default_output=format_output("Set polarity to {polarity}"),
    )
    def set_polarity(self, polarity: Polarity):
        """Set polarity of the motor."""
        return self.set_property("polarity", polarity.value)

    @command(
        click.argument("pos_limit", type=bool),
        default_output=format_output("Set position limit to {pos_limit}"),
    )
    def set_position_limit(self, pos_limit: bool):
        """Set position limit parameter."""
        return self.set_property("is_position_limited", pos_limit)

    @command(
        click.argument("night_tip_light", type=bool),
        default_output=format_output("Setting night tip light {night_tip_light"),
    )
    def set_night_tip_light(self, night_tip_light: bool):
        """Set night tip light."""
        return self.set_property("night_tip_light", night_tip_light)

    @command(
        click.argument("adjust_value", type=int),
        default_output=format_output("Set adjust value to {adjust_value}"),
    )
    def set_adjust_value(self, adjust_value: int):
        """Adjust to preferred position."""
        if adjust_value < -100 or adjust_value > 100:
            raise ValueError(
                "Value must be between [-100, 100] value, was %s" % adjust_value
            )
        return self.set_property("adjust_value", adjust_value)
