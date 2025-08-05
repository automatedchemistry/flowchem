## Endpoints

### `GET /my-elite11/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-elite11
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-elite11/pump/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-elite11, my-elite11
**Operation ID:** `get_component_info_fake_device_pump__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-elite11/pump/infuse`

**Summary:** Infuse
**Description:** Infuse at the specified rate and volume.

Args:
    rate (str): The flow rate for infusion. If not specified, the previous rate will be used.
    volume (str): The target volume for infusion. Defaults to "0 ml".

Returns:
    bool: True if infusion starts successfully, False otherwise.
**Tags:** my-elite11, my-elite11
**Operation ID:** `infuse_fake_device_pump_infuse_put`

**Query Parameters:**
- `rate` (string, optional, default = ``)
- `volume` (string, optional, default = `0 ml`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-elite11/pump/stop`

**Summary:** Stop
**Description:** Stop pump.
**Tags:** my-elite11, my-elite11
**Operation ID:** `stop_fake_device_pump_stop_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-elite11/pump/is-pumping`

**Summary:** Is Pumping
**Description:** Check if the pump is currently moving.

Returns:
    bool: True if the pump is moving, False otherwise.
**Tags:** my-elite11, my-elite11
**Operation ID:** `is_pumping_fake_device_pump_is_pumping_get`

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
