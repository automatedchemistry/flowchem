## Endpoints

### `GET /my-runze-valve/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-runze-valve
**Operation ID:** `get_device_info_my_runze_valve__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-runze-valve/distribution-valve/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-runze-valve, my-runze-valve
**Operation ID:** `get_component_info_my_runze_valve_distribution_valve__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-runze-valve/distribution-valve/position`

**Summary:** Get Position
**Description:** Get current valve position.
**Tags:** my-runze-valve, my-runze-valve
**Operation ID:** `get_position_my_runze_valve_distribution_valve_position_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-runze-valve/distribution-valve/position`

**Summary:** Set Position
**Description:** Move valve to position, which connects named ports
**Tags:** my-runze-valve, my-runze-valve
**Operation ID:** `set_position_my_runze_valve_distribution_valve_position_put`

**Query Parameters:**
- `connect` (string, optional, default = ``)
- `disconnect` (string, optional, default = ``)
- `ambiguous_switching` (string, optional, default = `False`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-runze-valve/distribution-valve/connections`

**Summary:** Connections
**Description:** Get the list of all available positions for this valve.
This mainly has informative purpose
**Tags:** my-runze-valve, my-runze-valve
**Operation ID:** `connections_my_runze_valve_distribution_valve_connections_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-runze-valve/distribution-valve/monitor_position`

**Summary:** Get Monitor Position
**Description:** Get current valve position.
**Tags:** my-runze-valve, my-runze-valve
**Operation ID:** `get_monitor_position_my_runze_valve_distribution_valve_monitor_position_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-runze-valve/distribution-valve/monitor_position`

**Summary:** Set Monitor Position
**Description:** Move valve to position.
**Tags:** my-runze-valve, my-runze-valve
**Operation ID:** `set_monitor_position_my_runze_valve_distribution_valve_monitor_position_put`

**Query Parameters:**
- `position` (string, required, default = ``)

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

### `ValveInfo` (object)

**Required:** ports, positions
**Description:** ports: an attribute representing the available ports on the stator
positions: an attribute mapping implicit, tacit numbers as keys to the stator ports that are connected at this
            position

**Properties:**
- `ports`: array
- `positions`: object

---
