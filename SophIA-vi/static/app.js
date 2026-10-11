const STORAGE_CHATS = "sophia_chats";
const STORAGE_PROFILE = "sophia_profile";

const els = {
  sidebar: document.getElementById("chat-sidebar"),
  sidebarBackdrop: document.getElementById("sidebarBackdrop"),
  openSidebarBtn: document.getElementById("openSidebarBtn"),
  closeSidebarBtn: document.getElementById("closeSidebarBtn"),
  newChatBtn: document.getElementById("newChatBtn"),
  conversationItems: document.getElementById("conversationItems"),
  profileBtn: document.getElementById("profileBtn"),
  profileAvatar: document.getElementById("profileAvatar"),
  profileName: document.getElementById("profileName"),

  assistantAvatarSmall: document.getElementById("assistantAvatarSmall"),
  chatTitle: document.getElementById("chatTitle"),
  chatSubtitle: document.getElementById("chatSubtitle"),

  chatScroll: document.getElementById("chatScroll"),
  welcomeView: document.getElementById("welcomeView"),
  suggestionsList: document.getElementById("suggestionsList"),
  messageList: document.getElementById("messageList"),

  errorBanner: document.getElementById("errorBanner"),
  errorText: document.getElementById("errorText"),
  retryBtn: document.getElementById("retryBtn"),
  dismissErrorBtn: document.getElementById("dismissErrorBtn"),

  composerForm: document.getElementById("composerForm"),
  question: document.getElementById("question"),
  sendBtn: document.getElementById("sendBtn"),

  settingsDialog: document.getElementById("settingsDialog"),
  closeSettingsBtn: document.getElementById("closeSettingsBtn"),
  cancelSettingsBtn: document.getElementById("cancelSettingsBtn"),
  settingsForm: document.getElementById("settingsForm"),
  settingsAvatarPreview: document.getElementById("settingsAvatarPreview"),
  avatarInput: document.getElementById("avatarInput"),
  displayName: document.getElementById("displayName"),
  settingsError: document.getElementById("settingsError"),
};

const state = {
  chats: [],
  selectedId: null,
  profile: { name: "", avatarUrl: null },
  assistant: null,
  suggestions: [],
  sending: false,
  lastFailedQuestion: null,
};

// ---------- persistência (localStorage) ----------

function loadChats() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_CHATS) || "[]");
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function saveChats() {
  localStorage.setItem(STORAGE_CHATS, JSON.stringify(state.chats));
}

function loadProfile() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_PROFILE) || "null") || { name: "", avatarUrl: null };
  } catch {
    return { name: "", avatarUrl: null };
  }
}

function saveProfile() {
  localStorage.setItem(STORAGE_PROFILE, JSON.stringify(state.profile));
}

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

// ---------- avatar ----------

function avatarMarkup(name, avatarUrl) {
  if (avatarUrl) {
    const img = document.createElement("img");
    img.src = avatarUrl;
    img.alt = `Foto de ${name || "perfil"}`;
    img.className = "avatar-image";
    return img;
  }
  const span = document.createElement("span");
  span.textContent = (name || "?").trim().charAt(0).toLocaleUpperCase() || "?";
  return span;
}

function fillAvatar(container, name, avatarUrl) {
  container.innerHTML = "";
  container.appendChild(avatarMarkup(name, avatarUrl));
}

// ---------- sidebar ----------

function getSelectedChat() {
  return state.chats.find((c) => c.id === state.selectedId) || null;
}

function renderSidebar() {
  fillAvatar(els.profileAvatar, state.profile.name, state.profile.avatarUrl);
  els.profileName.textContent = state.profile.name || "Meu perfil";

  els.conversationItems.innerHTML = "";

  if (state.chats.length === 0) {
    const p = document.createElement("p");
    p.className = "sidebar-empty";
    p.textContent = "Nenhuma conversa ainda.";
    els.conversationItems.appendChild(p);
    return;
  }

  state.chats.forEach((chat) => {
    const row = document.createElement("div");
    row.className = "conversation-row" + (chat.id === state.selectedId ? " conversation-selected" : "");

    const titleBtn = document.createElement("button");
    titleBtn.type = "button";
    titleBtn.className = "conversation-title";
    titleBtn.title = chat.title;
    titleBtn.textContent = chat.title;
    titleBtn.addEventListener("click", () => selectChat(chat.id));

    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.className = "icon-button";
    renameBtn.title = "Renomear conversa";
    renameBtn.setAttribute("aria-label", `Renomear conversa ${chat.title}`);
    renameBtn.innerHTML = iconSvg("rename");
    renameBtn.addEventListener("click", () => renameChat(chat));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "icon-button button-danger";
    deleteBtn.title = "Apagar conversa";
    deleteBtn.setAttribute("aria-label", `Apagar conversa ${chat.title}`);
    deleteBtn.innerHTML = iconSvg("delete");
    deleteBtn.addEventListener("click", () => deleteChat(chat));

    row.append(titleBtn, renameBtn, deleteBtn);
    els.conversationItems.appendChild(row);
  });
}

