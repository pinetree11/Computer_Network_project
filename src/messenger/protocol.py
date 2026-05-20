from __future__ import annotations

from dataclasses import dataclass


HEADER_END = b"\r\n\r\n"


@dataclass(frozen=True)
class Message:
    method: str
    headers: dict[str, str]
    body: str = ""


def encode_message(method: str, headers: dict[str, str] | None = None, body: str = "") -> bytes:
    fields = {"Content-Length": str(len(body.encode("utf-8")))}
    if headers:
        fields.update(headers)

    lines = [f"METHOD {method}"]
    lines.extend(f"{key}: {value}" for key, value in fields.items())
    head = "\r\n".join(lines).encode("utf-8")
    return head + HEADER_END + body.encode("utf-8")


def decode_message(data: bytes) -> Message:
    head, _, raw_body = data.partition(HEADER_END)
    lines = head.decode("utf-8").splitlines()
    if not lines or not lines[0].startswith("METHOD "):
        raise ValueError("invalid message start line")

    method = lines[0].removeprefix("METHOD ").strip()
    headers: dict[str, str] = {}
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"invalid header line: {line}")
        headers[key.strip()] = value.strip()

    length = int(headers.get("Content-Length", "0"))
    body = raw_body[:length].decode("utf-8")
    return Message(method=method, headers=headers, body=body)


def recv_message(sock) -> Message:
    data = bytearray()
    while HEADER_END not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("connection closed while reading headers")
        data.extend(chunk)

    head, _, rest = bytes(data).partition(HEADER_END)
    headers = decode_message(head + HEADER_END).headers
    length = int(headers.get("Content-Length", "0"))

    body = bytearray(rest)
    while len(body) < length:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("connection closed while reading body")
        body.extend(chunk)

    return decode_message(head + HEADER_END + bytes(body[:length]))
