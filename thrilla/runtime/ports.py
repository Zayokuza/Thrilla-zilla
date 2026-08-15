"""Local runtime TCP port inspection."""

import socket
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class PortInspection:
    """Observed state of one TCP host/port."""

    host: str
    port: int
    listening: bool
    bindable: bool



def _can_bind_port(
    host: str,
    port: int,
) -> bool:
    """Return whether a TCP socket can bind to the address."""
    try:
        addresses = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return False

    for family, socktype, protocol, _, address in addresses:
        probe = socket.socket(
            family,
            socktype,
            protocol,
        )

        try:
            probe.bind(address)
            return True
        except OSError:
            continue
        finally:
            probe.close()

    return False


def _validate_port(port: int) -> None:
    """Reject values that cannot represent a TCP service port."""
    if port < 1 or port > 65535:
        raise ValueError(
            "port must be between 1 and 65535"
        )


def inspect_port(
    host: str,
    port: int,
    timeout: float = 0.2,
) -> PortInspection:
    """Inspect whether a TCP service accepts connections."""
    _validate_port(port)

    connection = None

    try:
        connection = socket.create_connection(
            (
                host,
                port,
            ),
            timeout=timeout,
        )
        listening = True
    except OSError:
        listening = False
    finally:
        if connection is not None:
            connection.close()

    return PortInspection(
        host=host,
        port=port,
        listening=listening,
        bindable=_can_bind_port(
            host,
            port,
        ),
    )


def find_available_port(
    host: str,
    ports: Iterable[int],
    timeout: float = 0.2,
) -> Optional[int]:
    """Return the first permitted TCP port that can be bound."""
    for port in ports:
        status = inspect_port(
            host,
            port,
            timeout=timeout,
        )

        if status.bindable:
            return port

    return None