function iconSvg(name) {
  const paths = {
    rename:
      '<path d="m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15z"/><path d="M13 20h7"/>',
    delete:
      '<path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/>',
  };
  return `<svg class="icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[name] || ""}</svg>`;
}

function startNewChat() {
  state.selectedId = null;
  closeSidebarMobile();
  renderSidebar();
  renderChatPanel();
}

function selectChat(id) {
  state.selectedId = id;
  closeSidebarMobile();
  renderSidebar();
  renderChatPanel();
}

function renameChat(chat) {
  const title = window.prompt("Digite o novo nome da conversa:", chat.title);
  if (title === null) return;
  const trimmed = title.trim();
  if (!trimmed) return;
  chat.title = trimmed;
  saveChats();
  renderSidebar();
  if (chat.id === state.selectedId) renderChatPanel();
}

function deleteChat(chat) {
  if (!window.confirm(`Apagar a conversa "${chat.title}"?`)) return;
  state.chats = state.chats.filter((c) => c.id !== chat.id);
  if (state.selectedId === chat.id) state.selectedId = null;
  saveChats();
  renderSidebar();
  renderChatPanel();
}

function openSidebarMobile() {
  els.sidebar.classList.add("sidebar-open");
  els.sidebarBackdrop.hidden = false;
}
function closeSidebarMobile() {
  els.sidebar.classList.remove("sidebar-open");
  els.sidebarBackdrop.hidden = true;
}

// ---------- painel de chat ----------

function renderChatPanel() {
  const chat = getSelectedChat();

  fillAvatar(els.assistantAvatarSmall, state.assistant?.name, state.assistant?.avatarUrl);
  els.chatTitle.textContent = chat ? chat.title : "Nova conversa";
  els.chatSubtitle.textContent = state.assistant ? state.assistant.name : "Carregando assistente...";

  const hasMessages = chat && chat.messages.length > 0;

  if (hasMessages) {
    els.welcomeView.hidden = true;
    els.messageList.hidden = false;
    renderMessages(chat.messages);
  } else {
    els.messageList.hidden = true;
    els.welcomeView.hidden = false;
  }

  requestAnimationFrame(() => {
    els.chatScroll.scrollTop = els.chatScroll.scrollHeight;
  });
}

function renderSuggestions() {
  els.suggestionsList.innerHTML = "";
  state.suggestions.forEach((question) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "suggestion";
    btn.textContent = question;
    btn.addEventListener("click", () => {
      els.question.value = question;
      submitQuestion();
    });
    els.suggestionsList.appendChild(btn);
  });
}

function messageRow(message) {
  const isUser = message.role === "user";
  const row = document.createElement("div");
  row.className = "message-row" + (isUser ? " message-user" : "");

  const name = isUser ? state.profile.name || "Você" : state.assistant?.name || "Assistente";
  const avatarUrl = isUser ? state.profile.avatarUrl : state.assistant?.avatarUrl;

  if (!isUser) {
    const av = document.createElement("span");
    av.className = "avatar avatar-small";
    fillAvatar(av, name, avatarUrl);
    row.appendChild(av);
  }

  const body = document.createElement("div");
  body.className = "message-body";

  const nameP = document.createElement("p");
  nameP.className = "message-name";
  nameP.textContent = name;
  body.appendChild(nameP);

  const bubble = document.createElement("div");
  bubble.className = "message-bubble" + (isUser ? "" : " message-markdown");

  if (message.pending && !message.content) {
    const span = document.createElement("span");
    span.className = "muted";
    span.textContent = message.failed ? "Não foi possível gerar a resposta." : "Pensando...";
    bubble.appendChild(span);
  } else {
    bubble.style.whiteSpace = "pre-wrap";
    bubble.textContent = message.content;
  }
  body.appendChild(bubble);

  if (!isUser && message.sources && message.sources.length > 0) {
    const details = document.createElement("details");
    details.style.marginTop = "6px";
    const summary = document.createElement("summary");
    summary.className = "message-status";
    summary.style.cursor = "pointer";
    summary.textContent = "Trechos consultados";
    details.appendChild(summary);
    const ul = document.createElement("ul");
    ul.style.margin = "6px 0 0";
    ul.style.paddingLeft = "20px";
    ul.style.fontSize = "12px";
    ul.style.color = "var(--muted)";
    message.sources.forEach((s) => {
      const li = document.createElement("li");
      li.textContent = s;
      ul.appendChild(li);
    });
    details.appendChild(ul);
    body.appendChild(details);
  }

  row.appendChild(body);

  if (isUser) {
    const av = document.createElement("span");
    av.className = "avatar avatar-small";
    fillAvatar(av, name, avatarUrl);
    row.appendChild(av);
  }

  return row;
}

function renderMessages(messages) {
  els.messageList.innerHTML = "";
  messages.forEach((m) => els.messageList.appendChild(messageRow(m)));
}

// ---------- erro ----------

