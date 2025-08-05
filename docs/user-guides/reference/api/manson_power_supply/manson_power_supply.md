## Endpoints

### `GET /my-mansonpower/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-mansonpower
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-mansonpower/power-control/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `get_component_info_fake_device_power_control__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-mansonpower/power-control/power-on`

**Summary:** Power On
**Description:** Turn on the power supply output.

Returns:
    Awaitable: Result of the power on operation from the hardware device.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `power_on_fake_device_power_control_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-mansonpower/power-control/power-off`

**Summary:** Power Off
**Description:** Turn off the power supply output.

Returns:
    Awaitable: Result of the power off operation from the hardware device.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `power_off_fake_device_power_control_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-mansonpower/power-control/current`

**Summary:** Get Current
**Description:** Retrieve the current output in Amperes.

Returns:
    float: The current output in Amperes.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `get_current_fake_device_power_control_current_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-mansonpower/power-control/current`

**Summary:** Set Current
**Description:** Set the target current using a natural language string.

Args:
    current (str): The desired current as a string in natural language (e.g., '5A', '500mA').

Returns:
    Awaitable: Result of the set_current operation from the hardware device.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `set_current_fake_device_power_control_current_put`

**Query Parameters:**
- `current` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-mansonpower/power-control/voltage`

**Summary:** Get Voltage
**Description:** Retrieve the current output voltage in Volts.

Returns:
    float: The current output voltage in Volts.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `get_voltage_fake_device_power_control_voltage_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-mansonpower/power-control/voltage`

**Summary:** Set Voltage
**Description:** Set the target voltage using a natural language string.

Args:
    voltage (str): The desired voltage as a string in natural language (e.g., '12V', '3.3V').

Returns:
    Awaitable: Result of the set_voltage operation from the hardware device.
**Tags:** my-mansonpower, my-mansonpower
**Operation ID:** `set_voltage_fake_device_power_control_voltage_put`

**Query Parameters:**
- `voltage` (string, required, default = ``)

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
