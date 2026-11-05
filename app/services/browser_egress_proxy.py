"""Minimal HTTPS CONNECT egress gateway with DNS pinning and public-IP checks.

Expose this service only on the private browser Docker network. Attach the
container to exactly one separate egress network as its outbound route; do not
publish its port on the host. It permits CONNECT :443 only.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import socket
from urllib.parse import urlsplit

LOG = logging.getLogger("nexus.browser-egress")
MAX_HEADER = 8192
IDLE_TIMEOUT = 300
MAX_CONNECTIONS = 32


def _valid_domain(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 253:
        return False
    return all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in value.split(".")
    )


def load_allowlist(value: str) -> frozenset[str]:
    domains = set()
    for item in value.split(","):
        domain = item.strip().lower().rstrip(".")
        if not _valid_domain(domain):
            raise ValueError("NEXUS_EGRESS_ALLOWED_DOMAINS contains an invalid domain")
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            pass
        else:
            raise ValueError("NEXUS_EGRESS_ALLOWED_DOMAINS must contain DNS names, not IP literals")
        domains.add(domain)
    if not domains:
        raise ValueError("NEXUS_EGRESS_ALLOWED_DOMAINS must not be empty")
    return frozenset(domains)


def host_allowed(host: str, allowed: frozenset[str]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


async def resolve_public(host: str) -> list[tuple[int, str]]:
    loop = asyncio.get_running_loop()
    try:
        records = await asyncio.wait_for(
            loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM), timeout=5
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise ValueError("destination DNS resolution failed") from exc
    addresses = []
    for family, _type, _proto, _canonname, sockaddr in records:
        address = ipaddress.ip_address(sockaddr[0])
        if not address.is_global:
            raise ValueError("destination resolved to a non-public IP address")
        item = (family, str(address))
        if item not in addresses:
            addresses.append(item)
    if not addresses:
        raise ValueError("destination has no public IP address")
    return addresses


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    total = 0
    while True:
        data = await asyncio.wait_for(reader.read(65536), timeout=IDLE_TIMEOUT)
        if not data:
            break
        total += len(data)
        if total > 2_147_483_648:
            break
        writer.write(data)
        await writer.drain()


async def tunnel(client_reader, client_writer, remote_reader, remote_writer):
    tasks = [
        asyncio.create_task(_pipe(client_reader, remote_writer)),
        asyncio.create_task(_pipe(remote_reader, client_writer)),
    ]
    try:
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*done, *pending, return_exceptions=True)
    finally:
        remote_writer.close()
        client_writer.close()
        await asyncio.gather(
            remote_writer.wait_closed(), client_writer.wait_closed(),
            return_exceptions=True,
        )


class EgressProxy:
    def __init__(self, allowed_domains: frozenset[str]):
        self.allowed_domains = allowed_domains
        self.semaphore = asyncio.Semaphore(MAX_CONNECTIONS)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        async with self.semaphore:
            remote_writer = None
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=5)
                if not line:
                    return
                if len(line) > 2048:
                    raise ValueError("CONNECT request line too large")
                parts = line.decode("ascii", errors="strict").strip().split()
                if len(parts) != 3 or parts[0].upper() != "CONNECT" or parts[2] not in {"HTTP/1.0", "HTTP/1.1"}:
                    raise ValueError("only HTTPS CONNECT is supported")
                authority = parts[1]
                if authority.count(":") != 1:
                    raise ValueError("invalid CONNECT authority")
                raw_host, raw_port = authority.rsplit(":", 1)
                host = raw_host.encode("idna").decode("ascii").lower().rstrip(".")
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    pass
                else:
                    raise ValueError("IP-literal destinations are forbidden")
                if raw_port != "443" or not host_allowed(host, self.allowed_domains):
                    raise ValueError("destination is not allowlisted")
                if not _valid_domain(host):
                    raise ValueError("invalid destination hostname")
                header_bytes = 0
                while True:
                    header = await asyncio.wait_for(reader.readline(), timeout=5)
                    header_bytes += len(header)
                    if header_bytes > MAX_HEADER:
                        raise ValueError("CONNECT headers too large")
                    if header in {b"\r\n", b"\n", b""}:
                        break
                addresses = await resolve_public(host)
                # Connect directly to a validated numeric IP. No second DNS
                # lookup occurs between validation and the TCP connection.
                last_error = None
                for family, address in addresses:
                    try:
                        remote_reader, remote_writer = await asyncio.wait_for(
                            asyncio.open_connection(address, 443, family=family), timeout=8
                        )
                        break
                    except (OSError, asyncio.TimeoutError) as exc:
                        last_error = exc
                else:
                    raise ValueError("no validated destination IP accepted a connection") from last_error
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()
                await tunnel(reader, writer, remote_reader, remote_writer)
                remote_writer = None
            except Exception as exc:
                LOG.warning("blocked/failed CONNECT: %s", type(exc).__name__)
                try:
                    writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
                    await writer.drain()
                except Exception:
                    pass
            finally:
                if remote_writer is not None:
                    remote_writer.close()
                    await remote_writer.wait_closed()
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()


async def main():
    if os.getenv("NEXUS_EGRESS_PROXY_MODE") != "allowlist-v1":
        raise SystemExit("NEXUS_EGRESS_PROXY_MODE must be allowlist-v1")
    allowed = load_allowlist(os.getenv("NEXUS_EGRESS_ALLOWED_DOMAINS", ""))
    server = await asyncio.start_server(
        EgressProxy(allowed).handle, "0.0.0.0",  # nosec B104: private Docker network only; no host port is published
        int(os.getenv("NEXUS_EGRESS_PROXY_PORT", "3128")),
        limit=MAX_HEADER,
    )
    LOG.info("HTTPS CONNECT egress proxy ready for %d allowlisted domains", len(allowed))
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    asyncio.run(main())
