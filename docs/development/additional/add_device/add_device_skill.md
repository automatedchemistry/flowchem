# add-device

Invocation: `/add-device [manufacturer] [model] [component-type...]`

Scaffold and implement a new device integration for the flowchem package. Creates the required file structure, then uses device documentation to implement the hardware communication layer. Request documentation from the user — do not leave the communication layer as stubs.

---

## Step 1 — Collect required information

Parse slash-command arguments:
- Arg 1: manufacturer name
- Arg 2: device model name
- Arg 3+: component type tokens (optional)

If any required information is missing, use `AskUserQuestion` to collect everything in **one pass**:

1. **Manufacturer name** — company that makes the hardware (e.g. "Hamilton", "New Era")
2. **Device model** — exact model designation (e.g. "ML600", "NE-1000")
3. **Approach** — add directly to flowchem (`src/flowchem/devices/`) or as an external plugin. Use direct approach unless the device requires heavy new dependencies.
4. **Component types** — which functional interfaces does this device expose? One or more of:
   - `syringe_pump` — infuse / withdraw / stop (displacement pumps that can reverse)
   - `hplc_pump` — infuse / stop only (peristaltic, HPLC, unidirectional)
   - `pump` — generic pump, when neither above fits
   - `valve` — rotary multiport valve
   - `pressure_sensor`
   - `photo_sensor`
   - `temperature` — set/get temperature with configurable limits
   - `stirring` — set/get stir speed
   - `mass_flow_controller`
   - `adc` — analog-to-digital read
   - `dac` — digital-to-analog write
   - `custom` — define your own component from `FlowchemComponent`
5. **Simulated variant?** (yes/no) — creates a `{DeviceClass}Sim` stub for offline testing

---

## Step 2 — Derive naming identifiers

| Variable | Rule | Example |
|---|---|---|
| `manufacturer_dir` | `manufacturer.lower()`, spaces/hyphens → underscores | "New Era" → `new_era` |
| `device_snake` | `model.lower()`, spaces/hyphens → underscores, strip special chars | "NE-1000" → `ne_1000` |
| `DeviceClass` | PascalCase of model, strip hyphens/spaces | "NE-1000" → `Ne1000` |

Component suffix table:

| Component type | Class suffix | File suffix |
|---|---|---|
| `syringe_pump` / `hplc_pump` / `pump` | `Pump` | `_pump` |
| `valve` | `Valve` | `_valve` |
| `pressure_sensor` | `PressureSensor` | `_pressure_sensor` |
| `photo_sensor` | `PhotoSensor` | `_photo_sensor` |
| `temperature` | `TemperatureControl` | `_temperature_control` |
| `stirring` | `StirringControl` | `_stirring_control` |
| `mass_flow_controller` | `MFC` | `_mfc` |
| `adc` | `ADC` | `_adc` |
| `dac` | `DAC` | `_dac` |
| `custom` | (ask user) | (ask user) |

If a device has multiple components of the same type, add a qualifier (e.g. `Ne1000InletValve`, `Ne1000OutletValve`).

---

## Step 3 — Check if manufacturer directory exists

Read `src/flowchem/devices/__init__.py`. If `from .{manufacturer_dir} import *` already exists, only add new files inside the existing directory. Otherwise create the full directory structure and append the wildcard import.

---

## Step 4 — Create scaffolding files

Create all files with **method stubs** (`raise NotImplementedError`). The communication layer will be filled in Step 5 once the documentation has been analysed.

### 4a. Device file — `src/flowchem/devices/{manufacturer_dir}/{device_snake}.py`

```python
"""{ManufacturerStr} {ModelStr} device driver."""

from __future__ import annotations

from loguru import logger

from flowchem.components.device_info import DeviceInfo
from flowchem.devices.flowchem_device import FlowchemDevice
from flowchem.devices.{manufacturer_dir}.{device_snake}_{component_suffix} import {DeviceClass}{ComponentClassSuffix}
# Repeat the import line above for every component file.


class {DeviceClass}(FlowchemDevice):
    """{ManufacturerStr} {ModelStr}."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.device_info = DeviceInfo(
            manufacturer="{ManufacturerStr}",
            model="{ModelStr}",
        )
        # TODO: connection parameters will be added in Step 5

    async def initialize(self) -> None:
        """Open connection and register components."""
        # TODO: establish connection — Step 5
        logger.info(f"{self.device_info.manufacturer} {self.device_info.model} '{self.name}' initialized.")
        self.components.append({DeviceClass}{ComponentClassSuffix}("{component_name}", self))

    async def send_command(self, command: str) -> str:
        """Send a raw command and return the reply. All I/O lives here."""
        # TODO: implement in Step 5
        raise NotImplementedError
```

