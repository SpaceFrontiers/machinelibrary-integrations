from __future__ import annotations

from machinelibrary import AsyncMachineLibrary, MachineLibrary
from pydantic import SecretStr

INTEGRATION = "langchain"


def sync_client(api_key: SecretStr | None) -> MachineLibrary:
    return MachineLibrary(api_key.get_secret_value() if api_key else None, integration=INTEGRATION)


def async_client(api_key: SecretStr | None) -> AsyncMachineLibrary:
    return AsyncMachineLibrary(
        api_key.get_secret_value() if api_key else None, integration=INTEGRATION
    )
