## Endpoints

### `GET /my-knauer-autosampler/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-knauer-autosampler
**Operation ID:** `get_device_info_my_knauer_autosampler__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauer-autosampler/gantry3D/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_component_info_my_knauer_autosampler_gantry3D__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/gantry3D/set_x_position`

**Summary:** Set X Position
**Description:** Set the position of the X-axis.

Args:
    position (float | str): Target position for the X-axis.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_x_position_my_knauer_autosampler_gantry3D_set_x_position_put`

**Query Parameters:**
- `position` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauer-autosampler/gantry3D/set_y_position`

**Summary:** Set Y Position
**Description:** Set the position of the Y-axis.

Args:
    position (float | str): Target position for the Y-axis.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_y_position_my_knauer_autosampler_gantry3D_set_y_position_put`

**Query Parameters:**
- `position` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauer-autosampler/gantry3D/set_z_position`

**Summary:** Set Z Position
**Description:** Move the 3D gantry along the Z axis.

direction (str):
    DOWN
    UP
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_z_position_my_knauer_autosampler_gantry3D_set_z_position_put`

**Query Parameters:**
- `position` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauer-autosampler/gantry3D/reset_errors`

**Summary:** Reset Errors
**Description:** Resets AS error
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `reset_errors_my_knauer_autosampler_gantry3D_reset_errors_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/gantry3D/needle_position`

**Summary:** Set Needle Position
**Description:** Move the needle to one of the predefined positions.

Argument:
    position (str):
                WASH
                WASTE
                EXCHANGE
                TRANSPORT
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_needle_position_my_knauer_autosampler_gantry3D_needle_position_put`

**Query Parameters:**
- `position` (string, optional, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauer-autosampler/gantry3D/set_xy_position`

**Summary:** Set Xy Position
**Description:** Move the 3D gantry to the specified (x, y) coordinate of a specific plate.

plate (str):
            LEFT_PLATE
            RIGHT_PLATE

column: ["a", "b", "c", "d", "e", "f"].
row: [1, 2, 3, 4, 5, 6, 7, 8]
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_xy_position_my_knauer_autosampler_gantry3D_set_xy_position_put`

**Query Parameters:**
- `row` (integer, required, default = ``)
- `column` (string, required, default = ``)
- `tray` (string, optional, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauer-autosampler/gantry3D/connect_to_position`

**Summary:** Connect To Position
**Description:** Move the 3D gantry to the specified (x, y) coordinate of a specific plate and connects to it.

plate (str):
            LEFT_PLATE
            RIGHT_PLATE

column: ["a", "b", "c", "d", "e", "f"].
row: [1, 2, 3, 4, 5, 6, 7, 8]
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `connect_to_position_my_knauer_autosampler_gantry3D_connect_to_position_put`

**Query Parameters:**
- `row` (integer, required, default = ``)
- `column` (string, required, default = ``)
- `tray` (string, optional, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauer-autosampler/pump/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_component_info_my_knauer_autosampler_pump__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/pump/infuse`

**Summary:** Infuse
**Description:** Dispense with built in syringe.
Args:
    volume: volume to dispense in mL

Returns: None
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `infuse_my_knauer_autosampler_pump_infuse_put`

**Query Parameters:**
- `rate` (string, optional, default = ``)
- `volume` (string, optional, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauer-autosampler/pump/stop`

**Summary:** Stop
**Description:** Stop pumping.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `stop_my_knauer_autosampler_pump_stop_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauer-autosampler/pump/is-pumping`

**Summary:** Is Pumping
**Description:** "Checks if Syringe or syringe valve is running
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `is_pumping_my_knauer_autosampler_pump_is_pumping_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/pump/withdraw`

**Summary:** Withdraw
**Description:** Aspirate with built-in syringe.
Args:
    rate: Volume flow rate ml/min
    volume: volume to aspirate in mL

Returns: None
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `withdraw_my_knauer_autosampler_pump_withdraw_put`

**Query Parameters:**
- `rate` (string, optional, default = ``)
- `volume` (string, optional, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauer-autosampler/syringe_valve/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_component_info_my_knauer_autosampler_syringe_valve__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauer-autosampler/syringe_valve/position`

**Summary:** Get Position
**Description:** Get current valve position.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_position_my_knauer_autosampler_syringe_valve_position_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/syringe_valve/position`

**Summary:** Set Position
**Description:** Move valve to position, which connects named ports
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_position_my_knauer_autosampler_syringe_valve_position_put`

**Query Parameters:**
- `connect` (string, optional, default = ``)
- `disconnect` (string, optional, default = ``)
- `ambiguous_switching` (string, optional, default = `False`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauer-autosampler/syringe_valve/connections`

**Summary:** Connections
**Description:** Get the list of all available positions for this valve.
This mainly has informative purpose
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `connections_my_knauer_autosampler_syringe_valve_connections_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauer-autosampler/syringe_valve/monitor_position`

**Summary:** Get Monitor Position
**Description:** Gets the current valve position.

Returns:
    position (str): The current position:
    NEEDLE (position 0).
    WASH (position 1).
    WASH_PORT2 (position 2).
    WASTE (position 3).
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_monitor_position_my_knauer_autosampler_syringe_valve_monitor_position_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/syringe_valve/monitor_position`

**Summary:** Set Monitor Position
**Description:** Set the valve to a specified position.

Args:
    position (str): The desired position:
    NEEDLE (position 0).
    WASH (position 1).
    WASH_PORT2 (position 2).
    WASTE (position 3).
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_monitor_position_my_knauer_autosampler_syringe_valve_monitor_position_put`

**Query Parameters:**
- `position` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauer-autosampler/injection_valve/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_component_info_my_knauer_autosampler_injection_valve__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauer-autosampler/injection_valve/position`

**Summary:** Get Position
**Description:** Get current valve position.
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_position_my_knauer_autosampler_injection_valve_position_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/injection_valve/position`

**Summary:** Set Position
**Description:** Move valve to position, which connects named ports
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_position_my_knauer_autosampler_injection_valve_position_put`

**Query Parameters:**
- `connect` (string, optional, default = ``)
- `disconnect` (string, optional, default = ``)
- `ambiguous_switching` (string, optional, default = `False`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauer-autosampler/injection_valve/connections`

**Summary:** Connections
**Description:** Get the list of all available positions for this valve.
This mainly has informative purpose
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `connections_my_knauer_autosampler_injection_valve_connections_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauer-autosampler/injection_valve/monitor_position`

**Summary:** Get Monitor Position
**Description:** Gets the current valve position.

Returns:
    position (str):
        LOAD (position 0)
        INJECT (position 1)
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `get_monitor_position_my_knauer_autosampler_injection_valve_monitor_position_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauer-autosampler/injection_valve/monitor_position`

**Summary:** Set Monitor Position
**Description:** Set the valve to a specified position.

Args:
    position (str):
    LOAD (position 0)
    INJECT (position 1)
**Tags:** my-knauer-autosampler, my-knauer-autosampler
**Operation ID:** `set_monitor_position_my_knauer_autosampler_injection_valve_monitor_position_put`

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
