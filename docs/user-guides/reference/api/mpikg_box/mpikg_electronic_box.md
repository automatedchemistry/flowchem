## Endpoints

### `GET /my-box/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-box
**Operation ID:** `get_device_info_my_box__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-box/adc/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-box, my-box
**Operation ID:** `get_component_info_my_box_adc__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-box/adc/channel`

**Summary:** Read Channel
**Description:** Read ADC (Analog  Digital Channels) channel (1 to 8).

Returns:
    voltage value.
**Tags:** my-box, my-box
**Operation ID:** `read_channel_my_box_adc_channel_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-box/adc/read_all`

**Summary:** Read All
**Description:** Read all ADC (Analog  Digital Channels) channels.

Returns:
    dict[str, float]: Mapping of channel IDs (e.g. "ADC1", "ADC2") to measured
    voltage values.
**Tags:** my-box, my-box
**Operation ID:** `read_all_my_box_adc_read_all_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-box/dac/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-box, my-box
**Operation ID:** `get_component_info_my_box_dac__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-box/dac/channel`

**Summary:** Read Channel
**Description:** Read the DAC output of a channel.

Args:
    channel (str): DAC channel index (1 or 2).

Returns:
    float: DAC output in volts.
**Tags:** my-box, my-box
**Operation ID:** `read_channel_my_box_dac_channel_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-box/dac/channel`

**Summary:** Set Channel
**Description:** "
Set DAC output voltage.

Args:
    channel (int, optional): DAC channel index (1 or 2).
    volts (float, optional): Target voltage (0 to 5 V).

Returns:
    bool: True if the command succeeded, False otherwise.
**Tags:** my-box, my-box
**Operation ID:** `set_channel_my_box_dac_channel_put`

**Query Parameters:**
- `channel` (string, required, default = ``)
- `value` (number, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-box/hele/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-box, my-box
**Operation ID:** `get_component_info_my_box_hele__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-box/hele/channel`

**Summary:** Read Channel
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
        - False → if the channel index is invalid.
**Tags:** my-box, my-box
**Operation ID:** `read_channel_my_box_hele_channel_get`

**Query Parameters:**
- `channel` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-box/hele/channel`

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
        in the same port.
        If false, all other channels in the port are reset to 0.
    switch_to_low_after (float, optional):
        If >0 and value=2, automatically switches the channel
        to 1 (half power) after the given delay in seconds.
        Useful to reduce heat dissipation.
        Default = -1 (disabled).

Returns:
    bool: True if the device acknowledged the command, False otherwise.
**Tags:** my-box, my-box
**Operation ID:** `set_channel_my_box_hele_channel_put`

**Query Parameters:**
- `channel` (string, required, default = ``)
- `value` (string, required, default = ``)
- `keep_port_status` (string, optional, default = `true`)
- `switch_to_low_after` (number, optional, default = `-1`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-box/hele/read_all`

**Summary:** Get All
**Description:** Query the relay states of all channels.

Returns:
    dict[str, list[int]]: A dictionary mapping port IDs ("a", "b", "c", "d")
    to lists of 8 integers each.
    Each integer is the channel state:
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
**Tags:** my-box, my-box
**Operation ID:** `get_all_my_box_hele_read_all_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-box/hele/port`

**Summary:** Set Ports
**Description:** Set the relay states of all 8 channels in a port.

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
**Tags:** my-box, my-box
**Operation ID:** `set_ports_my_box_hele_port_put`

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
- `backend`: string (default: `flowchem v. 1.0.0a3`)
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
