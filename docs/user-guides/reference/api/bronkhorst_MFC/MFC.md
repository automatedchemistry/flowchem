## Endpoints

### `GET /my-MFC/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-MFC
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-MFC/MFC/`

**Summary:** Get Component Info
**Description:** Return metadata.
**Tags:** my-MFC, my-MFC
**Operation ID:** `get_component_info_fake_device_MFC__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-MFC/MFC/get-flow-rate`

**Summary:** Get Flow Setpoint
**Description:** Get the current flow rate in ml/min.

Returns:
--------
float
    The current flow rate in ml/min.
**Tags:** my-MFC, my-MFC
**Operation ID:** `get_flow_setpoint_fake_device_MFC_get_flow_rate_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-MFC/MFC/set-flow-rate`

**Summary:** Set Flow Setpoint
**Description:** Set the flow rate to the instrument; default unit is ml/min.

Parameters:
-----------
flowrate : str
    The desired flow rate to set.

Returns:
--------
bool
    True if the flow rate setpoint was set successfully.
**Tags:** my-MFC, my-MFC
**Operation ID:** `set_flow_setpoint_fake_device_MFC_set_flow_rate_put`

**Query Parameters:**
- `flowrate` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-MFC/MFC/stop`

**Summary:** Stop
**Description:** Stop the mass flow controller.

Returns:
--------
bool
    True if the mass flow controller was stopped successfully.
**Tags:** my-MFC, my-MFC
**Operation ID:** `stop_fake_device_MFC_stop_put`

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
