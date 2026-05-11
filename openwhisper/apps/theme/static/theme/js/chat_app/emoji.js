/** emoji-picker-element — loads from CDN (package has no vendored bundle in repo). */
const EMOJI_PICKER_MODULE =
  "https://cdn.jsdelivr.net/npm/emoji-picker-element@1.29.1/index.js";

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

export function initEmojiPicker(options) {
  const btn = options.button;
  const host = options.host;
  const composer = options.composer;
  const thread = options.thread;
  const convList = options.convList;
  if (!btn || !host || !composer) return null;
  if (host.dataset.emojiPickerInit === "1") return null;
  host.dataset.emojiPickerInit = "1";

  const aborter = new AbortController();
  const signal = aborter.signal;
  let ro = null;

  function layoutEmojiPopover() {
    if (host.classList.contains("hidden")) return;
    const rect = btn.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const margin = 8;
    const pickerEl = host.firstElementChild;
    const pw =
      pickerEl && pickerEl.offsetWidth
        ? pickerEl.offsetWidth
        : Math.min(352, vw - 2 * margin);
    const ph =
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
      ro = new ResizeObserver(function () {
        if (!host.classList.contains("hidden")) layoutEmojiPopover();
      });
      ro.observe(picker);
    }

    function onScrollOrResize() {
      layoutEmojiPopover();
    }
    window.addEventListener("resize", onScrollOrResize, { signal: signal });
    if (thread)
      thread.addEventListener("scroll", onScrollOrResize, {
        passive: true,
        signal: signal,
      });
    if (convList)
      convList.addEventListener("scroll", onScrollOrResize, {
        passive: true,
        signal: signal,
      });

    picker.addEventListener("emoji-click", function (event) {
      const unicode = event.detail && event.detail.unicode;
      if (unicode) insertAtCursor(composer, unicode);
      composer.focus();
      closePicker();
    });

    btn.addEventListener(
      "click",
      function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const opening = host.classList.contains("hidden");
        setOpen(opening);
      },
      { signal: signal },
    );

    document.addEventListener(
      "click",
      function (ev) {
        if (host.classList.contains("hidden")) return;
        const path = typeof ev.composedPath === "function" ? ev.composedPath() : [];
        for (let i = 0; i < path.length; i++) {
          const n = path[i];
          if (n === btn || n === host || n === picker) return;
        }
        closePicker();
      },
      { capture: true, signal: signal },
    );

    document.addEventListener(
      "keydown",
      function (ev) {
        if (ev.key === "Escape" && !host.classList.contains("hidden")) {
          closePicker();
          btn.focus();
        }
      },
      { signal: signal },
    );
  })();

  return function cleanupEmojiPicker() {
    aborter.abort();
    if (ro) ro.disconnect();
    host.dataset.emojiPickerInit = "0";
  };
}
