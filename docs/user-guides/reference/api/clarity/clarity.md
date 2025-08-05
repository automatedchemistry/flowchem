## Endpoints

### `GET /my-clarity/`

**Summary:** Get Device Info
**Description:** 
**Tags:** my-clarity
**Operation ID:** `get_device_info_fake_device__get`

**Responses:**
- `200`: Successful Response

---

### `GET /my-clarity/clarity/`

**Summary:** Get Component Info
**Description:** Return metadata.
**Tags:** my-clarity, my-clarity
**Operation ID:** `get_component_info_fake_device_clarity__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /my-clarity/clarity/run-sample`

**Summary:** Run Sample
**Description:** Run an analysis on the instrument with the specified sample and method.

Note that it takes at least 2 sec until the run actually starts (depending on instrument configuration).
While the export of the chromatogram in e.g. ASCII format can be achieved programmatically via the CLI, the best
solution is to enable automatic data export for all runs of the HPLC as the chromatogram will be automatically
exported as soon as the run is finished.

Parameters:
-----------
sample_name : str
    The name of the sample to be run.
method_name : str
    The name of the method file to be used.

Returns:
--------
bool
    True if the sample was successfully run, False otherwise.
**Tags:** my-clarity, my-clarity
**Operation ID:** `run_sample_fake_device_clarity_run_sample_put`

**Query Parameters:**
- `sample-name` (string, required, default = ``)
- `method-name` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-clarity/clarity/send-method`

**Summary:** Send Method
**Description:** Set the HPLC method using a file with a .MET extension.

Ensure that the 'Send Method to Instrument' option is selected in the Method Sending Options dialog in
System Configuration.

Parameters:
-----------
method_name : str
    The name of the method file to be sent.

Returns:
--------
bool
    True if the method was successfully sent, False otherwise.
**Tags:** my-clarity, my-clarity
**Operation ID:** `send_method_fake_device_clarity_send_method_put`

**Query Parameters:**
- `method-name` (string, required, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /my-clarity/clarity/exit`

**Summary:** Exit
**Description:** Exit the ClarityChrom application.

Returns:
--------
bool
    True if the exit command was successfully executed, False otherwise.
**Tags:** my-clarity, my-clarity
**Operation ID:** `exit_fake_device_clarity_exit_put`

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
