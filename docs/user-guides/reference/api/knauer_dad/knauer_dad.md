## Endpoints

### `GET /my-knauerdad/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-knauerdad
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/d2/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_component_info_fake_device_d2__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/d2/power-on`

**Summary:** Power On
**Description:** Turn the lamp power on.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_on_fake_device_d2_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/d2/power-off`

**Summary:** Power Off
**Description:** Turn the lamp power off.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_off_fake_device_d2_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/d2/lamp_status`

**Summary:** Get Lamp
**Description:** Get the status of the lamp.

Returns:
    str: The status of the lamp.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_lamp_fake_device_d2_lamp_status_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/d2/status`

**Summary:** Get Status
**Description:** Get the status of the instrument.

Returns:
    str: The status of the instrument.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_status_fake_device_d2_status_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/hal/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_component_info_fake_device_hal__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/hal/power-on`

**Summary:** Power On
**Description:** Turn the lamp power on.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_on_fake_device_hal_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/hal/power-off`

**Summary:** Power Off
**Description:** Turn the lamp power off.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_off_fake_device_hal_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/hal/lamp_status`

**Summary:** Get Lamp
**Description:** Get the status of the lamp.

Returns:
    str: The status of the lamp.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_lamp_fake_device_hal_lamp_status_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/hal/status`

**Summary:** Get Status
**Description:** Get the status of the instrument.

Returns:
    str: The status of the instrument.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_status_fake_device_hal_status_get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/channel1/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_component_info_fake_device_channel1__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel1/power-on`

**Summary:** Power On
**Description:** Check the lamp status.

Returns:
    str: The status of both the D2 and halogen lamps.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_on_fake_device_channel1_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel1/power-off`

**Summary:** Power Off
**Description:** Deactivate the measurement channel.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_off_fake_device_channel1_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/channel1/acquire-signal`

**Summary:** Acquire Signal
**Description:** Acquire a signal from the sensor, result to be expressed in % (optional).

Returns:
    float: The acquired signal.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `acquire_signal_fake_device_channel1_acquire_signal_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel1/calibration`

**Summary:** Calibrate Zero
**Description:** re-calibrate the sensors to their factory zero points.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `calibrate_zero_fake_device_channel1_calibration_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel1/set-wavelength`

**Summary:** Set Wavelength
**Description:** Set the acquisition wavelength.

Args:
    wavelength (int): The desired wavelength in nm (0-999 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_wavelength_fake_device_channel1_set_wavelength_put`

**Query Parameters:**
- `wavelength` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel1/set-integration-time`

**Summary:** Set Integration Time
**Description:** Set the integration time.

Args:
    int_time (int): The desired integration time in ms (10 - 2000 ms).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_integration_time_fake_device_channel1_set_integration_time_put`

**Query Parameters:**
- `int_time` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel1/set-bandwidth`

**Summary:** Set Bandwidth
**Description:** Set the bandwidth.

Args:
    bandwidth (int): The desired bandwidth in nm (4 to 25 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_bandwidth_fake_device_channel1_set_bandwidth_put`

**Query Parameters:**
- `bandwidth` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauerdad/channel2/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_component_info_fake_device_channel2__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel2/power-on`

**Summary:** Power On
**Description:** Check the lamp status.

Returns:
    str: The status of both the D2 and halogen lamps.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_on_fake_device_channel2_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel2/power-off`

**Summary:** Power Off
**Description:** Deactivate the measurement channel.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_off_fake_device_channel2_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/channel2/acquire-signal`

**Summary:** Acquire Signal
**Description:** Acquire a signal from the sensor, result to be expressed in % (optional).

Returns:
    float: The acquired signal.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `acquire_signal_fake_device_channel2_acquire_signal_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel2/calibration`

**Summary:** Calibrate Zero
**Description:** re-calibrate the sensors to their factory zero points.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `calibrate_zero_fake_device_channel2_calibration_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel2/set-wavelength`

**Summary:** Set Wavelength
**Description:** Set the acquisition wavelength.

Args:
    wavelength (int): The desired wavelength in nm (0-999 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_wavelength_fake_device_channel2_set_wavelength_put`

