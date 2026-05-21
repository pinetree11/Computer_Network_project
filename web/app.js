const peersEl = document.querySelector("#peers");
const sessionEl = document.querySelector("#session");
const messagesEl = document.querySelector("#messages");
const statusEl = document.querySelector("#status");
const userTitleEl = document.querySelector("#userTitle");
const endpointEl = document.querySelector("#endpoint");
const messageInputEl = document.querySelector("#messageInput");
const sendButtonEl = document.querySelector("#sendForm button");
const refreshButtonEl = document.querySelector("#refreshButton");
const endButtonEl = document.querySelector("#endButton");
const quitButtonEl = document.querySelector("#quitButton");

let lastMessageCount = 0;

const bubblePalettes = [
  { bg: "#e8f1ff", border: "#9ab9f5", name: "#2f4697" },
  { bg: "#e5f8f4", border: "#8cd7c9", name: "#166b63" },
  { bg: "#f1ecff", border: "#b7a4ef", name: "#5b43a6" },
  { bg: "#e9f7ff", border: "#8ecde9", name: "#17698e" },
  { bg: "#fff1f6", border: "#eca6bf", name: "#9a3158" },
  { bg: "#f1f7e7", border: "#b7d98c", name: "#526f1f" },
];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.error) {
    throw new Error(payload.error || "request failed");
  }
  return payload;
}

function render(state) {
  userTitleEl.textContent = state.user.user_id;
  endpointEl.textContent = `${state.user.ip}:${state.user.port}`;
  setControlsEnabled(state.active !== false);

  peersEl.replaceChildren(
    ...state.peers.map((peer) => {
      const item = document.createElement("li");
      const text = document.createElement("span");
      const button = document.createElement("button");
      text.textContent = `${peer.user_id} (${peer.ip}:${peer.port})`;
      button.textContent = "Invite";
      button.type = "button";
      button.addEventListener("click", () => invite(peer.user_id));
      item.append(text, button);
      return item;
    })
  );

  if (state.peers.length === 0) {
    peersEl.append(emptyItem("온라인 사용자가 없습니다."));
  }

  sessionEl.replaceChildren(
    ...state.session.map((peer) => {
      const item = document.createElement("li");
      item.textContent = `${peer.user_id} (${peer.ip}:${peer.port})`;
      return item;
    })
  );

  if (state.session.length === 0) {
    sessionEl.append(emptyItem("초대한 사용자가 없습니다."));
  }

  messagesEl.replaceChildren(
    ...state.messages.map((message) => {
      const item = document.createElement("article");
      const sender = document.createElement("strong");
      const meta = document.createElement("span");
      const body = document.createElement("p");
      const palette = paletteFor(message.sender);
      sender.textContent = message.sender;
      meta.textContent = formatTime(message.received_at);
      body.textContent = message.body;
      item.className = message.sender === state.user.user_id ? "message mine" : "message";
      item.style.setProperty("--bubble-bg", palette.bg);
      item.style.setProperty("--bubble-border", palette.border);
      item.style.setProperty("--sender-color", palette.name);
      item.append(sender, meta, body);
      return item;
    })
  );

  if (state.messages.length !== lastMessageCount) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
    lastMessageCount = state.messages.length;
  }
}

function emptyItem(text) {
  const item = document.createElement("li");
  item.className = "empty";
  item.textContent = text;
  return item;
}

async function refresh() {
  try {
    render(await api("/api/refresh", { method: "POST" }));
    setStatus("온라인 목록을 새로 받았습니다.");
  } catch (error) {
    setStatus(error.message);
  }
}

async function loadState() {
  try {
    render(await api("/api/state"));
  } catch (error) {
    setStatus(error.message);
  }
}

async function invite(userId) {
  try {
    render(
      await api("/api/invite", {
        method: "POST",
        body: JSON.stringify({ user_id: userId }),
      })
    );
    setStatus(`${userId} 초대 완료`);
  } catch (error) {
    setStatus(error.message);
  }
}

async function sendMessage(body) {
  const state = await api("/api/send", {
    method: "POST",
    body: JSON.stringify({ body }),
  });
  render(state);
  setStatus(`${state.sent_count}명에게 전송했습니다.`);
}

function setStatus(text) {
  statusEl.textContent = text;
}

function formatTime(seconds) {
  return new Date(seconds * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function paletteFor(sender) {
  let hash = 0;
  for (const character of sender) {
    hash = (hash * 31 + character.charCodeAt(0)) % bubblePalettes.length;
  }
  return bubblePalettes[hash];
}

function setControlsEnabled(enabled) {
  refreshButtonEl.disabled = !enabled;
  endButtonEl.disabled = !enabled;
  messageInputEl.disabled = !enabled;
  sendButtonEl.disabled = !enabled;
}

refreshButtonEl.addEventListener("click", refresh);

endButtonEl.addEventListener("click", async () => {
  try {
    render(await api("/api/end", { method: "POST" }));
    setStatus("세션을 종료했습니다.");
  } catch (error) {
    setStatus(error.message);
  }
});

quitButtonEl.addEventListener("click", async () => {
  try {
    await api("/api/quit", { method: "POST" });
    setControlsEnabled(false);
    quitButtonEl.disabled = true;
    setStatus("로그아웃하고 웹 클라이언트를 종료했습니다.");
  } catch (error) {
    setStatus(error.message);
  }
});

document.querySelector("#sendForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = messageInputEl.value.trim();
  if (!body) {
    return;
  }
  try {
    await sendMessage(body);
    messageInputEl.value = "";
  } catch (error) {
    setStatus(error.message);
  }
});

loadState();
setInterval(loadState, 1000);
