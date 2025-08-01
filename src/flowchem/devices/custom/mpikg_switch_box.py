""" Control module for Eletronic Switch Box develop by MPIKG (Eletronic Lab) """
from __future__ import annotations

from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.components.device_info import DeviceInfo
from flowchem.utils.people import samuel_saraiva

from enum import StrEnum
import aioserial
import asyncio


class InfRequest(StrEnum):
    GET = "get"
    SET = "set"


class VaribleType(StrEnum):
    # --------------------------------------------------<\r>
    # <\n>- help or ?         -> Show this page<\r>
    # <\n>- reset             -> reset the Device (softreset)<\r>
    # <\n><\r>
    # <\n>-------   Port Befehle   ----------------------<\r>
    # <\n>- set a:x           -> set PortA Byte Decimal(x:0-65535)<\r>
    # <\n>- set b:x           -> set PortB Byte Decimal(x:0-65535)<\r>
    # <\n>- set c:x           -> set PortC Byte Decimal(x:0-65535)<\r>
    # <\n>- set d:x           -> set PortD Byte Decimal(x:0-65535)<\r>
    # <\n>- set abcd:a,b,c,d  -> set Ports A,B,C und D<\r>
    # <\n>- get abcd          -> get Ports A,B,C und D<\r>
    # <\n>- get a             -> get PortA Byte Decimal<\r>
    # <\n>- get b             -> get PortB Byte Decimal<\r>
    # <\n>- get c             -> get PortC Byte Decimal<\r>
    # <\n>- get d             -> get PortD Byte Decimal<\r>
    # <\n>- set starta:x      -> set PortA Startwert (x:0-65535)<\r>
    # <\n>- set startb:x      -> set PortB Startwert (x:0-65535)<\r>
    # <\n>- set startc:x      -> set PortC Startwert (x:0-65535)<\r>
    # <\n>- set startd:x      -> set PortD Startwert (x:0-65535)<\r>
    # <\n>- get starta        -> get PortA Startwert Decimal<\r>
    # <\n>- get startb        -> get PortB Startwert Decimal<\r>
    # <\n>- get startc        -> get PortC Startwert Decimal<\r>
    # <\n>- get startd        -> get PortC Startwert Decimal<\r>
    # <\n><\r>
    # <\n>------    ADC/DAC Commands        ----------<\r>
    # <\n>- set dac1:x        -> set Dac1 (x:0-4095)(0-10V)<\r>
    # <\n>- set dac2:x        -> set Dac2 (x:0-4095)(0-10V)<\r>
    # <\n>- get dac1          -> get Dac1 value (0-4095)<\r>
    # <\n>- get dac2          -> get Dac2 value (0-4095)<\r>
    # <\n><\r>
    # <\n>--------------------------------------------<\r>
    # <\n>- get adcx          -> get ADC0..ADC7 value (0-5 Volt)<\r>
    # <\n>- get adc0          -> get ADC0 value (0-5 Volt)<\r>
    # <\n>- get adc1          -> get ADC1 value (0-5 Volt)<\r>
    # <\n>- get adc2          -> get ADC2 value (0-5 Volt)<\r>
    # <\n>- get adc3          -> get ADC3 value (0-5 Volt)<\r>
    # <\n>- get adc4          -> get ADC4 value (0-5 Volt)<\r>
    # <\n>- get adc5          -> get ADC5 value (0-5 Volt)<\r>
    # <\n>- get adc6          -> get ADC6 value (0-5 Volt)<\r>
    # <\n>- get adc7          -> get ADC7 value (0-5 Volt)<\r>
    # <\n><\r>
    # <\n>- get ver           -> Shows programversion<\r>
    # <\n>- test on           -> Hardware test ON<\r>
    # <\n>- test off          -> Hardware test OFF<\r>
    # <\n>----------------------------------------------

    VERSION = "ver"

    # -------   Port Befehle   -------
    # PortX Byte Decimal(x:0-65535)
    A = "a"
    B = "b"
    C = "c"
    D = "d"

    # Startwert (x:0-65535)
    START_A = "starta"
    START_B = "startb"
    START_C = "startc"
    START_D = "startd"

    # ------  ADC/DAC Commands  ------
    VOLTAGE = "adc"
    DAC = "dac"  # (0-4095)(0-10V)


@dataclass
class SwitchBoxCommand:
    """ Class representing a box command and its expected reply """
    channel: int = 0
    request: InfRequest = InfRequest.SET
    variable: VaribleType = VaribleType.VOLTAGE
    value: int = 0

    def compile(self)->str:
        """
        Create actual command byte by prepending box address to command.
        """
        if self.request == InfRequest.SET:
            if self.variable in {VaribleType.VOLTAGE, VaribleType.DAC}:
                command = f"{self.request} {self.variable}{self.channel}:{self.value}".encode("ascii")
            else:
                command = f"{self.request} {self.variable}:{self.value}".encode("ascii")
        else:
            if self.variable in {VaribleType.VOLTAGE, VaribleType.DAC}:
                command = f"{self.request} {self.variable}{self.channel}".encode("ascii")
            else:
                command = f"{self.request} {self.variable}".encode("ascii")