from pydantic import AnyHttpUrl, BaseModel, NameEmail

from flowchem import __version__


class DeviceInfo(BaseModel):
    """Metadata associated with hardware devices."""

    manufacturer: str = ""
    model: str = ""
    version: str = ""
    serial_number: str | int = "unknown"
    id: str | None = None  # Set in the config file, tracks which physical unit this is
    components: dict[str, AnyHttpUrl] = {}
    backend: str = f"flowchem v. {__version__}"
    authors: list[NameEmail] = []
    additional_info: dict = {}
