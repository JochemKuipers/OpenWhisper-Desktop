(function () {
  const STORAGE_ACCESS = "openwhisper_access";
  const STORAGE_REFRESH = "openwhisper_refresh";

  /** emoji-picker-element — loads from CDN (package has no vendored bundle in repo). */
  const EMOJI_PICKER_MODULE =
    "https://cdn.jsdelivr.net/npm/emoji-picker-element@1.29.1/index.js";

  const root = document.getElementById("chat-app-root");
  if (!root) return;

  const currentUsername = root.dataset.currentUser || "";

  const els = {
    convSearch: document.getElementById("conv-search"),
    convList: document.getElementById("conversation-list"),
    convEmpty: document.getElementById("conv-empty"),
    chatEmpty: document.getElementById("chat-empty"),
    chatActive: document.getElementById("chat-active"),
    thread: document.getElementById("message-thread"),
    composer: document.getElementById("composer-input"),
    btnSend: document.getElementById("btn-send"),
    headerTitle: document.getElementById("chat-header-title"),
    headerSub: document.getElementById("chat-header-sub"),
    headerAvatar: document.getElementById("chat-header-avatar"),
    btnInviteChat: document.getElementById("btn-invite-chat"),
    btnRenameChat: document.getElementById("btn-rename-chat"),
    renameChatModal: document.getElementById("rename-chat-modal"),
    renameChatBackdrop: document.getElementById("rename-chat-modal-backdrop"),
    renameChatCancel: document.getElementById("rename-chat-cancel"),
    renameChatSave: document.getElementById("rename-chat-save"),
    renameChatInput: document.getElementById("rename-chat-input"),
    inviteModal: document.getElementById("invite-modal"),
    inviteModalBackdrop: document.getElementById("invite-modal-backdrop"),
    inviteModalClose: document.getElementById("invite-modal-close"),
    inviteFriendsList: document.getElementById("invite-friends-list"),
    inviteFriendsEmpty: document.getElementById("invite-friends-empty"),
    btnOpenPeople: document.getElementById("btn-open-people"),
    peopleModal: document.getElementById("people-modal"),
    peopleModalBackdrop: document.getElementById("people-modal-backdrop"),
    peopleModalClose: document.getElementById("people-modal-close"),
    peopleSearch: document.getElementById("people-search"),
    peopleSearchResults: document.getElementById("people-search-results"),
    friendsList: document.getElementById("friends-list"),
    friendsEmpty: document.getElementById("friends-empty"),
    incomingRequestsList: document.getElementById("incoming-requests-list"),
    incomingRequestsEmpty: document.getElementById("incoming-requests-empty"),
    outgoingRequestsList: document.getElementById("outgoing-requests-list"),
    outgoingRequestsEmpty: document.getElementById("outgoing-requests-empty"),
  };

  let chatsCache = [];
  let selectedChatPk = null;
  let ws = null;
  let socialWs = null;
  let socialReconnectTimer = null;
  let socialOpSeq = 0;
  const pendingSocialAcks = {};
  let friendsUsernames = new Set();
  let incomingFromUsernames = new Set();
  let outgoingToUsernames = new Set();
  let searchDebounceTimer = null;
  /** Bumps on each runPeopleSearch start so overlapping awaits cannot append twice. */
  let peopleSearchSeq = 0;
  let cachedPeopleSearchQuery = "";
  let cachedPeopleSearchRows = null;

  function getCsrf() {
    const inp = document.querySelector('[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : "";
  }

  function setTokens(access, refresh) {
    sessionStorage.setItem(STORAGE_ACCESS, access);
    sessionStorage.setItem(STORAGE_REFRESH, refresh);
  }

  function clearTokens() {
    sessionStorage.removeItem(STORAGE_ACCESS);
    sessionStorage.removeItem(STORAGE_REFRESH);
  }

  function getAccess() {
    return sessionStorage.getItem(STORAGE_ACCESS);
  }

  async function apiFetch(path, options) {
    options = options || {};
    const headers = new Headers(options.headers || {});
    const token = getAccess();
    if (token) headers.set("Authorization", "Bearer " + token);
    const csrftoken = getCsrf();
    if (csrftoken) headers.set("X-CSRFToken", csrftoken);
    let body = options.body;
    if (
      body !== undefined &&
      body !== null &&
      typeof body === "object" &&
      !(body instanceof FormData)
    ) {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(body);
    }
    const res = await fetch(path, {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: headers,
      body: body,
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (_) {
      data = text;
    }
    if (res.status === 401) {
      clearTokens();
      window.location.href = "/login/";
      throw new Error("Unauthorized");
    }
    if (!res.ok) {
      let msg = res.status + " " + res.statusText;
      if (data && typeof data.detail === "string") msg = data.detail;
      else if (data && data.detail) msg = JSON.stringify(data.detail);
      else if (data && typeof data === "object") msg = JSON.stringify(data);
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  }

  async function bootstrapSessionJwt() {
    clearTokens();
    const data = await apiFetch("/api/auth/session-token/", {
      method: "POST",
      body: {},
    });
    setTokens(data.access, data.refresh);
  }

  function chatPkFromUrl(url) {
    const m = String(url).match(/\/chats\/(\d+)\/?$/);
    return m ? m[1] : null;
  }

  function formatShortTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      hour: "numeric",
      minute: "2-digit",
      month: "short",
      day: "numeric",
    });
  }

  function insertAtCursor(textarea, text) {
    if (!textarea || typeof text !== "string") return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = textarea.value.substring(0, start);
    const after = textarea.value.substring(end);
    textarea.value = before + text + after;
    const pos = start + text.length;
    textarea.selectionStart = textarea.selectionEnd = pos;
  }

  function initEmojiPicker() {
    const btn = document.getElementById("btn-emoji");
    const host = document.getElementById("emoji-picker-host");
    const composer = els.composer;
    if (!btn || !host || !composer) return;

    /** Viewport-fixed placement — avoids broken absolute anchors inside nested flex / overflow stacks. */
    function layoutEmojiPopover() {
      if (host.classList.contains("hidden")) return;
      const rect = btn.getBoundingClientRect();
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const margin = 8;
      const pickerEl = host.firstElementChild;
      let pw =
        pickerEl && pickerEl.offsetWidth
          ? pickerEl.offsetWidth
          : Math.min(352, vw - 2 * margin);
      let ph =
        pickerEl && pickerEl.offsetHeight
          ? pickerEl.offsetHeight
          : Math.min(360, vh - 2 * margin);

      const spaceAbove = rect.top - margin;
      const spaceBelow = vh - rect.bottom - margin;
      const preferAbove = spaceAbove >= ph || spaceAbove >= spaceBelow;

      let top;
      if (preferAbove) {
        top = rect.top - margin - ph;
        if (top < margin) top = margin;
      } else {
        top = rect.bottom + margin;
        if (top + ph > vh - margin) {
          top = Math.max(margin, vh - margin - ph);
        }
      }

      let left = rect.right - pw;
      if (left < margin) left = margin;
      if (left + pw > vw - margin) left = vw - margin - pw;

      host.style.top = top + "px";
      host.style.left = left + "px";
      host.style.right = "auto";
      host.style.bottom = "auto";
    }

    function scheduleLayout() {
      requestAnimationFrame(function () {
        requestAnimationFrame(layoutEmojiPopover);
      });
    }

    function setOpen(open) {
      if (open) {
        host.classList.remove("hidden");
        btn.setAttribute("aria-expanded", "true");
        host.setAttribute("aria-hidden", "false");
        scheduleLayout();
      } else {
        host.classList.add("hidden");
        btn.setAttribute("aria-expanded", "false");
        host.setAttribute("aria-hidden", "true");
      }
    }

    function closePicker() {
      setOpen(false);
    }

    (async function () {
      try {
        await import(/* webpackIgnore: true */ EMOJI_PICKER_MODULE);
      } catch (e) {
        console.error("emoji-picker-element failed to load", e);
        btn.disabled = true;
        btn.title = "Emoji picker unavailable";
        return;
      }

      document.body.appendChild(host);

      host.innerHTML = "";
      const picker = document.createElement("emoji-picker");
      picker.style.height = "min(360px, calc(100vh - 2rem))";
      picker.style.width = "min(352px, calc(100vw - 2rem))";
      picker.style.boxShadow =
        "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)";
      picker.style.borderRadius = "0.75rem";
      host.appendChild(picker);

      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(function () {
          if (!host.classList.contains("hidden")) layoutEmojiPopover();
        });
        ro.observe(picker);
      }

      function onScrollOrResize() {
        layoutEmojiPopover();
      }
      window.addEventListener("resize", onScrollOrResize);
      if (els.thread)
        els.thread.addEventListener("scroll", onScrollOrResize, {
          passive: true,
        });
      if (els.convList)
        els.convList.addEventListener("scroll", onScrollOrResize, {
          passive: true,
        });

      picker.addEventListener("emoji-click", function (event) {
        const unicode = event.detail && event.detail.unicode;
        if (unicode) insertAtCursor(composer, unicode);
        composer.focus();
        closePicker();
      });

      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const opening = host.classList.contains("hidden");
        setOpen(opening);
      });

      document.addEventListener(
        "click",
        function (ev) {
          if (host.classList.contains("hidden")) return;
          var path =
            typeof ev.composedPath === "function" ? ev.composedPath() : [];
          var i;
          for (i = 0; i < path.length; i++) {
            var n = path[i];
            if (n === btn || n === host || n === picker) return;
          }
          closePicker();
        },
        true,
      );

      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape" && !host.classList.contains("hidden")) {
          closePicker();
          btn.focus();
        }
      });
    })();
  }

  function participantTitle(chat) {
    const names = (chat.users || [])
      .map(function (u) {
        return u.username;
      })
      .filter(function (n) {
        return n !== currentUsername;
      });
    return names.length ? names.join(", ") : "Chat";
  }

  function displayChatTitle(chat) {
    const raw =
      chat && chat.title != null && chat.title !== undefined
        ? String(chat.title).trim()
        : "";
    if (raw) return raw;
    return participantTitle(chat);
  }

  function isMultiUserChat(chat) {
    return (chat.users || []).length >= 3;
  }

  function syncChatHeader(chat) {
    if (!chat || !els.headerTitle) return;
    const title = displayChatTitle(chat);
    els.headerTitle.textContent = title;
    els.headerSub.textContent =
      (chat.users || []).length + " members · Active";
    els.headerAvatar.textContent = title.slice(0, 2).toUpperCase();
    if (els.btnRenameChat) {
      els.btnRenameChat.classList.toggle("hidden", !isMultiUserChat(chat));
    }
  }

  function lastPreview(chat) {
    const msgs = chat.messages || [];
    if (!msgs.length) return "No messages yet";
    const last = msgs[msgs.length - 1];
    return (
      (last.sender && last.sender.username ? last.sender.username + ": " : "") +
      (last.content || "").slice(0, 48)
    );
  }

  function renderConversationList(filterText) {
    const ft = (filterText || "").trim().toLowerCase();
    els.convList.innerHTML = "";
    const list = chatsCache.filter(function (c) {
      if (!ft) return true;
      const hay =
        (displayChatTitle(c) + " " + participantTitle(c) + " " + lastPreview(c)).toLowerCase();
      return hay.indexOf(ft) !== -1;
    });
    if (!list.length) {
      els.convEmpty.classList.remove("hidden");
      return;
    }
    els.convEmpty.classList.add("hidden");
    list.forEach(function (chat) {
      const pk = chatPkFromUrl(chat.url);
      if (!pk) return;
      const li = document.createElement("li");
      li.setAttribute("role", "option");
      li.dataset.pk = pk;
      li.className =
        "cursor-pointer rounded-xl px-3 py-3 hover:bg-slate-50 " +
        (pk === selectedChatPk ? "bg-blue-50 ring-1 ring-blue-200" : "");
      const title = displayChatTitle(chat);
      const preview = lastPreview(chat);
      const lastMsg =
        chat.messages && chat.messages.length
          ? chat.messages[chat.messages.length - 1]
          : null;
      const when =
        lastMsg && lastMsg.created_at
          ? formatShortTime(lastMsg.created_at)
          : "";
      li.innerHTML =
        '<div class="flex gap-3">' +
        '<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600">' +
        title.slice(0, 2).toUpperCase() +
        "</div>" +
        '<div class="min-w-0 flex-1">' +
        '<div class="flex justify-between gap-2">' +
        '<span class="truncate font-medium text-slate-900">' +
        escapeHtml(title) +
        "</span>" +
        '<span class="shrink-0 text-xs text-slate-400">' +
        escapeHtml(when) +
        "</span>" +
        "</div>" +
        '<p class="truncate text-xs text-slate-500">' +
        escapeHtml(preview) +
        "</p>" +
        "</div>" +
        "</div>";
      li.addEventListener("click", function () {
        selectChat(pk);
      });
      els.convList.appendChild(li);
    });
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function disconnectWs() {
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  function rejectAllSocialPending(message) {
    Object.keys(pendingSocialAcks).forEach(function (k) {
      const p = pendingSocialAcks[k];
      if (!p) return;
      delete pendingSocialAcks[k];
      clearTimeout(p.timeoutId);
      p.reject(new Error(message));
    });
  }

  function applySocialNotification(j) {
    const t = j.type;
    if (t === "friend_request_received") {
      incomingFromUsernames.add(j.username);
    } else if (t === "friend_request_sent") {
      outgoingToUsernames.add(j.username);
    } else if (t === "friend_request_accepted") {
      incomingFromUsernames.delete(j.username);
      outgoingToUsernames.delete(j.username);
      friendsUsernames.add(j.username);
      loadChats().catch(function () {});
    } else if (t === "friend_request_removed") {
      incomingFromUsernames.delete(j.username);
      outgoingToUsernames.delete(j.username);
    } else if (t === "friend_removed") {
      friendsUsernames.delete(j.username);
      incomingFromUsernames.delete(j.username);
      outgoingToUsernames.delete(j.username);
      loadChats().catch(function () {});
    } else if (t === "chat_updated") {
      loadChats()
        .then(function () {
          if (!selectedChatPk) return;
          if (String(selectedChatPk) !== String(j.chat_id)) return;
          const ch = chatsCache.find(function (c) {
            return chatPkFromUrl(c.url) === String(j.chat_id);
          });
          if (ch) syncChatHeader(ch);
        })
        .catch(function () {});
      return;
    } else {
      return;
    }
    if (
      els.peopleModal &&
      !els.peopleModal.classList.contains("hidden")
    ) {
      refreshPeoplePanels();
      refreshPeopleSearchDomOnly();
    }
  }

  function connectSocialWs() {
    const token = getAccess();
    if (!token) return;
    if (socialWs && socialWs.readyState === WebSocket.OPEN) return;
    if (socialWs && socialWs.readyState === WebSocket.CONNECTING) return;
    if (socialWs) {
      socialWs.onclose = null;
      socialWs.close();
      socialWs = null;
    }
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url =
      proto +
      "//" +
      window.location.host +
      "/ws/social/?token=" +
      encodeURIComponent(token);
    socialWs = new WebSocket(url);
    socialWs.onmessage = function (ev) {
      try {
        const j = JSON.parse(ev.data);
        if (j.type === "social_ack") {
          const pending = pendingSocialAcks[j.op_id];
          if (pending) {
            delete pendingSocialAcks[j.op_id];
            clearTimeout(pending.timeoutId);
            if (j.ok) pending.resolve(j);
            else pending.reject(new Error(j.detail || "Request failed."));
          }
          return;
        }
        applySocialNotification(j);
      } catch (_) {
        /* ignore */
      }
    };
    socialWs.onclose = function () {
      socialWs = null;
      rejectAllSocialPending("Connection closed.");
      if (!getAccess()) return;
      if (socialReconnectTimer) clearTimeout(socialReconnectTimer);
      socialReconnectTimer = setTimeout(function () {
        socialReconnectTimer = null;
        connectSocialWs();
      }, 2500);
    };
  }

  function ensureSocialWsConnected() {
    return new Promise(function (resolve, reject) {
      const token = getAccess();
      if (!token) {
        reject(new Error("Not signed in."));
        return;
      }
      if (socialWs && socialWs.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }
      connectSocialWs();
      let n = 0;
      const iv = setInterval(function () {
        n++;
        if (socialWs && socialWs.readyState === WebSocket.OPEN) {
          clearInterval(iv);
          resolve();
        } else if (n > 200) {
          clearInterval(iv);
          reject(new Error("Social socket failed to connect."));
        }
      }, 50);
    });
  }

  function socialRpc(action, fields) {
    return ensureSocialWsConnected().then(function () {
      return new Promise(function (resolve, reject) {
        const op_id = ++socialOpSeq;
        const timeoutId = setTimeout(function () {
          if (pendingSocialAcks[op_id]) {
            delete pendingSocialAcks[op_id];
            reject(new Error("Request timed out."));
          }
        }, 15000);
        pendingSocialAcks[op_id] = {
          resolve: resolve,
          reject: reject,
          timeoutId: timeoutId,
        };
        socialWs.send(
          JSON.stringify(
            Object.assign({ action: action, op_id: op_id }, fields || {}),
          ),
        );
      });
    });
  }

  function connectWs(chatPk) {
    disconnectWs();
    const token = getAccess();
    if (!chatPk || !token) return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url =
      proto +
      "//" +
      window.location.host +
      "/ws/chats/" +
      encodeURIComponent(chatPk) +
      "/?token=" +
      encodeURIComponent(token);
    ws = new WebSocket(url);
    ws.onmessage = function (ev) {
      try {
        const j = JSON.parse(ev.data);
        if (
          j.type === "chat.members_updated" &&
          String(j.chat_id) === String(chatPk)
        ) {
          loadChats()
            .then(function () {
              const ch = chatsCache.find(function (c) {
                return chatPkFromUrl(c.url) === String(chatPk);
              });
              if (ch) syncChatHeader(ch);
            })
            .catch(function () {});
          return;
        }
        if (
          j.type !== "message.created" ||
          String(j.chat_id) !== String(chatPk)
        )
          return;
        if (j.sender_username === currentUsername) return;
        appendBubble(
          j.sender_username || String(j.sender_id),
          j.content,
          j.created_at,
          true,
        );
      } catch (_) {
        /* ignore ping etc */
      }
    };
  }

  function appendBubble(senderLabel, content, createdAt, incoming) {
    const wrap = document.createElement("div");
    wrap.className = incoming
      ? "mb-4 flex justify-start gap-2"
      : "mb-4 flex justify-end gap-2";

    const bubble = document.createElement("div");
    bubble.className = incoming
      ? "max-w-[85%] rounded-2xl rounded-tl-sm bg-white px-4 py-2 text-sm text-slate-900 shadow-sm ring-1 ring-slate-100"
      : "max-w-[85%] rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-2 text-sm text-white shadow-sm";

    const meta = document.createElement("div");
    meta.className = incoming
      ? "text-xs text-slate-500"
      : "text-xs text-blue-100";
    meta.textContent =
      (incoming ? senderLabel + " · " : "") + formatShortTime(createdAt);

    bubble.appendChild(meta);
    const p = document.createElement("p");
    p.className = incoming
      ? "mt-1 whitespace-pre-wrap text-slate-800"
      : "mt-1 whitespace-pre-wrap text-white";
    p.textContent = content;
    bubble.appendChild(p);

    if (incoming) {
      const av = document.createElement("div");
      av.className =
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-[10px] font-semibold text-slate-600";
      av.textContent = (senderLabel || "?").slice(0, 2).toUpperCase();
      wrap.appendChild(av);
      wrap.appendChild(bubble);
    } else {
      wrap.appendChild(bubble);
    }

    els.thread.appendChild(wrap);
    els.thread.scrollTop = els.thread.scrollHeight;
  }

  function renderMessages(chatPk, msgs) {
    els.thread.innerHTML = "";
    const chronological = (msgs || []).slice().sort(function (a, b) {
      return new Date(a.created_at) - new Date(b.created_at);
    });
    chronological.forEach(function (m) {
      const uname = m.sender && m.sender.username ? m.sender.username : "?";
      const incoming = uname !== currentUsername;
      appendBubble(uname, m.content || "", m.created_at, incoming);
    });
    els.thread.scrollTop = els.thread.scrollHeight;
  }

  async function selectChat(pk) {
    selectedChatPk = pk;
    renderConversationList(els.convSearch.value);
    const chat = chatsCache.find(function (c) {
      return chatPkFromUrl(c.url) === pk;
    });
    if (!chat) return;

    els.chatEmpty.classList.add("hidden");
    els.chatActive.classList.remove("hidden");

    syncChatHeader(chat);

    const msgs = await apiFetch("/api/chats/" + pk + "/messages/", {
      method: "GET",
    });
    renderMessages(pk, msgs);

    connectWs(pk);

    els.composer.focus();
  }

  async function loadChats() {
    chatsCache = await apiFetch("/api/chats/", { method: "GET" });
    if (!Array.isArray(chatsCache)) chatsCache = [];
    renderConversationList(els.convSearch.value);
  }

  async function sendMessage() {
    const pk = selectedChatPk;
    const text = (els.composer.value || "").trim();
    if (!pk || !text) return;
    await apiFetch("/api/chats/" + pk + "/messages/", {
      method: "POST",
      body: { content: text },
    });
    els.composer.value = "";
    const msgs = await apiFetch("/api/chats/" + pk + "/messages/", {
      method: "GET",
    });
    renderMessages(pk, msgs);
    await loadChats();
  }

  els.convSearch.addEventListener("input", function () {
    renderConversationList(els.convSearch.value);
  });

  els.btnSend.addEventListener("click", sendMessage);
  els.composer.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  async function loadFriendsUsernames() {
    const rows = await apiFetch("/api/users/me/friends/", { method: "GET" });
    friendsUsernames = new Set(
      (rows || []).map(function (r) {
        return r.username;
      }),
    );
  }

  async function loadFriendRequests() {
    const data = await apiFetch("/api/users/me/friend-requests/", {
      method: "GET",
    });
    incomingFromUsernames = new Set(
      (data.incoming || []).map(function (r) {
        return r.username;
      }),
    );
    outgoingToUsernames = new Set(
      (data.outgoing || []).map(function (r) {
        return r.username;
      }),
    );
  }

  function renderIncomingRequests() {
    if (!els.incomingRequestsList || !els.incomingRequestsEmpty) return;
    els.incomingRequestsList.innerHTML = "";
    const names = Array.from(incomingFromUsernames).sort();
    if (!names.length) {
      els.incomingRequestsEmpty.classList.remove("hidden");
      els.incomingRequestsList.classList.add("hidden");
      return;
    }
    els.incomingRequestsEmpty.classList.add("hidden");
    els.incomingRequestsList.classList.remove("hidden");
    names.forEach(function (uname) {
      const li = document.createElement("li");
      li.className =
        "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-white px-3 py-2";

      const span = document.createElement("span");
      span.className = "text-sm font-medium text-slate-800";
      span.textContent = uname;

      const actions = document.createElement("div");
      actions.className = "flex shrink-0 gap-1";

      const btnAccept = document.createElement("button");
      btnAccept.type = "button";
      btnAccept.className =
        "rounded-lg bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500";
      btnAccept.textContent = "Accept";
      btnAccept.addEventListener("click", function () {
        acceptFriendRequest(uname).catch(function (err) {
          alert(err.message || "Could not accept.");
        });
      });

      const btnDecline = document.createElement("button");
      btnDecline.type = "button";
      btnDecline.className =
        "rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50";
      btnDecline.textContent = "Decline";
      btnDecline.addEventListener("click", function () {
        cancelFriendRequest(uname).catch(function (err) {
          alert(err.message || "Could not decline.");
        });
      });

      actions.appendChild(btnAccept);
      actions.appendChild(btnDecline);
      li.appendChild(span);
      li.appendChild(actions);
      els.incomingRequestsList.appendChild(li);
    });
  }

  function renderOutgoingRequests() {
    if (!els.outgoingRequestsList || !els.outgoingRequestsEmpty) return;
    els.outgoingRequestsList.innerHTML = "";
    const names = Array.from(outgoingToUsernames).sort();
    if (!names.length) {
      els.outgoingRequestsEmpty.classList.remove("hidden");
      els.outgoingRequestsList.classList.add("hidden");
      return;
    }
    els.outgoingRequestsEmpty.classList.add("hidden");
    els.outgoingRequestsList.classList.remove("hidden");
    names.forEach(function (uname) {
      const li = document.createElement("li");
      li.className =
        "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2";

      const span = document.createElement("span");
      span.className = "truncate text-sm font-medium text-slate-800";
      span.textContent = uname;

      const btnCancel = document.createElement("button");
      btnCancel.type = "button";
      btnCancel.className =
        "shrink-0 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 hover:bg-slate-100";
      btnCancel.textContent = "Cancel";
      btnCancel.title = "Withdraw friend request";
      btnCancel.addEventListener("click", function () {
        cancelFriendRequest(uname).catch(function (err) {
          alert(err.message || "Could not cancel.");
        });
      });

      const pending = document.createElement("span");
      pending.className = "text-xs text-slate-500";
      pending.textContent = "Pending";

      const actions = document.createElement("div");
      actions.className = "flex shrink-0 items-center gap-2";
      actions.appendChild(pending);
      actions.appendChild(btnCancel);

      li.appendChild(span);
      li.appendChild(actions);
      els.outgoingRequestsList.appendChild(li);
    });
  }

  function refreshPeoplePanels() {
    renderIncomingRequests();
    renderOutgoingRequests();
    renderFriendsList();
  }

  function closePeopleModal() {
    if (els.peopleModal) els.peopleModal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }

  function openPeopleModal() {
    if (!els.peopleModal) return;
    els.peopleModal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
    if (els.peopleSearch) els.peopleSearch.value = "";
    if (els.peopleSearchResults) els.peopleSearchResults.innerHTML = "";
    cachedPeopleSearchQuery = "";
    cachedPeopleSearchRows = null;
    Promise.all([loadFriendsUsernames(), loadFriendRequests()])
      .then(refreshPeoplePanels)
      .catch(function (e) {
        alert(e.message || "Could not load people.");
      });
    if (els.peopleSearch) els.peopleSearch.focus();
  }

  function renderFriendsList() {
    if (!els.friendsList || !els.friendsEmpty) return;
    els.friendsList.innerHTML = "";
    const names = Array.from(friendsUsernames).sort();
    if (!names.length) {
      els.friendsEmpty.classList.remove("hidden");
      return;
    }
    els.friendsEmpty.classList.add("hidden");
    names.forEach(function (uname) {
      const li = document.createElement("li");
      li.className =
        "flex items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2";

      const span = document.createElement("span");
      span.className = "truncate text-sm font-medium text-slate-800";
      span.textContent = uname;

      const actions = document.createElement("div");
      actions.className = "flex shrink-0 gap-1";

      const btnChat = document.createElement("button");
      btnChat.type = "button";
      btnChat.className =
        "rounded-lg bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500";
      btnChat.textContent = "Chat";
      btnChat.addEventListener("click", function () {
        openOrSelectDm(uname);
      });

      const btnRm = document.createElement("button");
      btnRm.type = "button";
      btnRm.className =
        "rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white";
      btnRm.textContent = "Remove";
      btnRm.addEventListener("click", function () {
        removeFriend(uname);
      });

      actions.appendChild(btnChat);
      actions.appendChild(btnRm);
      li.appendChild(span);
      li.appendChild(actions);
      els.friendsList.appendChild(li);
    });
  }

  function removeFriend(username) {
    if (!confirm("Remove " + username + " from friends?")) return;
    socialRpc("friend_remove", { username: username }).catch(function (err) {
      alert(err.message || "Could not remove friend.");
    });
  }

  function sendFriendRequest(username) {
    return socialRpc("friend_request_send", { username: username });
  }

  function acceptFriendRequest(username) {
    return socialRpc("friend_request_accept", { username: username });
  }

  function cancelFriendRequest(username) {
    return socialRpc("friend_request_cancel", { username: username });
  }

  function refreshPeopleSearchDomOnly() {
    if (!els.peopleSearch || !els.peopleSearchResults) return;
    const q = els.peopleSearch.value.trim();
    if (
      q.length < 2 ||
      q !== cachedPeopleSearchQuery ||
      cachedPeopleSearchRows === null
    ) {
      return;
    }
    renderPeopleSearchRows(cachedPeopleSearchRows);
  }

  function renderPeopleSearchRows(rows) {
    if (!els.peopleSearchResults) return;
    els.peopleSearchResults.innerHTML = "";
    if (!rows || !rows.length) {
      const li = document.createElement("li");
      li.className = "text-sm text-slate-500";
      li.textContent = "No users match.";
      els.peopleSearchResults.appendChild(li);
      return;
    }
    rows.forEach(function (row) {
      const uname = row.username;
      const li = document.createElement("li");
      li.className =
        "flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-white px-3 py-2";

      const span = document.createElement("span");
      span.className = "text-sm font-medium text-slate-800";
      span.textContent = uname;

      const actions = document.createElement("div");
      actions.className = "flex shrink-0 gap-1";

      const isFriend = friendsUsernames.has(uname);
      const incoming = incomingFromUsernames.has(uname);
      const outgoing = outgoingToUsernames.has(uname);

      if (!isFriend && incoming) {
        const btnAccept = document.createElement("button");
        btnAccept.type = "button";
        btnAccept.className =
          "rounded-lg bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500";
        btnAccept.textContent = "Accept";
        btnAccept.addEventListener("click", function () {
          acceptFriendRequest(uname).catch(function (err) {
            alert(err.message || "Could not accept.");
          });
        });
        const btnDecline = document.createElement("button");
        btnDecline.type = "button";
        btnDecline.className =
          "rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50";
        btnDecline.textContent = "Decline";
        btnDecline.addEventListener("click", function () {
          cancelFriendRequest(uname).catch(function (err) {
            alert(err.message || "Could not decline.");
          });
        });
        actions.appendChild(btnAccept);
        actions.appendChild(btnDecline);
      } else if (!isFriend && outgoing) {
        const lbl = document.createElement("span");
        lbl.className = "rounded-lg bg-slate-100 px-2 py-1 text-xs text-slate-600";
        lbl.textContent = "Request sent";
        const btnCancel = document.createElement("button");
        btnCancel.type = "button";
        btnCancel.className =
          "rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white";
        btnCancel.textContent = "Cancel";
        btnCancel.addEventListener("click", function () {
          cancelFriendRequest(uname).catch(function (err) {
            alert(err.message || "Could not cancel.");
          });
        });
        actions.appendChild(lbl);
        actions.appendChild(btnCancel);
      } else if (!isFriend) {
        const btnReq = document.createElement("button");
        btnReq.type = "button";
        btnReq.className =
          "rounded-lg border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100";
        btnReq.textContent = "Send request";
        btnReq.addEventListener("click", function () {
          sendFriendRequest(uname).catch(function (err) {
            alert(err.message || "Could not send request.");
          });
        });
        actions.appendChild(btnReq);
      }

      const btnChat = document.createElement("button");
      btnChat.type = "button";
      btnChat.className =
        "rounded-lg px-2 py-1 text-xs font-semibold text-white " +
        (isFriend
          ? "bg-blue-600 hover:bg-blue-500"
          : "cursor-not-allowed bg-slate-300");
      btnChat.textContent = "Chat";
      btnChat.disabled = !isFriend;
      if (isFriend) btnChat.title = "Open direct chat";
      else if (incoming) btnChat.title = "Accept their request to chat";
      else if (outgoing) btnChat.title = "Wait until they accept";
      else btnChat.title = "Send a friend request first";
      if (isFriend) {
        btnChat.addEventListener("click", function () {
          openOrSelectDm(uname);
        });
      }

      actions.appendChild(btnChat);
      li.appendChild(span);
      li.appendChild(actions);
      els.peopleSearchResults.appendChild(li);
    });
  }

  async function openOrSelectDm(username) {
    try {
      const chat = await apiFetch("/api/chats/start/", {
        method: "POST",
        body: { username: username },
      });
      await loadChats();
      closePeopleModal();
      const pk = chatPkFromUrl(chat.url);
      if (pk) await selectChat(pk);
    } catch (e) {
      alert(e.message || "Could not start chat.");
    }
  }

  async function runPeopleSearch() {
    if (!els.peopleSearch || !els.peopleSearchResults) return;
    const seq = ++peopleSearchSeq;
    const q = els.peopleSearch.value.trim();
    els.peopleSearchResults.innerHTML = "";
    cachedPeopleSearchQuery = "";
    cachedPeopleSearchRows = null;
    if (q.length < 2) return;
    let rows;
    try {
      rows = await apiFetch("/api/users/search/?q=" + encodeURIComponent(q), {
        method: "GET",
      });
    } catch (e) {
      if (seq !== peopleSearchSeq) return;
      const errLi = document.createElement("li");
      errLi.className = "text-sm text-red-600";
      errLi.textContent = e.message || "Search failed.";
      els.peopleSearchResults.appendChild(errLi);
      return;
    }
    if (seq !== peopleSearchSeq) return;
    cachedPeopleSearchQuery = q;
    cachedPeopleSearchRows = Array.isArray(rows) ? rows : [];
    renderPeopleSearchRows(cachedPeopleSearchRows);
  }

  function closeInviteModal() {
    if (els.inviteModal) els.inviteModal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }

  function closeRenameChatModal() {
    if (els.renameChatModal) els.renameChatModal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }

  function openRenameChatModal() {
    if (!els.renameChatModal || !selectedChatPk || !els.renameChatInput) return;
    const chat = chatsCache.find(function (c) {
      return chatPkFromUrl(c.url) === String(selectedChatPk);
    });
    if (!chat || !isMultiUserChat(chat)) return;
    const stored =
      chat.title != null && chat.title !== undefined ? String(chat.title).trim() : "";
    els.renameChatInput.value = stored;
    els.renameChatModal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
    els.renameChatInput.focus();
    els.renameChatInput.select();
  }

  async function saveRenameChatTitle() {
    const pk = selectedChatPk;
    if (!pk || !els.renameChatInput) return;
    const raw = els.renameChatInput.value.trim();
    try {
      await apiFetch("/api/chats/" + encodeURIComponent(pk) + "/", {
        method: "PATCH",
        body: { title: raw },
      });
      closeRenameChatModal();
      await loadChats();
      const ch = chatsCache.find(function (c) {
        return chatPkFromUrl(c.url) === String(pk);
      });
      if (ch) syncChatHeader(ch);
    } catch (e) {
      alert(e.message || "Could not save chat name.");
    }
  }

  async function openInviteModal() {
    if (!els.inviteModal || !selectedChatPk || !els.inviteFriendsList) return;
    const chat = chatsCache.find(function (c) {
      return chatPkFromUrl(c.url) === String(selectedChatPk);
    });
    if (!chat) return;
    els.inviteModal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
    els.inviteFriendsList.innerHTML = "";
    if (els.inviteFriendsEmpty) els.inviteFriendsEmpty.classList.add("hidden");

    let rows;
    try {
      rows = await apiFetch("/api/users/me/friends/", { method: "GET" });
    } catch (e) {
      alert(e.message || "Could not load friends.");
      closeInviteModal();
      return;
    }

    const inChat = new Set(
      (chat.users || []).map(function (u) {
        return u.username;
      }),
    );
    const eligible = (rows || []).filter(function (r) {
      return !inChat.has(r.username);
    });

    if (!eligible.length) {
      if (els.inviteFriendsEmpty)
        els.inviteFriendsEmpty.classList.remove("hidden");
      return;
    }
    if (els.inviteFriendsEmpty) els.inviteFriendsEmpty.classList.add("hidden");

    eligible.forEach(function (row) {
      const uname = row.username;
      const li = document.createElement("li");
      li.className =
        "flex items-center justify-between gap-2 rounded-xl border border-slate-100 bg-white px-3 py-2";
      const span = document.createElement("span");
      span.className = "truncate text-sm font-medium text-slate-800";
      span.textContent = uname;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "shrink-0 rounded-lg bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500";
      btn.textContent = "Invite";
      btn.addEventListener("click", function () {
        inviteFriendToChat(uname).catch(function (err) {
          alert(err.message || "Could not invite.");
        });
      });
      li.appendChild(span);
      li.appendChild(btn);
      els.inviteFriendsList.appendChild(li);
    });
  }

  async function inviteFriendToChat(username) {
    const pk = selectedChatPk;
    if (!pk) return;
    await apiFetch(
      "/api/chats/" + encodeURIComponent(pk) + "/invite/",
      {
        method: "POST",
        body: { username: username },
      },
    );
    closeInviteModal();
    await loadChats();
    const ch = chatsCache.find(function (c) {
      return chatPkFromUrl(c.url) === String(pk);
    });
    if (ch) syncChatHeader(ch);
  }

  initEmojiPicker();

  if (els.btnInviteChat)
    els.btnInviteChat.addEventListener("click", function () {
      openInviteModal().catch(function () {});
    });
  if (els.btnRenameChat)
    els.btnRenameChat.addEventListener("click", function () {
      openRenameChatModal();
    });
  if (els.renameChatBackdrop)
    els.renameChatBackdrop.addEventListener("click", closeRenameChatModal);
  if (els.renameChatCancel)
    els.renameChatCancel.addEventListener("click", closeRenameChatModal);
  if (els.renameChatSave)
    els.renameChatSave.addEventListener("click", function () {
      saveRenameChatTitle().catch(function () {});
    });
  if (els.inviteModalClose)
    els.inviteModalClose.addEventListener("click", closeInviteModal);
  if (els.inviteModalBackdrop)
    els.inviteModalBackdrop.addEventListener("click", closeInviteModal);

  if (els.btnOpenPeople)
    els.btnOpenPeople.addEventListener("click", openPeopleModal);
  if (els.peopleModalClose)
    els.peopleModalClose.addEventListener("click", closePeopleModal);
  if (els.peopleModalBackdrop)
    els.peopleModalBackdrop.addEventListener("click", closePeopleModal);
  if (els.peopleSearch) {
    els.peopleSearch.addEventListener("input", function () {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(function () {
        runPeopleSearch().catch(function () {});
      }, 320);
    });
  }

  bootstrapSessionJwt()
    .then(function () {
      connectSocialWs();
      return loadChats();
    })
    .catch(function (err) {
      console.error(err);
      alert("Could not start messaging session. Try signing in again.");
    });
})();