### 4b. Component file(s) — `src/flowchem/devices/{manufacturer_dir}/{device_snake}_{file_suffix}.py`

```python
"""{ManufacturerStr} {ModelStr} — {ComponentType} component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flowchem.components.pumps.syringe_pump import SyringePump  # change base class per guide below

if TYPE_CHECKING:
    from .{device_snake} import {DeviceClass}


class {DeviceClass}{ComponentClassSuffix}(SyringePump):
    hw_device: {DeviceClass}

    def __init__(self, name: str, hw_device: {DeviceClass}) -> None:
        super().__init__(name, hw_device)
        # Device-specific extra routes will be added in Step 5 if needed.

    # Stubs — implemented in Step 5:
    async def infuse(self, rate: str = "", volume: str = "") -> bool:
        raise NotImplementedError

    async def stop(self) -> bool:
        raise NotImplementedError

    async def is_pumping(self) -> bool:
        raise NotImplementedError

    async def withdraw(self, rate: str = "", volume: str = "") -> bool:
        raise NotImplementedError
```

See the **component base class guide** at the bottom of this file for the correct base class and method signatures per component type.

### 4c. Manufacturer `__init__.py`

```python
"""{ManufacturerStr} devices."""
from .{device_snake} import {DeviceClass}
__all__ = ["{DeviceClass}"]
```

### 4d. Top-level registry (new manufacturers only)

Append to `src/flowchem/devices/__init__.py`:
```python
from .{manufacturer_dir} import *
```

### 4e. Simulated variant (if requested)

Add at the bottom of the device file and export from `__init__.py`:
```python
class {DeviceClass}Sim({DeviceClass}):
    """{ModelStr} simulator — no hardware required."""

    async def initialize(self) -> None:
        self.device_info.version = "sim"
        logger.info(f"[SIM] {self.name} initialized.")
        self.components.append({DeviceClass}{ComponentClassSuffix}("{component_name}", self))

    async def send_command(self, command: str) -> str:
        logger.debug(f"[SIM] {self.name} ← {command!r}")
        return "OK"
```

---

## Step 5 — Implement the communication layer

**Do not skip this step.** Request documentation and implement the actual protocol before finishing.

### 5a. Request documentation

Ask the user to provide any of the following (the more the better):
- Programming/communication manual (PDF path, URL, or pasted text)
- Serial/network connection parameters if already known (baud rate, port, IP, etc.)
- Any existing working code in any language that talks to this device
- Known command examples (e.g. "sending `S\r` stops the pump")

If the user provides a PDF path, read it with the `Read` tool. If they provide a URL, fetch it.

### 5b. Analyse the protocol

From the documentation, extract every item in this checklist. Flag any that are missing (see 5d).

**Physical / transport layer**
- [ ] Interface type: RS-232, RS-485, USB-CDC (appears as COM port), Ethernet TCP, USB-HID, other
- [ ] For serial: baud rate, data bits, parity (N/E/O), stop bits, flow control (None/RTS-CTS/XON-XOFF)
- [ ] For Ethernet: port number, connection mode (persistent / per-command)
- [ ] For vendor library: library name, installation method

**Message framing**
- [ ] Command terminator (e.g. `\r`, `\n`, `\r\n`, `\x03`, none)
- [ ] Response terminator or fixed response length
- [ ] Is there a prompt character the device sends before each reply (e.g. `>`)? Strip it.
- [ ] Multi-packet responses? (read until terminator vs. read N bytes)
- [ ] Maximum response wait time / timeout (typical: 1–10 s)

**Command syntax**
- [ ] Encoding: plain ASCII text, SCPI, Modbus RTU, binary protocol, JSON, other
- [ ] Command structure: prefix + verb + value, or register-based, or opcode + payload
- [ ] Case sensitivity
- [ ] Address/node prefix required (e.g. `/1` in Hamilton, `@01` in some pumps)
- [ ] Checksum or CRC required?

