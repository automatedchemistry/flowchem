"""Various utility functions for the Magritek device."""

import ctypes
from collections.abc import Callable
from pathlib import Path

from loguru import logger

from flowchem.utils.exceptions import InvalidConfigurationError


def get_my_docs_path() -> Path:
    """Get my docs path on Windows.

    Spinsolve control software is only available on Windows, so lack of cross-platform support is unavoidable.
    XSD and XML schema are installed in my documents, whose location, if custom, can be obtained as follows.
    """
    # From https://stackoverflow.com/questions/6227590

    csidl_personal = 5  # My Documents (csidl = constant special item ID list)
    shgfp_type_current = (
        0  # Get current, not default value (shgfp = shell get folder path)
    )
    buf = ctypes.create_unicode_buffer(2000)
    ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore
        None,
        csidl_personal,
        None,
        shgfp_type_current,
        buf,
    )
    return Path(buf.value)


def create_folder_mapper(
    remote_root: str | Path,
    local_root: str | Path,
) -> Callable[[Path | str], Path]:
    """Return a function that converts path relative to remote_root to their corresponding on local_root.

    Used when using spinsolve on a remote PC to share the result data via a remotely mounted network drive.
    """

    def folder_mapper(path_to_be_translated: Path | str):
        """Convert remote path to the corresponding local location, or None + warning if not possible."""
        # Ensures it is a Path object
        if isinstance(path_to_be_translated, str):
            path_to_be_translated = Path(path_to_be_translated)

        nonlocal remote_root, local_root
        remote_root = Path(remote_root)
        local_root = Path(local_root)
        # If relative translate is not error
        # NOTE: Path.is_relative_to() is available from Py 3.9 only. NBD as this is not often used.
        if not path_to_be_translated.is_relative_to(remote_root):
            logger.exception(
                f"Cannot translate remote path {path_to_be_translated} to a local path!",
            )
            raise InvalidConfigurationError(
                f"Cannot translate remote path {path_to_be_translated} to a local path!"
                f"{path_to_be_translated} is not relative to {remote_root}"
            )

        suffix = path_to_be_translated.relative_to(remote_root)
        return local_root / suffix

    return folder_mapper
