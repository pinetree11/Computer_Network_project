from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .client import Peer, logout, parse_users, send_to_peer
from .protocol import encode_message, recv_message


@dataclass(frozen=True)
class ChatMessage:
    sender: str
    body: str
    received_at: float


class WebMessengerState:
    def __init__(
        self,
        user_id: str,
        server_host: str,
        server_port: int,
        listen_host: str,
        listen_port: int,
    ) -> None:
        self.user_id = user_id
        self.server_host = server_host
        self.server_port = server_port
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.peers: dict[str, Peer] = {}
        self.session: dict[str, Peer] = {}
        self.messages: list[ChatMessage] = []
        self.active = True
        self.lock = threading.Lock()

    def start(self) -> None:
        threading.Thread(target=self._listen_for_messages, daemon=True).start()
        self.refresh()

    def refresh(self) -> None:
        self._ensure_active()
        peers = self._request_users()
        with self.lock:
            self.peers = peers
            self.session = {peer_id: peer for peer_id, peer in self.session.items() if peer_id in peers}

    def invite(self, peer_id: str) -> None:
        self._ensure_active()
        with self.lock:
            if peer_id not in self.peers:
                raise ValueError(f"unknown user: {peer_id}")
            self.session[peer_id] = self.peers[peer_id]

    def end_session(self) -> None:
        self._ensure_active()
        with self.lock:
            self.session.clear()

    def send(self, body: str) -> int:
        self._ensure_active()
        with self.lock:
            recipients = list(self.session.values())
        for peer in recipients:
            send_to_peer(peer, self.user_id, body)
        return len(recipients)

    def logout(self) -> None:
        with self.lock:
            if not self.active:
                return
            self.active = False
            self.peers.clear()
            self.session.clear()
        logout(self.server_host, self.server_port, self.user_id)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "user": {
                    "user_id": self.user_id,
                    "ip": self.listen_host,
                    "port": self.listen_port,
                },
                "peers": [asdict(peer) for peer in self.peers.values()],
                "session": [asdict(peer) for peer in self.session.values()],
                "messages": [asdict(message) for message in self.messages],
                "active": self.active,
            }

    def _request_users(self) -> dict[str, Peer]:
        with socket.create_connection((self.server_host, self.server_port)) as conn:
            conn.sendall(
                encode_message(
                    "LOGIN",
                    {"User-Id": self.user_id, "Ip": self.listen_host, "Port": str(self.listen_port)},
                )
            )
            response = recv_message(conn)
        return parse_users(response.body, exclude=self.user_id)

    def _listen_for_messages(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.listen_host, self.listen_port))
            server.listen()
            server.settimeout(1)
            while self.active:
                try:
                    conn, _ = server.accept()
                except TimeoutError:
                    continue
                threading.Thread(target=self._handle_peer_message, args=(conn,), daemon=True).start()

    def _handle_peer_message(self, conn: socket.socket) -> None:
        with conn:
            message = recv_message(conn)
        sender = message.headers.get("From", "unknown")
        chat_message = ChatMessage(sender=sender, body=message.body, received_at=time.time())
        with self.lock:
            if self.active:
                self.messages.append(chat_message)

    def _ensure_active(self) -> None:
        if not self.active:
            raise ValueError("client already quit")


class WebClientHandler(SimpleHTTPRequestHandler):
    state: WebMessengerState

    def do_GET(self) -> None:
        if self.path == "/api/state":
            self._send_json(self.state.snapshot())
            return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/refresh":
                self.state.refresh()
                self._send_json(self.state.snapshot())
            elif self.path == "/api/invite":
                payload = self._read_json()
                self.state.invite(str(payload["user_id"]))
                self._send_json(self.state.snapshot())
            elif self.path == "/api/send":
                payload = self._read_json()
                sent_count = self.state.send(str(payload["body"]))
                self._send_json({"sent_count": sent_count, **self.state.snapshot()})
            elif self.path == "/api/end":
                self.state.end_session()
                self._send_json(self.state.snapshot())
            elif self.path == "/api/logout":
                self.state.logout()
                self._send_json({"ok": True})
            elif self.path == "/api/quit":
                self.state.logout()
                self._send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "not found")
        except (KeyError, ValueError, ConnectionError, OSError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def make_handler(state: WebMessengerState, web_root: Path) -> type[WebClientHandler]:
    class Handler(WebClientHandler):
        pass

    Handler.state = state

    def init(self, *args, **kwargs):
        super(Handler, self).__init__(*args, directory=str(web_root), **kwargs)

    Handler.__init__ = init
    return Handler


def run_web_client(args: argparse.Namespace) -> None:
    state = WebMessengerState(
        user_id=args.id,
        server_host=args.server_host,
        server_port=args.server_port,
        listen_host=args.listen_host,
        listen_port=args.listen_port,
    )
    state.start()

    web_root = Path(__file__).resolve().parents[2] / "web"
    handler = make_handler(state, web_root)
    with ThreadingHTTPServer((args.web_host, args.web_port), handler) as server:
        print(f"web messenger for {args.id}: http://{args.web_host}:{args.web_port}")
        server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Web UI client for the messenger project")
    parser.add_argument("--id", required=True)
    parser.add_argument("--server-host", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=9000)
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--web-host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    run_web_client(parse_args())