function showError(message) {
  els.errorText.textContent = message;
  els.errorBanner.hidden = false;
}
function clearError() {
  els.errorBanner.hidden = true;
  state.lastFailedQuestion = null;
}

// ---------- envio de mensagem ----------

function setComposerBusy(busy) {
  state.sending = busy;
  els.question.disabled = busy;
  els.sendBtn.disabled = busy || !els.question.value.trim();
  els.sendBtn.textContent = busy ? "Aguarde..." : "Enviar";
}

async function submitQuestion(retryText) {
  const text = (retryText ?? els.question.value).trim();
  if (!text || state.sending) return;

  clearError();

  let chat = getSelectedChat();
  if (!chat) {
    chat = {
      id: uid(),
      title: text.length > 48 ? text.slice(0, 48) + "…" : text,
      messages: [],
    };
    state.chats.unshift(chat);
    state.selectedId = chat.id;
    saveChats();
    renderSidebar();
  }

  const userMessage = { id: uid(), role: "user", content: text };
  chat.messages.push(userMessage);

  const pendingMessage = { id: uid(), role: "assistant", content: "", pending: true };
  chat.messages.push(pendingMessage);

  els.question.value = "";
  setComposerBusy(true);
  renderChatPanel();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text }),
    });
    const data = await res.json().catch(() => null);

    if (!res.ok) {
      throw new Error(data?.error || `Erro do servidor (${res.status}).`);
    }

    pendingMessage.content = data.content;
    pendingMessage.sources = data.sources || [];
    pendingMessage.pending = false;
    saveChats();
    renderSidebar();
    renderChatPanel();
  } catch (err) {
    chat.messages = chat.messages.filter((m) => m.id !== pendingMessage.id);
    saveChats();
    renderChatPanel();
    state.lastFailedQuestion = text;
    showError(err.message || "Não foi possível falar com a SophIA.");
  } finally {
    setComposerBusy(false);
  }
}

// ---------- configurações de perfil ----------

let avatarDraft = null;

function openSettings() {
  els.displayName.value = state.profile.name || "";
  avatarDraft = null;
  fillAvatar(els.settingsAvatarPreview, state.profile.name, state.profile.avatarUrl);
  els.settingsError.hidden = true;
  els.settingsDialog.showModal();
  closeSidebarMobile();
}

function closeSettings() {
  els.settingsDialog.close();
}

els.avatarInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0] || null;
  if (!file) return;

  const okTypes = ["image/png", "image/jpeg", "image/webp"];
  if (!okTypes.includes(file.type) || file.size > 5 * 1024 * 1024) {
    els.settingsError.textContent = "Escolha uma imagem PNG, JPEG ou WebP de até 5 MB.";
    els.settingsError.hidden = false;
    event.target.value = "";
    return;
  }

  els.settingsError.hidden = true;
  const reader = new FileReader();
  reader.onload = () => {
    avatarDraft = reader.result;
    fillAvatar(els.settingsAvatarPreview, els.displayName.value, avatarDraft);
  };
  reader.readAsDataURL(file);
});

els.settingsForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = els.displayName.value.trim();
  if (!name) {
    els.settingsError.textContent = "Informe seu nome.";
    els.settingsError.hidden = false;
    return;
  }
  state.profile.name = name;
  if (avatarDraft) state.profile.avatarUrl = avatarDraft;
  saveProfile();
  renderSidebar();
  renderChatPanel();
  closeSettings();
});

// ---------- eventos gerais ----------

els.newChatBtn.addEventListener("click", startNewChat);
els.openSidebarBtn.addEventListener("click", openSidebarMobile);
els.closeSidebarBtn.addEventListener("click", closeSidebarMobile);
els.sidebarBackdrop.addEventListener("click", closeSidebarMobile);
els.profileBtn.addEventListener("click", openSettings);
els.closeSettingsBtn.addEventListener("click", closeSettings);
els.cancelSettingsBtn.addEventListener("click", closeSettings);

els.composerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion();
});
els.question.addEventListener("input", () => {
  els.sendBtn.disabled = state.sending || !els.question.value.trim();
});
els.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!els.sendBtn.disabled) submitQuestion();
  }
});

els.dismissErrorBtn.addEventListener("click", clearError);
els.retryBtn.addEventListener("click", () => {
  const text = state.lastFailedQuestion;
  clearError();
  if (text) submitQuestion(text);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && els.sidebar.classList.contains("sidebar-open")) {
    closeSidebarMobile();
  }
});

// ---------- inicialização ----------

async function init() {
  state.chats = loadChats();
  state.profile = loadProfile();
  renderSidebar();
  renderChatPanel();

  try {
    const res = await fetch("/api/assistant");
    const data = await res.json();
    state.assistant = { ...data.assistant, avatarUrl: data.assistant.avatarUrl };
    state.suggestions = data.suggestions || [];
  } catch {
    state.assistant = { name: "SophIA", avatarUrl: null };
    state.suggestions = [];
  }

  renderSuggestions();
  renderSidebar();
  renderChatPanel();
}

init();
