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

### `PUT /mybox/dac/set`

**Summary:** Set
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
**Operation ID:** `set_mybox_dac_set_put`

**Query Parameters:**
- `channel` (string, optional, default = `1`)
- `value` (string, optional, default = `0 V`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/dac/read`

**Summary:** Read
**Description:** Read the DAC output of a channel.

Args:
    channel (str): DAC channel index (1 or 2).

Returns:
    float: DAC output in volts.
**Tags:** mybox, mybox
**Operation ID:** `read_mybox_dac_read_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-A/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_relay_A__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-A/power-on`

**Summary:** Power On
**Description:** Power ON a single relay channel at full power (~24 V).

Sends a command to set the specified channel to state "2".

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping:
        - Port a → channels 1–8
        - Port b → channels 9–16
        - Port c → channels 17–24
        - Port d → channels 25–32

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_on_mybox_relay_A_power_on_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-A/power-off`

**Summary:** Power Off
**Description:** Power OFF a single relay channel.

Sends a command to set the given channel to state "0" (no voltage).

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_off_mybox_relay_A_power_off_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-A/multiple_channel`

**Summary:** Multiple Channel
**Description:** Set the relay states of all 8 channels on the current port simultaneously.

Each character in `values` represents one channel’s state:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    values (str): String of up to 8 digits (0, 1, or 2).
        Example: "00010012"
        - If shorter than 8, remaining channels default to 0 (OFF).
        - If longer than 8, extra values are ignored.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `multiple_channel_mybox_relay_A_multiple_channel_put`

**Query Parameters:**
- `values` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-A/channel_set_point`

**Summary:** Read Channel Set Point
**Description:** Read the current state of a specific relay channel.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port.

Returns:
    int | None:
        - 0, 1, or 2 → Valid relay state.
        - None → If the channel index is invalid or not part of this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channel_set_point_mybox_relay_A_channel_set_point_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-A/channels_set_point`

**Summary:** Read Channels Set Point
**Description:** Read the current states of all 8 channels on the current port.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Returns:
    list[int]: List of 8 integers (0, 1, or 2) representing the current state
    of each relay channel on this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channels_set_point_mybox_relay_A_channels_set_point_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-A/lower_power_approach`

**Summary:** Set Lower Power Approach
**Description:** Configure automatic switching from full power to half power after a delay.

This function reduces heat generation by automatically changing the relay output
from full power (2) to half power (1) after the specified time.
If the delay is set to 0 seconds, the feature is disabled.

Args:
    switch_to_low_after (str): Delay time before switching to half power, with units.
        Example: "1 s", "500 ms", "2 s".
        Use "0 s" to disable automatic reduction.
**Tags:** mybox, mybox
**Operation ID:** `set_lower_power_approach_mybox_relay_A_lower_power_approach_put`

**Query Parameters:**
- `switch_to_low_after` (string, optional, default = `1 s`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-B/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_relay_B__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-B/power-on`

**Summary:** Power On
**Description:** Power ON a single relay channel at full power (~24 V).

Sends a command to set the specified channel to state "2".

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping:
        - Port a → channels 1–8
        - Port b → channels 9–16
        - Port c → channels 17–24
        - Port d → channels 25–32

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_on_mybox_relay_B_power_on_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-B/power-off`

**Summary:** Power Off
**Description:** Power OFF a single relay channel.

Sends a command to set the given channel to state "0" (no voltage).

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_off_mybox_relay_B_power_off_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-B/multiple_channel`

**Summary:** Multiple Channel
**Description:** Set the relay states of all 8 channels on the current port simultaneously.

Each character in `values` represents one channel’s state:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    values (str): String of up to 8 digits (0, 1, or 2).
        Example: "00010012"
        - If shorter than 8, remaining channels default to 0 (OFF).
        - If longer than 8, extra values are ignored.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `multiple_channel_mybox_relay_B_multiple_channel_put`

**Query Parameters:**
- `values` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-B/channel_set_point`

**Summary:** Read Channel Set Point
**Description:** Read the current state of a specific relay channel.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port.

Returns:
    int | None:
        - 0, 1, or 2 → Valid relay state.
        - None → If the channel index is invalid or not part of this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channel_set_point_mybox_relay_B_channel_set_point_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-B/channels_set_point`

**Summary:** Read Channels Set Point
**Description:** Read the current states of all 8 channels on the current port.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Returns:
    list[int]: List of 8 integers (0, 1, or 2) representing the current state
    of each relay channel on this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channels_set_point_mybox_relay_B_channels_set_point_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-B/lower_power_approach`

**Summary:** Set Lower Power Approach
**Description:** Configure automatic switching from full power to half power after a delay.

This function reduces heat generation by automatically changing the relay output
from full power (2) to half power (1) after the specified time.
If the delay is set to 0 seconds, the feature is disabled.

Args:
    switch_to_low_after (str): Delay time before switching to half power, with units.
        Example: "1 s", "500 ms", "2 s".
        Use "0 s" to disable automatic reduction.
**Tags:** mybox, mybox
**Operation ID:** `set_lower_power_approach_mybox_relay_B_lower_power_approach_put`

**Query Parameters:**
- `switch_to_low_after` (string, optional, default = `1 s`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-C/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_relay_C__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-C/power-on`

**Summary:** Power On
**Description:** Power ON a single relay channel at full power (~24 V).

Sends a command to set the specified channel to state "2".

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping:
        - Port a → channels 1–8
        - Port b → channels 9–16
        - Port c → channels 17–24
        - Port d → channels 25–32

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_on_mybox_relay_C_power_on_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-C/power-off`

**Summary:** Power Off
**Description:** Power OFF a single relay channel.

Sends a command to set the given channel to state "0" (no voltage).

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_off_mybox_relay_C_power_off_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-C/multiple_channel`

**Summary:** Multiple Channel
**Description:** Set the relay states of all 8 channels on the current port simultaneously.

Each character in `values` represents one channel’s state:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    values (str): String of up to 8 digits (0, 1, or 2).
        Example: "00010012"
        - If shorter than 8, remaining channels default to 0 (OFF).
        - If longer than 8, extra values are ignored.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `multiple_channel_mybox_relay_C_multiple_channel_put`

**Query Parameters:**
- `values` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-C/channel_set_point`

**Summary:** Read Channel Set Point
**Description:** Read the current state of a specific relay channel.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port.

Returns:
    int | None:
        - 0, 1, or 2 → Valid relay state.
        - None → If the channel index is invalid or not part of this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channel_set_point_mybox_relay_C_channel_set_point_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-C/channels_set_point`

**Summary:** Read Channels Set Point
**Description:** Read the current states of all 8 channels on the current port.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Returns:
    list[int]: List of 8 integers (0, 1, or 2) representing the current state
    of each relay channel on this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channels_set_point_mybox_relay_C_channels_set_point_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-C/lower_power_approach`

**Summary:** Set Lower Power Approach
**Description:** Configure automatic switching from full power to half power after a delay.

This function reduces heat generation by automatically changing the relay output
from full power (2) to half power (1) after the specified time.
If the delay is set to 0 seconds, the feature is disabled.

Args:
    switch_to_low_after (str): Delay time before switching to half power, with units.
        Example: "1 s", "500 ms", "2 s".
        Use "0 s" to disable automatic reduction.
**Tags:** mybox, mybox
**Operation ID:** `set_lower_power_approach_mybox_relay_C_lower_power_approach_put`

**Query Parameters:**
- `switch_to_low_after` (string, optional, default = `1 s`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-D/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** mybox, mybox
**Operation ID:** `get_component_info_mybox_relay_D__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-D/power-on`

**Summary:** Power On
**Description:** Power ON a single relay channel at full power (~24 V).

Sends a command to set the specified channel to state "2".

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping:
        - Port a → channels 1–8
        - Port b → channels 9–16
        - Port c → channels 17–24
        - Port d → channels 25–32

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_on_mybox_relay_D_power_on_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-D/power-off`

**Summary:** Power Off
**Description:** Power OFF a single relay channel.

Sends a command to set the given channel to state "0" (no voltage).

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port mapping.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `power_off_mybox_relay_D_power_off_put`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /mybox/relay-D/multiple_channel`

**Summary:** Multiple Channel
**Description:** Set the relay states of all 8 channels on the current port simultaneously.

Each character in `values` represents one channel’s state:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    values (str): String of up to 8 digits (0, 1, or 2).
        Example: "00010012"
        - If shorter than 8, remaining channels default to 0 (OFF).
        - If longer than 8, extra values are ignored.

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** mybox, mybox
**Operation ID:** `multiple_channel_mybox_relay_D_multiple_channel_put`

**Query Parameters:**
- `values` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-D/channel_set_point`

**Summary:** Read Channel Set Point
**Description:** Read the current state of a specific relay channel.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Args:
    channel (str): Relay channel index (1–8) or (1–32) depending on the port.

Returns:
    int | None:
        - 0, 1, or 2 → Valid relay state.
        - None → If the channel index is invalid or not part of this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channel_set_point_mybox_relay_D_channel_set_point_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /mybox/relay-D/channels_set_point`

**Summary:** Read Channels Set Point
**Description:** Read the current states of all 8 channels on the current port.

Channel states:
    * 0 → OFF
    * 1 → Half power (~12 V)
    * 2 → Full power (~24 V)

Returns:
    list[int]: List of 8 integers (0, 1, or 2) representing the current state
    of each relay channel on this port.
**Tags:** mybox, mybox
**Operation ID:** `read_channels_set_point_mybox_relay_D_channels_set_point_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /mybox/relay-D/lower_power_approach`

**Summary:** Set Lower Power Approach
**Description:** Configure automatic switching from full power to half power after a delay.

This function reduces heat generation by automatically changing the relay output
from full power (2) to half power (1) after the specified time.
If the delay is set to 0 seconds, the feature is disabled.

Args:
    switch_to_low_after (str): Delay time before switching to half power, with units.
        Example: "1 s", "500 ms", "2 s".
        Use "0 s" to disable automatic reduction.
**Tags:** mybox, mybox
**Operation ID:** `set_lower_power_approach_mybox_relay_D_lower_power_approach_put`

**Query Parameters:**
- `switch_to_low_after` (string, optional, default = `1 s`)

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
