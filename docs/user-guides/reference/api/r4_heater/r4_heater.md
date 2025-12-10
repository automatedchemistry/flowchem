## Endpoints

### `GET /my-h4heater/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-h4heater
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor1/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_component_info_fake_device_reactor1__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor1/temperature`

**Summary:** Set Temperature
**Description:** Set the target temperature for this channel using a natural language string.

Args:
    temp (str): The desired temperature as a string (e.g., '50C', '75.5C').

Returns:
    Awaitable: Result of the set temperature operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `set_temperature_fake_device_reactor1_temperature_put`

**Query Parameters:**
- `temp` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-h4heater/reactor1/temperature`

**Summary:** Get Temperature
**Description:** Retrieve the current temperature of this channel in Celsius.

Returns:
    float: The current temperature in Celsius.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_temperature_fake_device_reactor1_temperature_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor1/power-on`

**Summary:** Power On
**Description:** Turn on the temperature control for this channel.

Returns:
    Awaitable: Result of the power on operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_on_fake_device_reactor1_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor1/power-off`

**Summary:** Power Off
**Description:** Turn off the temperature control for this channel.

Returns:
    Awaitable: Result of the power off operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_off_fake_device_reactor1_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor1/target-reached`

**Summary:** Is Target Reached
**Description:** Check if the set temperature target has been reached for this channel.

Returns:
    bool: True if the target temperature has been reached, False otherwise.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `is_target_reached_fake_device_reactor1_target_reached_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor2/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_component_info_fake_device_reactor2__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor2/temperature`

**Summary:** Set Temperature
**Description:** Set the target temperature for this channel using a natural language string.

Args:
    temp (str): The desired temperature as a string (e.g., '50C', '75.5C').

Returns:
    Awaitable: Result of the set temperature operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `set_temperature_fake_device_reactor2_temperature_put`

**Query Parameters:**
- `temp` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-h4heater/reactor2/temperature`

**Summary:** Get Temperature
**Description:** Retrieve the current temperature of this channel in Celsius.

Returns:
    float: The current temperature in Celsius.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_temperature_fake_device_reactor2_temperature_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor2/power-on`

**Summary:** Power On
**Description:** Turn on the temperature control for this channel.

Returns:
    Awaitable: Result of the power on operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_on_fake_device_reactor2_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor2/power-off`

**Summary:** Power Off
**Description:** Turn off the temperature control for this channel.

Returns:
    Awaitable: Result of the power off operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_off_fake_device_reactor2_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor2/target-reached`

**Summary:** Is Target Reached
**Description:** Check if the set temperature target has been reached for this channel.

Returns:
    bool: True if the target temperature has been reached, False otherwise.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `is_target_reached_fake_device_reactor2_target_reached_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor3/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_component_info_fake_device_reactor3__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor3/temperature`

**Summary:** Set Temperature
**Description:** Set the target temperature for this channel using a natural language string.

Args:
    temp (str): The desired temperature as a string (e.g., '50C', '75.5C').

Returns:
    Awaitable: Result of the set temperature operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `set_temperature_fake_device_reactor3_temperature_put`

**Query Parameters:**
- `temp` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-h4heater/reactor3/temperature`

**Summary:** Get Temperature
**Description:** Retrieve the current temperature of this channel in Celsius.

Returns:
    float: The current temperature in Celsius.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_temperature_fake_device_reactor3_temperature_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor3/power-on`

**Summary:** Power On
**Description:** Turn on the temperature control for this channel.

Returns:
    Awaitable: Result of the power on operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_on_fake_device_reactor3_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor3/power-off`

**Summary:** Power Off
**Description:** Turn off the temperature control for this channel.

Returns:
    Awaitable: Result of the power off operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_off_fake_device_reactor3_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor3/target-reached`

**Summary:** Is Target Reached
**Description:** Check if the set temperature target has been reached for this channel.

Returns:
    bool: True if the target temperature has been reached, False otherwise.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `is_target_reached_fake_device_reactor3_target_reached_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor4/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_component_info_fake_device_reactor4__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor4/temperature`

**Summary:** Set Temperature
**Description:** Set the target temperature for this channel using a natural language string.

Args:
    temp (str): The desired temperature as a string (e.g., '50C', '75.5C').

Returns:
    Awaitable: Result of the set temperature operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `set_temperature_fake_device_reactor4_temperature_put`

**Query Parameters:**
- `temp` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-h4heater/reactor4/temperature`

**Summary:** Get Temperature
**Description:** Retrieve the current temperature of this channel in Celsius.

Returns:
    float: The current temperature in Celsius.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `get_temperature_fake_device_reactor4_temperature_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor4/power-on`

**Summary:** Power On
**Description:** Turn on the temperature control for this channel.

Returns:
    Awaitable: Result of the power on operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_on_fake_device_reactor4_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-h4heater/reactor4/power-off`

**Summary:** Power Off
**Description:** Turn off the temperature control for this channel.

Returns:
    Awaitable: Result of the power off operation from the hardware device.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `power_off_fake_device_reactor4_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-h4heater/reactor4/target-reached`

**Summary:** Is Target Reached
**Description:** Check if the set temperature target has been reached for this channel.

Returns:
    bool: True if the target temperature has been reached, False otherwise.
**Tags:** my-h4heater, my-h4heater
**Operation ID:** `is_target_reached_fake_device_reactor4_target_reached_get`

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
