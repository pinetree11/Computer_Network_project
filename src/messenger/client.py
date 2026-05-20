from __future__ import annotations

import argparse
import json
import socket
import threading
from dataclasses import dataclass

from .protocol import encode_message, recv_message


@dataclass(frozen=True)
class Peer:
    user_id: str
    ip: str
    port: int


def request_users(server_host: str, server_port: int, user_id: str, listen_host: str, listen_port: int) -> dict[str, Peer]:
    with socket.create_connection((server_host, server_port)) as conn:
        conn.sendall(
            encode_message(
                "LOGIN",
                {"User-Id": user_id, "Ip": listen_host, "Port": str(listen_port)},
            )
        )
        response = recv_message(conn)
    return parse_users(response.body, exclude=user_id)


def logout(server_host: str, server_port: int, user_id: str) -> None:
    with socket.create_connection((server_host, server_port)) as conn:
        conn.sendall(encode_message("LOGOUT", {"User-Id": user_id}))
        recv_message(conn)


def parse_users(body: str, exclude: str) -> dict[str, Peer]:
    peers = {}
    for item in json.loads(body):
        if item["user_id"] != exclude:
            peers[item["user_id"]] = Peer(item["user_id"], item["ip"], int(item["port"]))
    return peers


def listen_for_messages(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"message listener on {host}:{port}")
        while True:
            conn, _ = server.accept()
            threading.Thread(target=handle_peer_message, args=(conn,), daemon=True).start()


def handle_peer_message(conn: socket.socket) -> None:
    with conn:
        message = recv_message(conn)
        sender = message.headers.get("From", "unknown")
        print(f"\n[{sender}] {message.body}")
        print("> ", end="", flush=True)


def send_to_peer(peer: Peer, sender: str, body: str) -> None:
    with socket.create_connection((peer.ip, peer.port), timeout=5) as conn:
        conn.sendall(encode_message("MESSAGE", {"From": sender}, body))


def command_loop(user_id: str, peers: dict[str, Peer]) -> None:
    session: dict[str, Peer] = {}
    print_users(peers)
    while True:
        command = input("> ").strip()
        if command == "/users":
            print_users(peers)
        elif command.startswith("/invite "):
            target = command.split(maxsplit=1)[1]
            if target not in peers:
                print(f"unknown user: {target}")
                continue
            session[target] = peers[target]
            print(f"invited {target}")
        elif command.startswith("/send "):
            body = command.split(maxsplit=1)[1]
            for peer in session.values():
                send_to_peer(peer, user_id, body)
            print(f"sent to {len(session)} user(s)")
        elif command == "/end":
            session.clear()
            print("session ended")
        elif command == "/quit":
            break
        else:
            print("commands: /users, /invite <id>, /send <message>, /end, /quit")


def print_users(peers: dict[str, Peer]) -> None:
    if not peers:
        print("online users: none")
        return
    print("online users:")
    for peer in peers.values():
        print(f"- {peer.user_id} ({peer.ip}:{peer.port})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Messenger client")
    parser.add_argument("--id", required=True)
    parser.add_argument("--server-host", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=9000)
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    threading.Thread(
        target=listen_for_messages,
        args=(args.listen_host, args.listen_port),
        daemon=True,
    ).start()
    peers = request_users(args.server_host, args.server_port, args.id, args.listen_host, args.listen_port)
    try:
        command_loop(args.id, peers)
    finally:
        logout(args.server_host, args.server_port, args.id)
