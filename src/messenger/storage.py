from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserInfo:
    user_id: str
    ip: str
    port: int


class UserStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, UserInfo]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {user_id: UserInfo(**info) for user_id, info in raw.items()}

    def save(self, users: dict[str, UserInfo]) -> None:
        serializable = {user_id: asdict(info) for user_id, info in users.items()}
        self.path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    def upsert(self, user: UserInfo) -> dict[str, UserInfo]:
        users = self.load()
        users[user.user_id] = user
        self.save(users)
        return users

    def remove(self, user_id: str) -> dict[str, UserInfo]:
        users = self.load()
        users.pop(user_id, None)
        self.save(users)
        return users
