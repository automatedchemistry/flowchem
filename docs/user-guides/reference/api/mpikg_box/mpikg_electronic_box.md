## Endpoints

### `GET /mybox/`

**Summary:** Get Device Info
**Description:** 
**Tags:** mybox
**Operation ID:** `get_device_info_mybox__get`

**Responses:**
- `200`: Successful Response

---

### `GET /mybox/adc/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_adc__get`

**Responses:**
- `200`: Successful Response

---

### `GET /mybox/adc/read`

**Summary:** Read
**Description:** Read ADC (Analog-to-Digital Converter) channel (1 to 8).

Returns:
    voltage value in volts.
**Tags:** mybox, mybox
**Operation ID:** `read_mybox_adc_read_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/adc/read_all`

**Summary:** Read All
**Description:** Read all ADC (Analog-to-Digital Converter) channels.

Returns:
    dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
    voltage values in volts.
**Tags:** mybox, mybox
**Operation ID:** `read_all_mybox_adc_read_all_get`

**Responses:**
- `200`: Successful Response

---

### `GET /mybox/dac/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_dac__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/dac/power-on`

**Summary:** Power On
**Description:** Turn power on.
**Tags:** mybox, mybox
**Operation ID:** `power_on_mybox_dac_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/dac/power-off`

**Summary:** Power Off
**Description:** Turn off power.
**Tags:** mybox, mybox
**Operation ID:** `power_off_mybox_dac_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/dac/channel`

**Summary:** Set Channel
**Description:** Set the DAC output voltage for a given channel.

Args:
    channel (str, optional): DAC channel index. Must be a digit string
        (e.g., "1", "2"). Defaults to "1".
    value (str, optional): Target voltage with unit, expressed as a string
        parsable by the unit registry (e.g., "2.5 V", "500 mV").
        Defaults to "0 V".

Returns:
    bool:
        - True if the voltage command was successfully sent to the hardware.
        - False if the channel argument is invalid or if the value cannot be parsed.

Notes:
    - The channel must be convertible to an integer.
    - The voltage string is parsed using the unit registry (`ureg`).
    - Any parsing or hardware errors are logged via `logger`.
**Tags:** mybox, mybox
**Operation ID:** `set_channel_mybox_dac_channel_put`

**Query Parameters:**
- `channel` (string, optional, default = `1`)
- `value` (string, optional, default = `0 V`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/dac/channel`

**Summary:** Read Channel
**Description:** Read the DAC output of a channel.

Args:
    channel (str): DAC channel index (1 or 2).

Returns:
    float: DAC output in volts.
**Tags:** mybox, mybox
**Operation ID:** `read_channel_mybox_dac_channel_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_relay__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay/power-on`

**Summary:** Power On
**Description:** Set the state ON of a single relay channel.

Args:
    channel (str): Relay channel index (1–32).

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_on_mybox_relay_power_on_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay/power-off`

**Summary:** Power Off
**Description:** Set the state OFF of a single relay channel.

Args:
    channel (str): Relay channel index (1–32).

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_off_mybox_relay_power_off_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay/channel_setpoint`

**Summary:** Read Channel Setpoint
**Description:** Read the current relay state of a single channel.

Each channel corresponds to one relay (1–32), organized in four ports:
- Port A → channels 1–8
- Port B → channels 9–16
- Port C → channels 17–24
- Port D → channels 25–32

Channel states:
    * 0 → OFF
    * 1 → Half power (power1 only, ~12 V)
    * 2 → Full power (power1 + power2, ~24 V)

Args:
    channel (str): Relay channel index (1–32).

Returns:
    int | bool:
        - 0, 1, or 2 → valid relay state.
        - None → if the channel index is invalid.
**Tags:** mybox, mybox
**Operation ID:** `read_channel_setpoint_mybox_relay_channel_setpoint_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay/channel`

**Summary:** Set Channel
**Description:** Set the state of a single relay channel.

Args:
    channel (str): Relay channel index (1–32).
    value (str): Desired channel state:
        * 0 → OFF
        * 1 → Half power (~12 V)
        * 2 → Full power (~24 V)
    keep_port_status (str, optional):
        If true (default), preserves the state of other channels
        in the same port (module).
        If false, all other channels in the port are reset to 0.
    switch_to_low_after (float, optional):
        If >0 and value=2, automatically switches the channel
        to 1 (half power) after the given delay in seconds.
        Useful to reduce heat generation.
        Default = -1 (disabled).

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `set_channel_mybox_relay_channel_put`

**Query Parameters:**
- `channel` (string, required, default = ``)
- `value` (string, required, default = ``)
- `keep_port_status` (string, optional, default = `true`)
- `switch_to_low_after` (number, optional, default = `-1`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay/read_channels_modules`

**Summary:** Read Channels Modules
**Description:** Query the relay states of all channels in modules.

Returns:
    dict[str, list[int]]: A dictionary mapping port modules IDs ("a", "b", "c", "d")
    to lists of 8 integers each.
    Each integer represents the current state of one of the 8 channels:
        * 0 → OFF
        * 1 → Half power (~12 V)
        * 2 → Full power (~24 V)

Example:
    {
        "a": [0, 1, 2, 0, 0, 1, 0, 0],
        "b": [...],
        "c": [...],
        "d": [...]
    }
**Tags:** mybox, mybox
**Operation ID:** `read_channels_modules_mybox_relay_read_channels_modules_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay/port_module`

**Summary:** Set Port Module
**Description:** Set the relay states of all 8 channels in a port module.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    values (str): List of up to 8 integers (0, 1, or 2).
        - Example: "00010012"
        - If shorter than 8, remaining channels are set to 0.
        - If longer than 8, extra values are ignored.
    switch_to_low_after (float, optional):
        If >0, channels set to 2 (full power) are automatically
        reduced to 1 (half power) after the given delay in seconds.
        Default = -1 (disabled).
    port (str, optional): Port identifier ("a", "b", "c", or "d").
        Default = "a".

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `set_port_module_mybox_relay_port_module_put`

**Query Parameters:**
- `values` (string, required, default = ``)
- `switch_to_low_after` (number, optional, default = `-1`)
- `port` (string, optional, default = `a`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

## Components

### `ComponentInfo` (object)

**Description:** Metadata associated with flowchem components.

**Properties:**
- `name`: string (default: ``)
- `parent_device`: string (default: ``)
- `type`: string (default: ``)
- `corresponding_class`: array (default: `[]`)
- `owl_subclass_of`: array (default: `['http://purl.obolibrary.org/obo/OBI_0000968']`)

---

### `DeviceInfo` (object)

**Description:** Metadata associated with hardware devices.

**Properties:**
- `manufacturer`: string (default: ``)
- `model`: string (default: ``)
- `version`: string (default: ``)
- `serial_number`: object (default: `unknown`)
- `components`: object (default: `{}`)
- `backend`: string (default: `flowchem v. 1.1.0.post1`)
- `authors`: array (default: `[]`)
- `additional_info`: object (default: `{}`)

---

### `HTTPValidationError` (object)


**Properties:**
- `detail`: array

---

### `ValidationError` (object)

**Required:** loc, msg, type

**Properties:**
- `loc`: array
- `msg`: string
- `type`: string

---
