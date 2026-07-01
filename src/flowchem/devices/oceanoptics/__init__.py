try:
    from .flame import FlameOptical
except ImportError:
    __all__: list[str] = []
else:
    __all__ = ["FlameOptical"]
