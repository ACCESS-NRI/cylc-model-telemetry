from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("access-ram3-telemetry")
except PackageNotFoundError:
    __version__ = "unknown"