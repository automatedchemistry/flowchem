## Endpoints

### `GET /my-icir/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-icir
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-icir/ir-control/`

**Summary:** Get Component Info
**Description:** Retrieve the component's metadata.

This endpoint provides information about the component, such as its name and associated hardware device.

Returns:
--------
ComponentInfo
    Metadata about the component.
**Tags:** my-icir, my-icir
**Operation ID:** `get_component_info_fake_device_ir_control__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-icir/ir-control/acquire-spectrum`

**Summary:** Acquire Spectrum
**Description:** Acquire an IR spectrum.

Args:
    treated (bool): If True, perform background subtraction. If False, return a raw scan.

Returns:
    IRSpectrum: The acquired IR spectrum.
**Tags:** my-icir, my-icir
**Operation ID:** `acquire_spectrum_fake_device_ir_control_acquire_spectrum_put`

**Query Parameters:**
- `treated` (boolean, optional, default = `True`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-icir/ir-control/stop`

**Summary:** Stop
**Description:** Stop the ongoing IR experiment.

Returns:
    bool: True if the experiment was successfully stopped, False otherwise.
**Tags:** my-icir, my-icir
**Operation ID:** `stop_fake_device_ir_control_stop_put`

**Responses:**
- `200`: Successful Response

---

### `GET /my-icir/ir-control/spectrum-count`

**Summary:** Spectrum Count
**Description:** Get the count of acquired spectra.

Returns:
    int: The number of spectra acquired. Returns -1 if the count is None.
**Tags:** my-icir, my-icir
**Operation ID:** `spectrum_count_fake_device_ir_control_spectrum_count_get`

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

### `IRSpectrum` (object)

**Required:** wavenumber, intensity
**Description:** IR spectrum class.

Consider rampy for advance features (baseline fit, etc.)
See e.g. https://github.com/charlesll/rampy/blob/master/examples/baseline_fit.ipynb

**Properties:**
- `wavenumber`: array
- `intensity`: array

---

### `ValidationError` (object)

**Required:** loc, msg, type

**Properties:**
- `loc`: array
- `msg`: string
- `type`: string

---
