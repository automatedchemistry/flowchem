## Endpoints

### `GET /my-peltier/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-peltier
**Operation ID:** `get_device_info_my_peltier__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-peltier/temperature_control/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-peltier, my-peltier
**Operation ID:** `get_component_info_my_peltier_temperature_control__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-peltier/temperature_control/is-reachable`

**Summary:** Is Reachable
**Description:** Return ONLINE if the temperature controller responds to a temperature query.
**Tags:** my-peltier, my-peltier
**Operation ID:** `is_reachable_my_peltier_temperature_control_is_reachable_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-peltier/temperature_control/is-idle`

**Summary:** Is Idle
**Description:** Check whether the set temperature target has been reached.
**Tags:** my-peltier, my-peltier
**Operation ID:** `is_idle_my_peltier_temperature_control_is_idle_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-peltier/temperature_control/temperature`

**Summary:** Set Temperature
**Description:** Set the target temperature to the given string in "magnitude and unit" format.
**Tags:** my-peltier, my-peltier
**Operation ID:** `set_temperature_my_peltier_temperature_control_temperature_put`

**Query Parameters:**
- `temperature` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-peltier/temperature_control/temperature`

**Summary:** Get Temperature
**Description:** Return temperature in Celsius.
**Tags:** my-peltier, my-peltier
**Operation ID:** `get_temperature_my_peltier_temperature_control_temperature_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-peltier/temperature_control/power-on`

**Summary:** Power On
**Description:** Turn on temperature control.
**Tags:** my-peltier, my-peltier
**Operation ID:** `power_on_my_peltier_temperature_control_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-peltier/temperature_control/power-off`

**Summary:** Power Off
**Description:** Turn off temperature control.
**Tags:** my-peltier, my-peltier
**Operation ID:** `power_off_my_peltier_temperature_control_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-peltier/temperature_control/target-reached`

**Summary:** Is Target Reached
**Description:** Return True if the set temperature target has been reached.
**Tags:** my-peltier, my-peltier
**Operation ID:** `is_target_reached_my_peltier_temperature_control_target_reached_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-peltier/temperature_control/temperature-setpoint`

**Summary:** Get Temperature Setpoint
**Description:** Return the current set temperature from the Peltier parameter list.
**Tags:** my-peltier, my-peltier
**Operation ID:** `get_temperature_setpoint_my_peltier_temperature_control_temperature_setpoint_get`

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
- `backend`: string (default: `flowchem v. 1.1.1`)
- `authors`: array (default: `[]`)
- `additional_info`: object (default: `{}`)

---

### `HTTPValidationError` (object)


**Properties:**
- `detail`: array

---

### `ReachabilityStatus` (string)


**Properties:**

---

### `ValidationError` (object)

**Required:** loc, msg, type

**Properties:**
- `loc`: array
- `msg`: string
- `type`: string
- `input`: object
- `ctx`: object

---
