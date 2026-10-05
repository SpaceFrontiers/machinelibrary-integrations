"""Machine Library client: citable search for AI agents and research tools.

>>> from machinelibrary import MachineLibrary
>>> ml = MachineLibrary()  # reads MACHINELIBRARY_API_KEY
>>> hits = ml.search("CRISPR off-target effects in vivo", limit=5)
>>> doc = ml.fetch_document(hits[0].source_uri)
"""

from machinelibrary.client import (
    AsyncMachineLibrary,
    AuthenticationError,
    InsufficientCreditError,
    MachineLibrary,
    MachineLibraryError,
)
from machinelibrary.models import Document, Passage, SearchHit

__all__ = [
    "AsyncMachineLibrary",
    "AuthenticationError",
    "Document",
    "InsufficientCreditError",
    "MachineLibrary",
    "MachineLibraryError",
    "Passage",
    "SearchHit",
]