**Device behaviour**
- [ ] Does the device echo the command back before the response? (must be consumed and discarded)
- [ ] Is there an initialisation handshake on connect?
- [ ] Error response format — how does the device signal a command failure?
- [ ] Status / busy-idle query command (needed for `is_pumping()`, `is_target_reached()`, etc.)

**Per-component commands** — for each component method, identify the exact command string:
- Map `infuse(rate, volume)` → command
- Map `stop()` → command
- Map `is_pumping()` → command + response parsing
- Map `set_temperature(temp)` → command + value encoding
- etc.

### 5c. Implement the transport layer in the device file

Choose the pattern that matches the protocol. Replace the `send_command` stub and add connection setup to `__init__` / `initialize()`.

#### Pattern A — ASCII serial (most common)

```python
import asyncio
import aioserial
from flowchem.utils.exceptions import InvalidConfigurationError

class {DeviceClass}(FlowchemDevice):

    def __init__(self, name: str, port: str, baudrate: int = 9600,
                 parity: str = "N", stopbits: int = 1) -> None:
        super().__init__(name)
        self.device_info = DeviceInfo(manufacturer="...", model="...")
        self._port = port
        self._baudrate = baudrate
        self._parity = parity
        self._stopbits = stopbits
        self._serial: aioserial.AioSerial | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        try:
            self._serial = aioserial.AioSerial(
                port=self._port,
                baudrate=self._baudrate,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=5,
            )
        except Exception as e:
            raise InvalidConfigurationError(
                f"Cannot open {self._port}: {e}"
            ) from e
        # Optional: send an identification query and store result in device_info.version
        self.device_info.version = await self._query_version()
        logger.info(f"Connected to {self.device_info.manufacturer} '{self.name}' on {self._port}")
        self.components.append(...)

    async def send_command(self, command: str) -> str:
        """Send ASCII command and return stripped reply."""
        async with self._lock:
            raw = (command + "\r").encode()   # adjust terminator per manual
            await self._serial.write_async(raw)
            reply = await self._serial.readline_async()
        return reply.decode().strip()

    async def _query_version(self) -> str:
        # TODO: replace with real version command from the manual
        return "unknown"
```

#### Pattern B — SCPI (instruments: oscilloscopes, power supplies, analysers)

```python
import asyncio
import aioserial

class {DeviceClass}(FlowchemDevice):

    CMD_TERMINATOR = "\n"

    async def send_command(self, command: str) -> str:
        async with self._lock:
            await self._serial.write_async((command + self.CMD_TERMINATOR).encode())
            if "?" in command:          # query — expect a response
                reply = await self._serial.readline_async()
                return reply.decode().strip()
            return ""

    async def query_errors(self) -> str:
        return await self.send_command("SYST:ERR?")
```

#### Pattern C — Modbus RTU

```python
from pymodbus.client import AsyncModbusSerialClient

class {DeviceClass}(FlowchemDevice):

    def __init__(self, name: str, port: str, slave_id: int = 1) -> None:
        super().__init__(name)
        self._port = port
        self._slave_id = slave_id
        self._client: AsyncModbusSerialClient | None = None

    async def initialize(self) -> None:
        self._client = AsyncModbusSerialClient(
            port=self._port, baudrate=9600, parity="N", stopbits=1
        )
        await self._client.connect()
        ...

    async def read_register(self, address: int) -> int:
        result = await self._client.read_holding_registers(address, count=1, slave=self._slave_id)
        return result.registers[0]

    async def write_register(self, address: int, value: int) -> None:
        await self._client.write_register(address, value, slave=self._slave_id)

    # send_command is not used in Modbus — components call read_register / write_register directly
```

#### Pattern D — Ethernet TCP

```python
import asyncio

class {DeviceClass}(FlowchemDevice):

    def __init__(self, name: str, ip_address: str, port: int = 5000) -> None:
        super().__init__(name)
        self._ip = ip_address
        self._tcp_port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self._ip, self._tcp_port)
        logger.info(f"TCP connection to {self._ip}:{self._tcp_port} established.")
        self.components.append(...)

    async def send_command(self, command: str) -> str:
        async with self._lock:
            self._writer.write((command + "\r\n").encode())
            await self._writer.drain()
            reply = await self._reader.readline()
        return reply.decode().strip()
```

