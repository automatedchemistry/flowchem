## Endpoints

### `GET /my-ebpr/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-ebpr
**Operation ID:** `get_device_info_my_ebpr__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-ebpr/pressure/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `get_component_info_my_ebpr_pressure__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-ebpr/pressure/is-reachable`

**Summary:** Is Reachable
**Description:** Return ONLINE if the pressure controller responds to a pressure query.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `is_reachable_my_ebpr_pressure_is_reachable_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-ebpr/pressure/is-idle`

**Summary:** Is Idle
**Description:** Check whether any in-progress physical action has finished.

Subclasses should override this with a real hardware busy/idle probe where
available. Returns True by default when completion can't be verified.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `is_idle_my_ebpr_pressure_is_idle_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-ebpr/pressure/pressure`

**Summary:** Set Pressure
**Description:** Set the target pressure (default unit mbar if none given).
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `set_pressure_my_ebpr_pressure_pressure_put`

**Query Parameters:**
- `pressure` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-ebpr/pressure/pressure`

**Summary:** Get Pressure
**Description:** Get the current pressure in bar.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `get_pressure_my_ebpr_pressure_pressure_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-ebpr/pressure/power-on`

**Summary:** Power On
**Description:** Turn on pressure control.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `power_on_my_ebpr_pressure_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-ebpr/pressure/power-off`

**Summary:** Power Off
**Description:** Turn off pressure control.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `power_off_my_ebpr_pressure_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-ebpr/pressure/target-reached`

**Summary:** Is Target Reached
**Description:** Check if the current pressure is within the eBPR's documented resolution of the set point.
**Tags:** my-ebpr, my-ebpr
**Operation ID:** `is_target_reached_my_ebpr_pressure_target_reached_get`

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

---
