const serverInput = document.querySelector("#server");
const connectButton = document.querySelector("#connect");
const status = document.querySelector("#status");
const messages = document.querySelector("#messages");
const form = document.querySelector("#message-form");
const messageInput = document.querySelector("#message");
const sendButton = document.querySelector("#send");

let socket;

function addMessage(text) {
  const item = document.createElement("li");
  item.textContent = text;
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
}

function setConnected(connected) {
  status.textContent = connected ? "Online" : "Offline";
  status.dataset.state = connected ? "online" : "offline";
  messageInput.disabled = !connected;
  sendButton.disabled = !connected;
  connectButton.textContent = connected ? "Disconnect" : "Connect";
}

function connect() {
  if (socket) {
    socket.close();
    return;
  }

  socket = new WebSocket(serverInput.value.trim());
  socket.addEventListener("open", () => {
    setConnected(true);
    addMessage("Connected to PocketSocket");
    messageInput.focus();
  });
  socket.addEventListener("message", (event) => addMessage(event.data));
  socket.addEventListener("close", () => {
    socket = null;
    setConnected(false);
    addMessage("Disconnected");
  });
  socket.addEventListener("error", () => addMessage("Connection error"));
}

connectButton.addEventListener("click", connect);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message || !socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(message);
  messageInput.value = "";
  messageInput.focus();
});
