from __future__ import annotations

import argparse
import json
import socket
import threading

from .protocol import encode_message, recv_message
from .storage import UserInfo, UserStore


def users_body(users: dict[str, UserInfo]) -> str:
    return json.dumps(
        [user.__dict__ for user in users.values()],
        ensure_ascii=False,
    )


def handle_client(conn: socket.socket, store: UserStore) -> None:
    with conn:
        request = recv_message(conn)
        if request.method == "LOGIN":
            user = UserInfo(
                user_id=request.headers["User-Id"],
                ip=request.headers["Ip"],
                port=int(request.headers["Port"]),
            )
            users = store.upsert(user)
            conn.sendall(encode_message("USERS", body=users_body(users)))
            print(f"[login] {user.user_id} {user.ip}:{user.port}")
        elif request.method == "LOGOUT":
            users = store.remove(request.headers["User-Id"])
            conn.sendall(encode_message("USERS", body=users_body(users)))
            print(f"[logout] {request.headers['User-Id']}")
        else:
            conn.sendall(encode_message("ERROR", body=f"unknown method: {request.method}"))


def run_server(host: str, port: int, store_path: str) -> None:
    store = UserStore(store_path)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"login server listening on {host}:{port}")
        while True:
            conn, _ = server.accept()
            threading.Thread(target=handle_client, args=(conn, store), daemon=True).start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Login server for the messenger project")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--store", default="data/online_users.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_server(args.host, args.port, args.store)
