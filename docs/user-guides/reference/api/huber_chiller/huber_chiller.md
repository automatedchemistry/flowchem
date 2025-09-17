## Endpoints

### `GET /my-chiller/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-chiller
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-chiller/temperature-control/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-chiller, my-chiller
**Operation ID:** `get_component_info_fake_device_temperature_control__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-chiller/temperature-control/temperature`

**Summary:** Set Temperature
**Description:** Set the target temperature to the given value.

Args:
    temp (str): The desired temperature as a string in natural language.

Returns:
    bool: True if the temperature was successfully set, False otherwise.
**Tags:** my-chiller, my-chiller
**Operation ID:** `set_temperature_fake_device_temperature_control_temperature_put`

**Query Parameters:**
- `temp` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-chiller/temperature-control/temperature`

**Summary:** Get Temperature
**Description:** Get the current temperature.

Returns:
    float: The current temperature in Celsius.
**Tags:** my-chiller, my-chiller
**Operation ID:** `get_temperature_fake_device_temperature_control_temperature_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-chiller/temperature-control/power-on`

**Summary:** Power On
**Description:** Turn on the temperature control.

Returns:
    bool: True if the command was successfully sent, False otherwise.
**Tags:** my-chiller, my-chiller
**Operation ID:** `power_on_fake_device_temperature_control_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-chiller/temperature-control/power-off`

**Summary:** Power Off
**Description:** Turn off the temperature control.

Returns:
    bool: True if the command was successfully sent, False otherwise.
**Tags:** my-chiller, my-chiller
**Operation ID:** `power_off_fake_device_temperature_control_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-chiller/temperature-control/target-reached`

**Summary:** Is Target Reached
**Description:** Check if the set temperature target has been reached.

Returns:
    bool: True if the target temperature has been reached, False otherwise.
**Tags:** my-chiller, my-chiller
**Operation ID:** `is_target_reached_fake_device_temperature_control_target_reached_get`

**Responses:**
- `200`: Successful Response

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
