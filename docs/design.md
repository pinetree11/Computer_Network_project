# Messenger Design

## Components

1. Login Server
   - Stores online users in `data/online_users.json`.
   - Receives `LOGIN` and `LOGOUT`.
   - Returns the full online user list after each request.

2. Messenger Client
   - Registers its `id`, `ip`, and listening `port` with the login server.
   - Prints online users.
   - Opens a local TCP listener for direct peer messages.
   - Sends messages directly to invited peers.

## Message Format

```text
METHOD <TYPE>
Header-Name: Header-Value
Content-Length: <bytes>

<body>
```

Current methods:

- `LOGIN`
- `LOGOUT`
- `USERS`
- `MESSAGE`
- `ERROR`

## Session Commands

- `/invite <id>` adds an online user to the current messenger session.
- `/send <message>` sends a message to every user in the session.
- `/end` clears the current session.
