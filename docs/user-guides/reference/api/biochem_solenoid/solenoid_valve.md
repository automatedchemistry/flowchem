## Endpoints

### `GET /valve/`

**Summary:** Get Device Info
**Description:** 
**Tags:** valve
**Operation ID:** `get_device_info_valve__get`

**Responses:**
- `200`: Successful Response

---

### `GET /valve/valve/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** valve, valve
**Operation ID:** `get_component_info_valve_valve__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /valve/valve/open`

**Summary:** Open
**Description:** Open the solenoid valve.

This method energises the solenoid if it is normally closed, or de-energises it if it is normally open, switching the valve to the
'open' state, which allows flow through the channel.
**Tags:** valve, valve
**Operation ID:** `open_valve_valve_open_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /valve/valve/close`

**Summary:** Close
**Description:** Close the solenoid valve.

This method de-energizes the solenoid, switching the valve to
the "closed" state, stopping flow through the channel.
**Tags:** valve, valve
**Operation ID:** `close_valve_valve_close_put`

**Responses:**
- `200`: Successful Response

---

### `GET /valve/valve/is_open`

**Summary:** Is Open
**Description:** Get the current valve status.

Returns
-------
bool
    `True` if the valve is open, `False` if closed.
**Tags:** valve, valve
**Operation ID:** `is_open_valve_valve_is_open_get`

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
