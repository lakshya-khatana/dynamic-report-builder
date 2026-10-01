"""
Spec §6 'Connector Service': adding a new dialect or file type should mean
adding one class + one line here — nothing else in the codebase should need
to change.
"""

from connectors.base import BaseConnector
from connectors.flatfile import FlatFileConnector
from connectors.rdbms import RDBMSConnector

_REGISTRY: dict[str, type[BaseConnector]] = {
    "postgresql": RDBMSConnector,
    "mysql": RDBMSConnector,
    "mssql": RDBMSConnector,
    "sqlite": RDBMSConnector,
    "flatfile": FlatFileConnector,
}


def get_connector(dialect: str, source_id: str, config: dict) -> BaseConnector:
    try:
        connector_cls = _REGISTRY[dialect]
    except KeyError:
        raise ValueError(f"No connector registered for dialect '{dialect}'") from None
    return connector_cls(source_id=source_id, config=config)
