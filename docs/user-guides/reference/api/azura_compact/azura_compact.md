## Endpoints

### `GET /pump-b90e33/pump/`

**Summary:** Get Metadata
**Description:** Return metadata.
**Tags:** pump-b90e33, pump-b90e33
**Operation ID:** `get_metadata_pump_b90e33_pump__get`

**Responses:**
- `200`: Successful Response

---

### `PUT /pump-b90e33/pump/infuse`

**Summary:** Infuse
**Description:** Start infusion.
**Tags:** pump-b90e33, pump-b90e33
**Operation ID:** `infuse_pump_b90e33_pump_infuse_put`

**Query Parameters:**
- `rate` (string, optional, default = ``)
- `volume` (string, optional, default = ``)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT /pump-b90e33/pump/stop`

**Summary:** Stop
**Description:** Stop pumping.
**Tags:** pump-b90e33, pump-b90e33
**Operation ID:** `stop_pump_b90e33_pump_stop_put`

**Responses:**
- `200`: Successful Response

---

### `GET /pump-b90e33/pump/is-pumping`

**Summary:** Is Pumping
**Description:** Is pump running?
**Tags:** pump-b90e33, pump-b90e33
**Operation ID:** `is_pumping_pump_b90e33_pump_is_pumping_get`

**Responses:**
- `200`: Successful Response

---

### `GET /pump-b90e33/pressure/`

**Summary:** Get Metadata
**Description:** Return metadata.
**Tags:** pump-b90e33, pump-b90e33
**Operation ID:** `get_metadata_pump_b90e33_pressure__get`

**Responses:**
- `200`: Successful Response

---

### `GET /pump-b90e33/pressure/read-pressure`

**Summary:** Read Pressure
**Description:** Read from sensor, result to be expressed in units (optional).
**Tags:** pump-b90e33, pump-b90e33
**Operation ID:** `read_pressure_pump_b90e33_pressure_read_pressure_get`

**Query Parameters:**
- `units` (string, optional, default = `bar`)

**Responses:**
- `200`: Successful Response
- `422`: Validation Error

---

## Components

### `ComponentInfo` (object)

**Required:** hw_device
**Description:** Metadata associated with flowchem components.

**Properties:**
- `hw_device`: object
- `name`: string (default: ``)
- `owl_subclass_of`: string (default: `http://purl.obolibrary.org/obo/OBI_0000968`)

---

### `DeviceInfo` (object)

**Required:** authors, maintainers, manufacturer, model
**Description:** Metadata associated with hardware devices.

**Properties:**
- `authors`: array
- `maintainers`: array
- `manufacturer`: string
- `model`: string
- `additional_info`: object (default: `{}`)
- `backend`: string (default: `flowchem v. 0.1.0a3`)
- `serial_number`: string (default: `unknown`)
- `version`: string (default: ``)

---

### `HTTPValidationError` (object)


**Properties:**
- `detail`: array

---

### `Person` (object)

**Required:** name, email

**Properties:**
- `name`: string
- `email`: string

---

### `ValidationError` (object)

**Required:** loc, msg, type

**Properties:**
- `loc`: array
- `msg`: string
- `type`: string

---