#### Pattern E — Vendor library wrapping

```python
from vendor_package import VendorDevice   # the third-party library

class {DeviceClass}(FlowchemDevice):

    def __init__(self, name: str, port: str) -> None:
        super().__init__(name)
        self._port = port
        self._device: VendorDevice | None = None

    async def initialize(self) -> None:
        loop = asyncio.get_event_loop()
        # Wrap synchronous vendor calls with run_in_executor to avoid blocking the event loop
        self._device = await loop.run_in_executor(None, VendorDevice, self._port)
        self.components.append(...)

    async def send_command(self, command: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._device.send, command)
```

### 5d. Flag missing information — stop and ask the user

If any of the following cannot be answered from the documentation, **stop and explicitly list what is missing** before writing any code. Do not guess or leave silent stubs.

Critical gaps that block implementation:
- Connection parameters (baud rate, port, IP) not documented
- Command terminator / response format not specified
- No command exists in the manual for a required component method (e.g. no way to query pump status)
- Response parsing for numeric values is ambiguous (units? scaling factor? byte order?)
- Handshake or initialisation sequence not described
- Error response indistinguishable from a normal reply

Example flag message to the user:
> The manual describes how to set the flow rate (command `F{value}`) but does not document a command to query whether the pump is currently running. `is_pumping()` cannot be implemented without this. Please check:
> - Is there a status query command? (e.g. a `?` or `STATUS` command)
> - Is there a way to read back the current flow rate, which could serve as a proxy?
> - Or should `is_pumping()` always return `True` while a command is in progress (requires tracking state internally)?

### 5e. Implement component methods

For each method stub in the component files, implement the actual command based on the analysed protocol. Use `ureg` (pint) for all physical quantities.

Key conventions:
- Parse rate/volume strings via `ureg.Quantity(value).m_as("ml/min")` to get a float in the expected unit
- Use `from flowchem import ureg` at the top of the device file
- For base classes that do range validation in `set_temperature()` / `set_speed()`, call `await super().method(arg)` first and use the returned `pint.Quantity` — then translate to the device command

Example — implementing `infuse` for an ASCII serial pump:
```python
async def infuse(self, rate: str = "", volume: str = "") -> bool:
    from flowchem import ureg
    rate_val = ureg.Quantity(rate).m_as("ml/min") if rate else 1.0
    vol_val  = ureg.Quantity(volume).m_as("ml")   if volume else 0.0
    reply = await self.hw_device.send_command(f"FR{rate_val:.3f}")
    if volume:
        await self.hw_device.send_command(f"VOL{vol_val:.3f}")
    await self.hw_device.send_command("RUN")
    return reply != "ERR"
```

---

## Step 6 — Verification checklist

**Device class**
- [ ] Subclasses `FlowchemDevice`
- [ ] `__init__` calls `super().__init__(name)` first
- [ ] `self.device_info = DeviceInfo(manufacturer=..., model=...)` set in `__init__`
- [ ] `initialize()` appends at least one component to `self.components`
- [ ] All I/O (serial/TCP/library) is in the device class; no component imports transport libraries

**Component class(es)**
- [ ] Correct base class from the guide below
- [ ] `hw_device: {DeviceClass}` class attribute declared
- [ ] `__init__` calls `super().__init__(name, hw_device)` — `TemperatureControl` passes `TempRange` too
- [ ] No direct I/O; all calls go through `self.hw_device`
- [ ] `SyringePump` subclasses declare `is_withdrawing_capable()` as `@staticmethod`
- [ ] `from __future__ import annotations` at top of each component file
- [ ] Device class imported inside `if TYPE_CHECKING:` block
- [ ] No method still raises `NotImplementedError` unless flagged as genuinely not supported

**Package wiring**
- [ ] Manufacturer `__init__.py` has `__all__` listing all exported classes
- [ ] `src/flowchem/devices/__init__.py` contains `from .{manufacturer_dir} import *` (new manufacturer only)

**Suggest this test snippet** to verify the server starts:
```toml
# {device_snake}_test.toml
[device.my-{device_snake}]
type = "{DeviceClass}"
port = "COM1"   # adjust to actual port / ip_address
```
Run: `flowchem {device_snake}_test.toml`