**Query Parameters:**
- `wavelength` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel2/set-integration-time`

**Summary:** Set Integration Time
**Description:** Set the integration time.

Args:
    int_time (int): The desired integration time in ms (10 - 2000 ms).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_integration_time_fake_device_channel2_set_integration_time_put`

**Query Parameters:**
- `int_time` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel2/set-bandwidth`

**Summary:** Set Bandwidth
**Description:** Set the bandwidth.

Args:
    bandwidth (int): The desired bandwidth in nm (4 to 25 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_bandwidth_fake_device_channel2_set_bandwidth_put`

**Query Parameters:**
- `bandwidth` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauerdad/channel3/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_component_info_fake_device_channel3__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel3/power-on`

**Summary:** Power On
**Description:** Check the lamp status.

Returns:
    str: The status of both the D2 and halogen lamps.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_on_fake_device_channel3_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel3/power-off`

**Summary:** Power Off
**Description:** Deactivate the measurement channel.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_off_fake_device_channel3_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/channel3/acquire-signal`

**Summary:** Acquire Signal
**Description:** Acquire a signal from the sensor, result to be expressed in % (optional).

Returns:
    float: The acquired signal.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `acquire_signal_fake_device_channel3_acquire_signal_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel3/calibration`

**Summary:** Calibrate Zero
**Description:** re-calibrate the sensors to their factory zero points.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `calibrate_zero_fake_device_channel3_calibration_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel3/set-wavelength`

**Summary:** Set Wavelength
**Description:** Set the acquisition wavelength.

Args:
    wavelength (int): The desired wavelength in nm (0-999 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_wavelength_fake_device_channel3_set_wavelength_put`

**Query Parameters:**
- `wavelength` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel3/set-integration-time`

**Summary:** Set Integration Time
**Description:** Set the integration time.

Args:
    int_time (int): The desired integration time in ms (10 - 2000 ms).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_integration_time_fake_device_channel3_set_integration_time_put`

**Query Parameters:**
- `int_time` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel3/set-bandwidth`

**Summary:** Set Bandwidth
**Description:** Set the bandwidth.

Args:
    bandwidth (int): The desired bandwidth in nm (4 to 25 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_bandwidth_fake_device_channel3_set_bandwidth_put`

**Query Parameters:**
- `bandwidth` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET /my-knauerdad/channel4/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `get_component_info_fake_device_channel4__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel4/power-on`

**Summary:** Power On
**Description:** Check the lamp status.

Returns:
    str: The status of both the D2 and halogen lamps.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_on_fake_device_channel4_power_on_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel4/power-off`

**Summary:** Power Off
**Description:** Deactivate the measurement channel.

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `power_off_fake_device_channel4_power_off_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-knauerdad/channel4/acquire-signal`

**Summary:** Acquire Signal
**Description:** Acquire a signal from the sensor, result to be expressed in % (optional).

Returns:
    float: The acquired signal.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `acquire_signal_fake_device_channel4_acquire_signal_get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel4/calibration`

**Summary:** Calibrate Zero
**Description:** re-calibrate the sensors to their factory zero points.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `calibrate_zero_fake_device_channel4_calibration_put`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-knauerdad/channel4/set-wavelength`

**Summary:** Set Wavelength
**Description:** Set the acquisition wavelength.

Args:
    wavelength (int): The desired wavelength in nm (0-999 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_wavelength_fake_device_channel4_set_wavelength_put`

**Query Parameters:**
- `wavelength` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel4/set-integration-time`

**Summary:** Set Integration Time
**Description:** Set the integration time.

Args:
    int_time (int): The desired integration time in ms (10 - 2000 ms).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_integration_time_fake_device_channel4_set_integration_time_put`

**Query Parameters:**
- `int_time` (integer, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-knauerdad/channel4/set-bandwidth`

**Summary:** Set Bandwidth
**Description:** Set the bandwidth.

Args:
    bandwidth (int): The desired bandwidth in nm (4 to 25 nm).

Returns:
    str: The response from the hardware device.
**Tags:** my-knauerdad, my-knauerdad
**Operation ID:** `set_bandwidth_fake_device_channel4_set_bandwidth_put`

**Query Parameters:**
- `bandwidth` (integer, required, default = ``)

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
