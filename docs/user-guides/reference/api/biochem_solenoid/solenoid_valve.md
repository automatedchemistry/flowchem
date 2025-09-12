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

This method energizes the solenoid, switching the valve to the
"open" state, allowing flow through the channel.
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

### `GET /valve/valve/status`

**Summary:** Status
**Description:** Get the current valve status.

Returns
-------
bool
    `True` if the valve is open, `False` if closed.
**Tags:** valve, valve
**Operation ID:** `status_valve_valve_status_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /valve/valve/switch_to_low_power`

**Summary:** Switch To Low Power
**Description:** Schedule switching the valve to low-power mode.

This reduces the risk of overheating by lowering
the power supplied to the solenoid after the
given delay (in seconds).

Parameters
----------
after : float
    Time in seconds after which the solenoid should enter
    low-power mode. Use `-1` to disable low-power switching.

Returns
-------
None
**Tags:** valve, valve
**Operation ID:** `switch_to_low_power_valve_valve_switch_to_low_power_put`

**Query Parameters:**
- `after` (number, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---