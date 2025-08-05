## Endpoints

### `GET /my-phidgetPressure/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-phidgetPressure
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-phidgetPressure/pressure-sensor/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-phidgetPressure, my-phidgetPressure
**Operation ID:** `get_component_info_fake_device_pressure_sensor__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-phidgetPressure/pressure-sensor/power-on`

**Summary:** Power On
**Description:** Power on the sensor.

Returns:
--------
None
**Tags:** my-phidgetPressure, my-phidgetPressure
**Operation ID:** `power_on_fake_device_pressure_sensor_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-phidgetPressure/pressure-sensor/power-off`

**Summary:** Power Off
**Description:** Power off the sensor.

Returns:
--------
None
**Tags:** my-phidgetPressure, my-phidgetPressure
**Operation ID:** `power_off_fake_device_pressure_sensor_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-phidgetPressure/pressure-sensor/read-pressure`

**Summary:** Read Pressure
**Description:** Read the pressure from the sensor and return it in the specified units.

Args:
    units (str): The units to express the pressure in. Default is "bar".

Returns:
    float: The pressure reading expressed in the specified units.
**Tags:** my-phidgetPressure, my-phidgetPressure
**Operation ID:** `read_pressure_fake_device_pressure_sensor_read_pressure_get`

**Query Parameters:**
- `units` (string, optional, default = `bar`)

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
