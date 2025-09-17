## Endpoints

### `GET /my-EPC/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-EPC
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-EPC/EPC/`

**Summary:** Get Component Info
**Description:** Return metadata.
**Tags:** my-EPC, my-EPC
**Operation ID:** `get_component_info_fake_device_EPC__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-EPC/EPC/power-on`

**Summary:** Power On
**Description:** Power on the sensor.

Returns:
--------
None
**Tags:** my-EPC, my-EPC
**Operation ID:** `power_on_fake_device_EPC_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-EPC/EPC/power-off`

**Summary:** Power Off
**Description:** Power off the sensor.

Returns:
--------
None
**Tags:** my-EPC, my-EPC
**Operation ID:** `power_off_fake_device_EPC_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-EPC/EPC/read-pressure`

**Summary:** Read Pressure
**Description:** Read the current pressure from the sensor and return it in the specified units.

Parameters:
-----------
units : str, optional
    The units in which to return the pressure (default is bar).

Returns:
--------
float
    The current pressure in the specified units.
**Tags:** my-EPC, my-EPC
**Operation ID:** `read_pressure_fake_device_EPC_read_pressure_get`

**Query Parameters:**
- `units` (string, optional, default = `bar`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-EPC/EPC/get-pressure`

**Summary:** Get Pressure
**Description:** Get the current system pressure in bar.

Returns:
--------
float
    The current pressure in bar.
**Tags:** my-EPC, my-EPC
**Operation ID:** `get_pressure_fake_device_EPC_get_pressure_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-EPC/EPC/set-pressure`

**Summary:** Set Pressure Setpoint
**Description:** Set the controlled pressure to the instrument; default unit is bar.

Parameters:
-----------
pressure : str
    The desired pressure to set.

Returns:
--------
bool
    True if the pressure setpoint was set successfully.
**Tags:** my-EPC, my-EPC
**Operation ID:** `set_pressure_setpoint_fake_device_EPC_set_pressure_put`

**Query Parameters:**
- `pressure` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-EPC/EPC/stop`

**Summary:** Stop
**Description:** Stop the pressure controller by setting pressure to 0 bar.

Returns:
--------
bool
    True if the pressure controller was stopped successfully.
**Tags:** my-EPC, my-EPC
**Operation ID:** `stop_fake_device_EPC_stop_put`

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
