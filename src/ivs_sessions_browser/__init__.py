# --- version (managed by setuptools-scm) ---
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0"

# --- main entry point (used by pyproject.toml [project.scripts]) ---
def main() -> None:
    """CLI entry point."""
    # for now just a simple demo, later wire this to SessionBrowser
    from .get_data_from_url import GetDataFromURL

    url = "https://ivscc.gsfc.nasa.gov/sessions/2025/"
    fetcher = GetDataFromURL(url)
    data = fetcher.fetch()
    print(f"Downloaded {len(data)} bytes from {url}")

# --- re-exports for convenience ---
from .get_data_from_url import GetDataFromURL

__all__ = [
    "__version__",
    "main",
    "GetDataFromURL",
]