---

## Appendix — Component base class guide

Choose the base class that genuinely matches the device interface. If fitting the interface requires unnatural workarounds, inherit from `FlowchemComponent` directly.

**`syringe_pump`** → `from flowchem.components.pumps.syringe_pump import SyringePump`
```python
@staticmethod
def is_withdrawing_capable() -> bool: return True  # False if no reverse

async def infuse(self, rate: str = "", volume: str = "") -> bool: ...
async def stop(self) -> bool: ...
async def is_pumping(self) -> bool: ...
async def withdraw(self, rate: str = "", volume: str = "") -> bool: ...
```

**`hplc_pump`** → `from flowchem.components.pumps.hplc_pump import HPLCPump`
```python
# is_withdrawing_capable() is False by default
async def infuse(self, rate: str = "", volume: str = "") -> bool: ...
async def stop(self) -> bool: ...
async def is_pumping(self) -> bool: ...
```

**`valve`** — ask user for port layout before choosing:
- Pre-built: `from flowchem.components.valves.distribution_valves import SixPortDistributionValve` (also Two/Four/Eight/Ten/Twelve/Sixteen)
- Injection: `from flowchem.components.valves.injection_valves import SixPortTwoPositionValve`
- Custom: `from flowchem.components.valves.valve import Valve` — supply `stator_ports`, `rotor_ports`; implement `_change_connections()`; `hw_device` must have `get_raw_position()` / `set_raw_position()`

**`pressure_sensor`** → `from flowchem.components.sensors.pressure_sensor import PressureSensor`
```python
async def read_pressure(self, units: str = "bar") -> float: ...
```

**`photo_sensor`** → `from flowchem.components.sensors.photo_sensor import PhotoSensor`
```python
async def acquire_signal(self): ...
async def calibrate_zero(self): ...
```

**`temperature`** → `from flowchem.components.technical.temperature import TemperatureControl, TempRange`
```python
# __init__ must pass TempRange with real hardware limits:
# super().__init__(name, hw_device, TempRange(min=ureg.Quantity("-40 degC"), max=ureg.Quantity("200 degC")))
# set_temperature() in the base validates range → call super() first, then translate to command

async def get_temperature(self) -> float: ...
async def is_target_reached(self) -> bool: ...
async def power_on(self): ...
async def power_off(self): ...
```

**`stirring`** → `from flowchem.components.technical.stirring import StirringControl`
```python
# super().__init__(name, hw_device, min_speed=100, max_speed=1400)  # set real limits
# set_speed() in the base validates range → call super() first, then translate to command

async def get_speed(self) -> float: ...
async def get_speed_setpoint(self) -> float: ...
async def power_on(self): ...
async def power_off(self): ...
async def is_on(self) -> bool: ...
```

**`mass_flow_controller`** → `from flowchem.components.technical.flow import MassFlowController`
```python
async def set_flow_setpoint(self, flowrate: str = "0 ml/min") -> bool: ...
async def get_flow_setpoint(self) -> float: ...
async def stop(self) -> bool: ...
```

**`adc`** → `from flowchem.components.technical.ADC import AnalogDigitalConverter`
```python
async def read(self) -> float: ...
```

**`dac`** → `from flowchem.components.technical.DAC import DigitalAnalogConverter`
```python
async def read(self) -> float: ...
async def set(self, value: str = "0 V") -> bool: ...
```

**`custom`** → `from flowchem.components.flowchem_component import FlowchemComponent`
Define methods and register all routes manually via `self.add_api_route(path, fn, methods=["GET"|"PUT"])`.

---

## Reference: key files

| Purpose | Path |
|---|---|
| Base device class | `src/flowchem/devices/flowchem_device.py` |
| Device registry | `src/flowchem/devices/__init__.py` |
| Canonical minimal example | `src/flowchem/devices/fakedevice/` |
| All component base classes | `src/flowchem/components/` |
| Add-device guide | `docs/development/additional/add_device/add_to_flowchem.md` |
| Plugin guide | `docs/development/additional/add_device/add_as_plugin.md` |
| Real-device walkthrough | `docs/development/additional/add_device/example_explained.md` |
