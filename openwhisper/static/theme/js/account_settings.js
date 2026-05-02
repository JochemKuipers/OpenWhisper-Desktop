(function () {
    function getCsrfToken() {
        const el = document.querySelector('[name="csrfmiddlewaretoken"]');
        return el ? el.value : "";
    }

    function showStatus(kind, msg) {
        const box = document.getElementById("profile-status");
        if (!box) return;
        box.classList.remove("hidden", "bg-emerald-50", "text-emerald-800", "bg-red-50", "text-red-700");
        box.classList.add(kind === "ok" ? "bg-emerald-50" : "bg-red-50", kind === "ok" ? "text-emerald-800" : "text-red-700");
        box.textContent = msg;
    }

    function setField(id, value) {
        const el = document.getElementById(id);
        if (el && value !== undefined && value !== null) el.value = value;
    }

    async function loadProfile() {
        const r = await fetch("/api/users/me/", {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        });
        if (!r.ok) {
            showStatus("err", "Could not load profile (" + r.status + ").");
            return;
        }
        const d = await r.json();
        setField("pf-username", d.username);
        setField("pf-email", d.email || "");
        setField("pf-first", d.first_name || "");
        setField("pf-last", d.last_name || "");
        setField("pf-bio", d.bio || "");
        setField("pf-phone", d.phone_number || "");
        setField("pf-location", d.location || "");
        setField("pf-gender", d.gender || "");
        if (d.birth_date) setField("pf-birth", d.birth_date);
    }

    const form = document.getElementById("profile-form");
    if (!form) return;

    loadProfile().catch(function () {
        showStatus("err", "Failed to load profile.");
    });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(form);
        const avatar = document.getElementById("pf-avatar");
        if (avatar && !avatar.files.length) fd.delete("avatar");
        const birth = document.getElementById("pf-birth");
        if (birth && !birth.value) fd.delete("birth_date");
        const gender = document.getElementById("pf-gender");
        if (gender && gender.value === "") fd.delete("gender");
        try {
            const r = await fetch("/api/users/me/", {
                method: "PATCH",
                credentials: "same-origin",
                headers: { "X-CSRFToken": getCsrfToken() },
                body: fd,
            });
            const text = await r.text();
            let data = {};
            try {
                data = text ? JSON.parse(text) : {};
            } catch (_) {
                data = {};
            }
            if (!r.ok) {
                const msg = data.detail || (typeof data === "object" ? JSON.stringify(data) : text);
                showStatus("err", "Save failed: " + msg);
                return;
            }
            showStatus("ok", "Saved.");
            loadProfile();
        } catch (err) {
            showStatus("err", err.message || "Network error.");
        }
    });
})();
