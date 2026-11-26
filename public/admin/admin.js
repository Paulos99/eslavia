(() => {
  "use strict";
  const API = String(window.ESLAVIA_ADMIN_API || "/api").replace(/\/$/, "");
  const TOKEN_KEY = "eslavia-admin-token";
  const MAX_PHOTOS = 8;
  const PAYLOAD_BUDGET = 2_100_000; // base64 bytes of all new photos (API Gateway limit 2.5 MB per request)
  const SINGLE = Array.from({ length: 16 }, (_, i) => String(42 + i * 2));
  const PAIRS = ["42-44", "46-48", "50-52", "54-56", "58-60", "62-64", "66-68", "70-72"];
  const $ = (s, r = document) => r.querySelector(s);
  const state = { data: null, filter: "Все", q: "", editing: null, photos: [], sizes: [], busy: false };

  // ---------- api
  function token() {
    try {
      const t = JSON.parse(localStorage.getItem(TOKEN_KEY) || "null");
      if (t && t.exp * 1000 > Date.now() + 60_000) return t.token;
    } catch (_) { /* ignore */ }
    return null;
  }
  function apiUrl(path) {
    if (!/functions\.yandexcloud\.net/.test(API)) return API + path;
    const [p, q] = path.split("?");
    return API + "?p=" + encodeURIComponent(p) + (q ? "&" + q : "");
  }
  async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json" };
    const t = token();
    if (t) headers["X-Admin-Token"] = t;
    let res;
    try {
      res = await fetch(apiUrl(path), { method: opts.body ? "POST" : "GET", headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
    } catch (_) {
      throw new Error("Нет связи с сервером. Проверьте интернет и повторите.");
    }
    let json = {};
    try { json = await res.json(); } catch (_) { /* empty */ }
    if (res.status === 401 && path !== "/login") { logout(); throw new Error(json.error || "Сессия закончилась, войдите снова"); }
    if (res.status === 413) throw new Error("Фото слишком тяжёлые для одной отправки. Уберите одно-два и сохраните ещё раз.");
    if (!res.ok) throw new Error(json.error || "Сервер ответил ошибкой " + res.status);
    return json;
  }

  // ---------- auth
  document.addEventListener("click", (e) => {
    const b = e.target.closest("#pw-toggle");
    if (!b) return;
    e.preventDefault();
    const inp = $("#password");
    const show = inp.type === "password";
    inp.type = show ? "text" : "password";
    b.setAttribute("aria-pressed", String(show));
    b.setAttribute("aria-label", show ? "Скрыть пароль" : "Показать пароль");
    inp.focus();
  });
  function showLogin() { $("#app").hidden = true; $("#editor").hidden = true; $("#login").hidden = false; setTimeout(() => $("#password").focus(), 50); }
  function logout() { localStorage.removeItem(TOKEN_KEY); showLogin(); }
  $("#logout").addEventListener("click", logout);
  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#login-btn"), err = $("#login-error");
    err.hidden = true; btn.disabled = true; btn.textContent = "Проверяем…";
    try {
      const r = await api("/login", { body: { password: $("#password").value.trim() } });
      localStorage.setItem(TOKEN_KEY, JSON.stringify(r));
      $("#password").value = "";
      await openApp();
    } catch (ex) {
      err.textContent = ex.message; err.hidden = false;
    } finally { btn.disabled = false; btn.textContent = "Войти"; }
  });

  // ---------- catalog list
  async function openApp() {
    $("#login").hidden = true; $("#app").hidden = false;
    await reload();
  }
  async function reload() {
    $("#list").innerHTML = '<li class="empty">Загружаем каталог…</li>';
    try {
      state.data = await api("/products");
    } catch (ex) {
      $("#list").innerHTML = ""; const li = document.createElement("li"); li.className = "empty"; li.textContent = ex.message; $("#list").append(li);
      return;
    }
    const d = state.data;
    const dry = [];
    if (d.dryRun.github) dry.push("сайт не сохраняется");
    if (d.dryRun.telegram) dry.push("посты в канал не отправляются");
    $("#mode-note").hidden = !dry.length && !/test/.test(d.repo);
    $("#mode-note").textContent = "Тестовый режим: " + (dry.length ? dry.join(", ") : "") + (/test/.test(d.repo) ? (dry.length ? "; " : "") + "изменения уходят в тестовую копию сайта" : "") + ".";
    $("#bar-meta").textContent = "Кабинет каталога";
    renderQueue();
    renderBlank();
    renderFilters(); renderList();
  }
  function imgUrl(p) {
    const first = (p.images || [])[0] || "";
    const thumb = first.replace("/images/products/", "/images/thumbs/").replace(/\.webp$/, "-480.webp");
    return { src: state.data.imageBase + thumb, fallback: state.data.rawBase + first };
  }
  function renderFilters() {
    const box = $("#filters"); box.innerHTML = "";
    const cats = ["Все", ...state.data.categories];
    for (const c of cats) {
      const n = c === "Все" ? state.data.products.length : state.data.products.filter((p) => p.category === c).length;
      const b = document.createElement("button");
      b.type = "button"; b.className = "filter"; b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", String(state.filter === c));
      b.innerHTML = `${esc(c)}<b>${n}</b>`;
      b.onclick = () => { state.filter = c; renderFilters(); renderList(); };
      box.append(b);
    }
  }
  function renderList() {
    const q = state.q.trim().toLowerCase();
    const items = state.data.products.filter((p) => (state.filter === "Все" || p.category === state.filter) &&
      (!q || (p.article + " " + p.name).toLowerCase().includes(q)));
    $("#count").textContent = String(state.data.products.length);
    const ul = $("#list"); ul.innerHTML = "";
    $("#empty").hidden = items.length > 0;
    const frag = document.createDocumentFragment();
    for (const p of items) {
      const li = document.createElement("li");
      li.className = "row"; li.tabIndex = 0; li.setAttribute("role", "button");
      li.setAttribute("aria-label", "Изменить " + p.article);
      const u = imgUrl(p);
      li.innerHTML = `<img class="row__img" loading="lazy" alt="" src="${esc(u.src)}">
        <div class="row__main"><div class="row__art">${esc(p.article)}</div><div class="row__name">${esc(p.name)}</div>
        <div class="row__sub">${esc(p.category)} · ${(p.sizes || []).length} разм.${p._post ? "" : ' · <span class="tag-off">нет поста в канале</span>'}</div></div>
        <div class="row__price"><div class="row__opt">${money(p.priceWholesale)}</div><div class="row__ret">розн. ${money(p.priceRetail)}</div></div>`;
      const img = li.querySelector("img");
      img.onerror = () => { if (img.src !== u.fallback) img.src = u.fallback; };
      li.onclick = () => openEditor(p);
      li.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openEditor(p); } };
      frag.append(li);
    }
    ul.append(frag);
  }
  $("#search").addEventListener("input", (e) => { state.q = e.target.value; renderList(); });
  $("#add-btn").addEventListener("click", () => openEditor(null));

  // ---------- editor
  function openEditor(p) {
    state.editing = p;
    $("#ed-title").textContent = p ? p.article : "Новая модель";
    const sel = $("#f-category"); sel.innerHTML = "";
    for (const c of state.data.categories) { const o = document.createElement("option"); o.textContent = c; sel.append(o); }
    if (!p && state.filter !== "Все") sel.value = state.filter;
    $("#f-article").value = p ? p.article : "";
    $("#f-name").value = p ? p.name : "";
    if (p) sel.value = p.category;
    $("#f-opt").value = p ? num(p.priceWholesale) : "";
    $("#f-retail").value = p ? num(p.priceRetail) : "";
    $("#f-colors").value = p ? (p.colors || []).join(", ") : "";
    $("#f-material").value = p ? (p.material || "") : "";
    $("#f-avail").value = p ? (p.availability || "Есть в наличии") : "Есть в наличии";
    $("#f-desc").value = p ? (p.description || "") : "";
    state.sizes = p ? [...(p.sizes || [])] : [];
    state.photos = p ? (p.images || []).map((path) => ({ keep: path, url: state.data.imageBase + path, fallback: state.data.rawBase + path })) : [];
    $("#ed-log").hidden = !p;
    $("#ed-post").hidden = !(p && p._post);
    if (p && p._post) $("#ed-post").href = p._post;
    $("#danger").hidden = !p; $("#del-post").checked = false;
    $("#ed-error").hidden = true;
    document.querySelectorAll(".field.is-bad").forEach((f) => f.classList.remove("is-bad"));
    document.querySelectorAll(".field__error").forEach((f) => { f.hidden = true; });
    renderSizes(); renderPhotos();
    $("#editor").hidden = false;
    document.body.style.overflow = "hidden";
    $("#ed-form .editor__body").scrollTop = 0;
    if (!p) setTimeout(() => $("#f-article").focus(), 60);
  }
  function closeEditor() {
    $("#editor").hidden = true; document.body.style.overflow = "";
    state.photos.forEach((ph) => ph.data && URL.revokeObjectURL(ph.url));
  }
  $("#ed-close").addEventListener("click", closeEditor);
  $("#editor").addEventListener("click", (e) => { if (e.target.id === "editor" && !state.busy) closeEditor(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#editor").hidden && $("#publish").hidden && !$("#confirm").open) closeEditor(); });
  $("#f-article").addEventListener("input", (e) => {
    const name = $("#f-name");
    if (!state.editing && (!name.value || name.dataset.auto === "1")) {
      const base = { "Платья": "платье домашнее", "Сарафаны": "сарафан домашний", "Пижамы для дома": "пижама домашняя",
        "Сорочки": "сорочка домашняя", "Халаты": "халат домашний", "Туники": "туника домашняя",
        "Толстовки": "толстовка" }[$("#f-category").value] || "";
      name.value = e.target.value ? (base + " " + e.target.value.trim()).trim() : "";
      name.dataset.auto = "1";
    }
  });
  $("#f-name").addEventListener("input", (e) => { e.target.dataset.auto = "0"; });

  // sizes
  function renderSizes() {
    for (const [id, list] of [["#sizes-single", SINGLE], ["#sizes-pair", PAIRS]]) {
      const box = $(id); box.innerHTML = "";
      for (const s of list) {
        const b = document.createElement("button");
        b.type = "button"; b.className = "chip"; b.textContent = s;
        b.setAttribute("aria-pressed", String(state.sizes.includes(s)));
        b.onclick = () => { toggleSize(s); };
        box.append(b);
      }
    }
    const extra = state.sizes.filter((s) => !SINGLE.includes(s) && !PAIRS.includes(s));
    $("#size-picked").textContent = state.sizes.length ? "Выбрано: " + sortSizes(state.sizes).join(" · ") : "Размеры пока не выбраны";
    $("#size-picked").dataset.extra = extra.join(",");
  }
  function sortSizes(a) { return [...a].sort((x, y) => parseInt(x, 10) - parseInt(y, 10) || x.length - y.length); }
  function toggleSize(s) {
    state.sizes = state.sizes.includes(s) ? state.sizes.filter((x) => x !== s) : sortSizes([...state.sizes, s]);
    renderSizes();
  }
  $("#size-extra-add").addEventListener("click", () => {
    const v = $("#size-extra").value.replace(/\s+/g, "").replace(/[–—]/g, "-");
    if (!/^\d{2}(-\d{2})?$/.test(v)) { showFieldError("sizes", "Запишите размер как 52 или 50-52"); return; }
    if (!state.sizes.includes(v)) toggleSize(v);
    $("#size-extra").value = ""; hideFieldError("sizes");
  });
  $("#size-extra").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); $("#size-extra-add").click(); } });

  // photos
  function renderPhotos() {
    const ol = $("#photos"); ol.innerHTML = "";
    state.photos.forEach((ph, i) => {
      const li = document.createElement("li");
      li.className = "photo"; li.dataset.index = String(i);
      li.innerHTML = `<img alt="Фото ${i + 1}" src="${esc(ph.url)}">
        <span class="photo__badge${i < 3 ? "" : " photo__badge--tg"}">${i === 0 ? "Обложка" : i < 3 ? "В посте" : i + 1}</span>
        <span class="photo__grip" aria-hidden="true"><svg class="ico"><use href="#i-grip"/></svg></span>
        <div class="photo__tools">
          <button type="button" data-act="left" aria-label="Сдвинуть фото ${i + 1} левее" ${i === 0 ? "disabled" : ""}><svg class="ico"><use href="#i-left"/></svg></button>
          <button type="button" data-act="del" aria-label="Убрать фото ${i + 1}"><svg class="ico"><use href="#i-close"/></svg></button>
          <button type="button" data-act="right" aria-label="Сдвинуть фото ${i + 1} правее" ${i === state.photos.length - 1 ? "disabled" : ""}><svg class="ico"><use href="#i-right"/></svg></button>
        </div>`;
      const img = li.querySelector("img");
      img.onerror = () => { if (ph.fallback && img.src !== ph.fallback) img.src = ph.fallback; };
      li.querySelectorAll("button").forEach((b) => b.addEventListener("click", (e) => {
        e.stopPropagation();
        const act = b.dataset.act;
        if (act === "del") { const [r] = state.photos.splice(i, 1); if (r.data) URL.revokeObjectURL(r.url); }
        if (act === "left" && i > 0) move(i, i - 1);
        if (act === "right" && i < state.photos.length - 1) move(i, i + 1);
        renderPhotos();
      }));
      li.querySelector(".photo__grip").addEventListener("pointerdown", (e) => startDrag(e, i));
      ol.append(li);
    });
    $("#photo-input").closest(".photo-add").hidden = state.photos.length >= MAX_PHOTOS;
  }
  function move(from, to) { const [x] = state.photos.splice(from, 1); state.photos.splice(to, 0, x); }
  function startDrag(e, index) {
    e.preventDefault();
    const items = [...document.querySelectorAll(".photo")];
    const src = items[index]; src.classList.add("is-drag");
    const ghost = document.createElement("div"); ghost.className = "photo__ghost";
    ghost.innerHTML = `<img alt="" src="${esc(src.querySelector("img").src)}">`;
    document.body.append(ghost);
    let over = index;
    const pos = (ev) => { ghost.style.left = ev.clientX - 48 + "px"; ghost.style.top = ev.clientY - 64 + "px"; };
    pos(e);
    const onMove = (ev) => {
      pos(ev);
      const el = document.elementFromPoint(ev.clientX, ev.clientY);
      const target = el && el.closest(".photo");
      items.forEach((x) => x.classList.remove("is-over"));
      if (target) { over = Number(target.dataset.index); if (over !== index) target.classList.add("is-over"); }
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onUp); window.removeEventListener("pointercancel", onUp);
      ghost.remove();
      if (over !== index) move(index, over);
      renderPhotos();
    };
    window.addEventListener("pointermove", onMove); window.addEventListener("pointerup", onUp); window.addEventListener("pointercancel", onUp);
  }
  $("#photo-input").addEventListener("change", async (e) => {
    const files = [...e.target.files].slice(0, MAX_PHOTOS - state.photos.length);
    e.target.value = "";
    hideFieldError("photos");
    for (const f of files) {
      try {
        const blob = await toJpeg(f, 0.9);
        state.photos.push({ data: blob, url: URL.createObjectURL(blob) });
        renderPhotos();
      } catch (_) {
        showFieldError("photos", `Не удалось открыть «${f.name}». Подойдут JPEG, PNG, WebP и фото с iPhone.`);
      }
    }
  });
  async function loadImage(file) {
    if (window.createImageBitmap) {
      try { return await createImageBitmap(file, { imageOrientation: "from-image" }); } catch (_) { /* fallback */ }
    }
    return await new Promise((ok, fail) => { const im = new Image(); im.onload = () => ok(im); im.onerror = fail; im.src = URL.createObjectURL(file); });
  }
  // 900x1200 (3:4). Close to 3:4 -> scaled; otherwise fitted on white, nothing is cut off.
  async function toJpeg(file, quality) {
    const im = await loadImage(file);
    const W = 900, H = 1200, w = im.width, h = im.height;
    const c = document.createElement("canvas"); c.width = W; c.height = H;
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, W, H); g.imageSmoothingQuality = "high";
    if (Math.abs(w / h - 0.75) <= 0.02) g.drawImage(im, 0, 0, W, H);
    else { const s = Math.min(W / w, H / h), dw = w * s, dh = h * s; g.drawImage(im, (W - dw) / 2, (H - dh) / 2, dw, dh); }
    if (im.close) im.close();
    c._q = quality;
    return await new Promise((ok, fail) => c.toBlob((b) => (b ? ok(b) : fail(new Error("canvas"))), "image/jpeg", quality));
  }
  const toB64 = (blob) => new Promise((ok, fail) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(",")[1]); r.onerror = fail; r.readAsDataURL(blob); });
  async function shrink(blob, q) {
    const f = new File([blob], "p.jpg", { type: "image/jpeg" });
    return await toJpeg(f, q);
  }

  // ---------- validation + save
  function showFieldError(key, msg) {
    const el = $("#err-" + key); if (!el) return;
    el.textContent = msg; el.hidden = false;
    const f = el.closest(".field"); if (f) f.classList.add("is-bad");
  }
  function hideFieldError(key) { const el = $("#err-" + key); if (el) { el.hidden = true; const f = el.closest(".field"); if (f) f.classList.remove("is-bad"); } }
  function collect() {
    const errs = [];
    const article = $("#f-article").value.trim(), name = $("#f-name").value.trim();
    const opt = parseMoney($("#f-opt").value), retail = parseMoney($("#f-retail").value);
    ["article", "name", "opt", "retail", "sizes", "photos"].forEach(hideFieldError);
    if (!article) errs.push(["article", "Укажите артикул"]);
    if (!name) errs.push(["name", "Укажите название"]);
    if (!(opt > 0)) errs.push(["opt", "Укажите оптовую цену числом"]);
    if (!(retail > 0)) errs.push(["retail", "Укажите розничную цену числом"]);
    if (!state.sizes.length) errs.push(["sizes", "Отметьте хотя бы один размер"]);
    if (state.photos.length < 3) errs.push(["photos", "Нужно минимум 3 фото: они уходят в пост канала"]);
    if (!state.editing) {
      const dup = state.data.products.find((p) => p.article.toLowerCase() === article.toLowerCase());
      if (dup) errs.push(["article", "Такой артикул уже есть в каталоге"]);
    }
    if (/производ/i.test(name + " " + $("#f-desc").value)) errs.push(["name", "Не используем слова «производство» и «производитель»"]);
    errs.forEach(([k, m]) => showFieldError(k, m));
    if (errs.length) { const first = $("#err-" + errs[0][0]); first.scrollIntoView({ block: "center", behavior: "smooth" }); return null; }
    return {
      article, name, category: $("#f-category").value, priceWholesale: opt, priceRetail: retail, sizes: sortSizes(state.sizes),
      colors: $("#f-colors").value.split(",").map((s) => s.trim()).filter(Boolean),
      material: $("#f-material").value.trim(), availability: $("#f-avail").value, description: $("#f-desc").value.trim(),
    };
  }
  async function buildPhotos() {
    let q = 0.9;
    for (let round = 0; round < 4; round++) {
      const out = []; let total = 0;
      for (const ph of state.photos) {
        if (ph.keep) { out.push({ keep: ph.keep }); continue; }
        const blob = q < 0.9 ? await shrink(ph.data, q) : ph.data;
        const b64 = await toB64(blob); total += b64.length; out.push({ data: b64 });
      }
      if (total <= PAYLOAD_BUDGET) return out;
      q -= 0.12;
    }
    throw new Error("Новых фото слишком много для одной отправки. Сохраните модель с тремя-четырьмя фото, остальные добавьте вторым сохранением.");
  }

  const STEPS = [
    ["images", "Готовим фото", "сайт, каталог и пост"],
    ["pdf", "Пересобираем оптовый прайс", "PDF с миниатюрами"],
    ["site", "Сохраняем на сайт", "одним изменением в репозитории"],
    ["telegram", "Канал в Telegram", "пост и кнопка «Заказать»"],
    ["app", "Каталог в Telegram", "Mini App"],
    ["deploy", "Сайт обновляется", "обычно 1–2 минуты"],
  ];
  function openPublish(title, steps) {
    $("#pub-title").textContent = title;
    const ol = $("#steps"); ol.innerHTML = "";
    for (const [id, label, note] of steps) {
      const li = document.createElement("li"); li.className = "step"; li.dataset.step = id;
      li.innerHTML = `<span class="step__dot"></span><div><div class="step__label">${esc(label)}</div><div class="step__note">${esc(note)}</div></div>`;
      ol.append(li);
    }
    $("#pub-result").innerHTML = ""; $("#pub-done").hidden = true; $("#publish").hidden = false;
  }
  function setStep(id, status, note) {
    const li = document.querySelector(`.step[data-step="${id}"]`); if (!li) return;
    li.className = "step is-" + status;
    const dot = li.querySelector(".step__dot");
    dot.innerHTML = status === "ok" ? '<svg class="ico"><use href="#i-check"/></svg>' : status === "warn" || status === "fail" ? '<svg class="ico"><use href="#i-warn"/></svg>' : "";
    if (note !== undefined) li.querySelector(".step__note").innerHTML = note;
  }
  $("#pub-done").addEventListener("click", () => { $("#publish").hidden = true; });

  $("#ed-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (state.busy) return;
    const product = collect(); if (!product) return;
    state.busy = true; $("#save-btn").disabled = true; $("#ed-error").hidden = true;
    openPublish(state.editing ? "Сохраняем изменения" : "Публикуем модель", STEPS);
    const order = ["images", "pdf", "site", "telegram", "app"];
    let k = 0; setStep(order[0], "run");
    const timer = setInterval(() => { if (k < order.length - 1) { setStep(order[k], "ok"); k++; setStep(order[k], "run"); } }, 3500);
    try {
      const photos = await buildPhotos();
      const r = await api("/save", { body: { id: state.editing ? state.editing.id : null, baseHead: state.data.head, product, photos } });
      clearInterval(timer);
      showReport(r, product);
      closeEditor();
      await reload();
      $("#pub-done").hidden = false; $("#pub-done").focus();
    } catch (ex) {
      clearInterval(timer);
      order.forEach((s) => { const li = document.querySelector(`.step[data-step="${s}"]`); if (li && !li.classList.contains("is-ok")) setStep(s, "", undefined); });
      setStep(order[k], "fail", esc(ex.message));
      $("#pub-result").innerHTML = `<p class="form-error">Изменения не сохранены. ${esc(ex.message)}</p>`;
      $("#pub-done").hidden = false; $("#pub-done").textContent = "Вернуться к карточке";
    } finally {
      state.busy = false; $("#save-btn").disabled = false;
    }
  });

  function showReport(r, product) {
    const by = Object.fromEntries((r.steps || []).map((s) => [s.step, s]));
    const site = by.site && by.site.commit;
    setStep("images", "ok", "готово");
    setStep("pdf", "ok", `готово, ${(r.pdfBytes / 1024 / 1024).toFixed(1).replace(".", ",")} МБ`);
    if (site && site.dry_run) setStep("site", "warn", "тестовый режим: изменения не записаны");
    else if (site && site.unchanged) setStep("site", "ok", "изменений нет");
    else setStep("site", "ok", site ? `сохранено <a href="${esc(site.url || "#")}" target="_blank" rel="noopener">${esc(String(site.sha).slice(0, 7))}</a>` : "сохранено");
    const tg = by.telegram || {};
    const dryText = { posted: "пост не отправлен", failed: "не получилось, см. ниже", deleted: "пост не удалён", kept: "пост оставлен", unchanged: "менять не понадобилось" };
    const tgText = tg.action === "queued" ? "обновится автоматически через GitHub, обычно за пару минут" : tg.dry_run && dryText[tg.action] ? dryText[tg.action] : tg.dry_run && String(tg.action || "").startsWith("edited") ? "пост не изменён (" + tg.action.slice(8) + ")" : { posted: "новый пост опубликован", unchanged: "менять не понадобилось", failed: "не получилось, см. ниже", kept: "пост оставлен", deleted: "пост удалён" }[tg.action]
      || (String(tg.action || "").startsWith("edited") ? "обновлено: " + tg.action.slice(8) : "без изменений");
    const tgLink = tg.post && !tg.dry_run ? ` · <a href="${esc(tg.post)}" target="_blank" rel="noopener">открыть пост</a>` : "";
    setStep("telegram", tg.action === "failed" ? "fail" : tg.action === "queued" ? "info" : tg.dry_run ? "warn" : "ok", (tg.dry_run ? "тестовый режим: " : "") + tgText + tgLink);
    if (by.app) setStep("app", "ok", "обновлён");
    else setStep("app", (r.warnings || []).some((w) => /Mini App/.test(w)) ? "fail" : "ok", (r.warnings || []).some((w) => /Mini App/.test(w)) ? "не обновился" : "обновлён вместе с сайтом");
    if (r.warnings && r.warnings.length) {
      $("#pub-result").innerHTML = `<ul class="warn-list">${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`;
    }
    if (r.pdfBytes && site && !site.unchanged) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "btn btn--ghost btn--small pdf-link"; b.id = "pub-pdf";
      b.innerHTML = '<svg class="ico"><use href="#i-down"/></svg>Скачать новый прайс (PDF)';
      b.onclick = () => downloadPdf(site.dry_run ? "" : site.sha, b);
      $("#pub-result").append(b);
    }
    $("#pub-title").textContent = product ? "Готово: " + product.article : "Готово";
    $("#pub-done").textContent = "Готово";
    if (site && site.sha && !site.dry_run && !site.unchanged) pollDeploy(site.sha); else setStep("deploy", "ok", site && site.dry_run ? "в тестовом режиме не запускается" : "изменений нет");
  }
  async function pollDeploy(sha) {
    setStep("deploy", "run", "обычно 1–2 минуты, окно можно закрыть");
    const t0 = Date.now();
    while (Date.now() - t0 < 6 * 60_000) {
      await new Promise((r) => setTimeout(r, 10_000));
      let s; try { s = await api("/status?sha=" + encodeURIComponent(sha)); } catch (_) { continue; }
      if (s.state === "unknown") { setStep("deploy", "ok", "запущено, сайт обновится через пару минут"); return; }
      if (s.state === "completed") {
        setStep("deploy", s.conclusion === "success" ? "ok" : "fail", s.conclusion === "success" ? "сайт обновлён" : `сборка не прошла · <a href="${esc(s.url)}" target="_blank" rel="noopener">подробности</a>`);
        return;
      }
    }
    setStep("deploy", "warn", "сборка идёт дольше обычного, проверьте сайт чуть позже");
  }

  // ---------- delete
  $("#del-btn").addEventListener("click", () => {
    const p = state.editing; if (!p) return;
    const withPost = $("#del-post").checked;
    $("#confirm-title").textContent = "Удалить " + p.article + "?";
    $("#confirm-text").textContent = "Модель пропадёт с сайта, из прайса и каталога в Telegram. " +
      (withPost ? "Пост в канале тоже уберём. Если посту больше двух дней, Telegram не даст удалить его автоматически. Тогда мы его очистим, а здесь появится напоминание удалить пост вручную." : "Пост в канале останется.");
    const dlg = $("#confirm");
    dlg.returnValue = "";
    dlg.showModal();
    dlg.onclose = async () => {
      if (dlg.returnValue !== "ok") return;
      state.busy = true;
      openPublish("Удаляем " + p.article, [["site", "Убираем с сайта и из прайса", "одним изменением"], ["telegram", "Канал в Telegram", withPost ? "удаляем пост" : "пост остаётся"], ["app", "Каталог в Telegram", "Mini App"], ["deploy", "Сайт обновляется", "обычно 1–2 минуты"]]);
      setStep("site", "run");
      try {
        const r = await api("/delete", { body: { id: p.id, deletePost: withPost } });
        showReport(r, null);
        $("#pub-title").textContent = "Удалено: " + p.article;
        if (withPost) blankHint();
        closeEditor(); await reload();
        $("#pub-done").hidden = false; $("#pub-done").focus();
      } catch (ex) {
        setStep("site", "fail", esc(ex.message));
        $("#pub-done").hidden = false; $("#pub-done").textContent = "Закрыть";
      } finally { state.busy = false; }
    };
  });

  // ---------- files: price PDF, Excel table
  function saveB64(b64, filename, type) {
    const bin = atob(b64); const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    const url = URL.createObjectURL(new Blob([buf], { type }));
    const a = document.createElement("a"); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  }
  function today() { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function fileStatus(text, bad) { const el = $("#files-status"); el.textContent = text || ""; el.classList.toggle("is-bad", !!bad); }
  async function busyButton(btn, label, fn) {
    if (btn.dataset.busy) return; btn.dataset.busy = "1";
    const html = btn.innerHTML; btn.disabled = true; btn.setAttribute("aria-disabled", "true");
    btn.innerHTML = `<svg class="ico"><use href="#i-down"/></svg>${esc(label)}`;
    try { await fn(); } finally { btn.innerHTML = html; btn.disabled = false; btn.removeAttribute("aria-disabled"); delete btn.dataset.busy; }
  }
  async function downloadPdf(sha, btn) {
    await busyButton(btn, "Готовим PDF…", async () => {
      try {
        const r = await api("/pdf" + (sha ? "?sha=" + encodeURIComponent(sha) : ""));
        saveB64(r.data, `ESLAVIA-optovyy-prays-${today()}.pdf`, "application/pdf");
        if (btn.id === "pdf-btn") fileStatus("");
      } catch (ex) {
        if (btn.id === "pdf-btn") fileStatus(ex.message, true); else alert(ex.message);
      }
    });
  }
  $("#pdf-btn").addEventListener("click", (e) => downloadPdf("", e.currentTarget));
  $("#xlsx-btn").addEventListener("click", (e) => busyButton(e.currentTarget, "Собираем таблицу…", async () => {
    try {
      const r = await api("/export");
      saveB64(r.data, r.filename || `ESLAVIA-katalog-${today()}.xlsx`, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
      fileStatus(`Таблица скачана: ${r.count} моделей`);
    } catch (ex) { fileStatus(ex.message, true); }
  }));
  $("#xlsx-up").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("#xlsx-input").click(); } });
  const imp = { data: null, preview: null, name: "" };
  $("#xlsx-input").addEventListener("change", async (e) => {
    const f = e.target.files[0]; e.target.value = "";
    if (!f) return;
    if (!/\.xlsx$/i.test(f.name)) { fileStatus("Нужен файл Excel в формате .xlsx", true); return; }
    if (f.size > 2_500_000) { fileStatus("Файл слишком большой", true); return; }
    fileStatus("Проверяем таблицу…");
    try {
      imp.data = await toB64(f); imp.name = f.name;
      imp.preview = await api("/import-preview", { body: { data: imp.data } });
      fileStatus("");
      renderImport();
    } catch (ex) { fileStatus(ex.message, true); }
  });
  function renderImport() {
    const d = imp.preview;
    const n = { ch: d.changes.length, add: d.added.length, del: d.missing.length, err: d.errors.length };
    $("#imp-file").textContent = `${imp.name} · строк с моделями: ${d.rowsRead}`;
    let h = "";
    const total = n.ch + n.add + n.del;
    if (n.err) {
      h += `<p class="form-error">В таблице ${n.err} ${plural(n.err, "ошибка", "ошибки", "ошибок")}. Исправьте их в файле и загрузите его снова, до этого ничего не применяется.</p>`;
      h += `<h3 class="imp-h">Ошибки</h3><table class="imp-err"><tbody>${d.errors.map((x) => `<tr><td>Строка ${x.row}</td><td>${x.column ? esc(x.column) + ": " : ""}${esc(x.message)}</td></tr>`).join("")}</tbody></table>`;
    }
    if (!total && !n.err) h += `<p class="imp-none">Изменений нет. Таблица совпадает с каталогом на сайте.</p>`;
    if (total) {
      h += `<ul class="imp-sum"><li>Изменено: <b>${n.ch}</b></li><li>Новых: <b>${n.add}</b></li><li class="${n.del ? "is-del" : ""}">Удаляется: <b>${n.del}</b></li></ul>`;
    }
    if (n.del) {
      h += `<div class="imp-del"><p>Этих моделей нет в таблице, они будут удалены с сайта, из прайса, из Mini App и из канала:</p><ul>${d.missing.map((x) => `<li><b>${esc(x.article)}</b> ${esc(x.name || "")}</li>`).join("")}</ul></div>`;
    }
    if (n.ch) {
      h += `<h3 class="imp-h">Изменения</h3><ul class="imp-list">${d.changes.map((x) => `<li class="imp-item"><div class="imp-item__head">${esc(x.article)}<span>строка ${x.row}</span></div><dl class="imp-ch">${x.fields.map((f) => `<dt>${esc(f.label)}</dt><dd><span class="imp-old">${esc(f.old) || "пусто"}</span><span class="imp-arrow">→</span><span class="imp-new">${esc(f.new) || "пусто"}</span></dd>`).join("")}</dl></li>`).join("")}</ul>`;
    }
    if (n.add) {
      h += `<h3 class="imp-h">Новые модели</h3><ul class="imp-list">${d.added.map((x) => `<li class="imp-item"><div class="imp-item__head">${esc(x.article)}<span>строка ${x.row}, пока без фото</span></div></li>`).join("")}</ul>`;
    }
    const fresh = d.newCategories || [];
    if (fresh.length) {
      h += `<div class="imp-newcat"><p>Этих категорий нет в каталоге:</p><ul>${fresh.map((x) => {
        const rows = x.rows || [];
        const shown = rows.slice(0, 8).join(", ");
        const more = rows.length > 8 ? ` и ещё ${rows.length - 8}` : "";
        return `<li><b>${esc(x.name)}</b> — строки ${shown}${more}</li>`;
      }).join("")}</ul></div>`;
    }
    const warns = (d.warnings || []).filter((w) => !/новая модель/.test(w));
    if (warns.length) h += `<ul class="warn-list">${warns.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`;
    $("#imp-body").innerHTML = h;
    const conf = $("#imp-del-confirm");
    conf.hidden = !(n.del && !n.err);
    $("#imp-del-check").checked = false;
    $("#imp-del-label").textContent = `Удалить ${n.del} ${plural(n.del, "модель", "модели", "моделей")} с сайта, из прайса и из канала`;
    const freshOk = (d.newCategories || []).length && !n.err;
    const catConf = $("#imp-cat-confirm");
    catConf.hidden = !freshOk;
    $("#imp-cat-check").checked = false;
    $("#imp-cat-label").textContent = (d.newCategories || []).length === 1
      ? `Добавить категорию «${d.newCategories[0].name}»`
      : `Добавить эти категории (${(d.newCategories || []).length})`;
    if (n.del && !n.err) $("#imp-body").insertAdjacentHTML("beforeend", `<p class="imp-note">Если посту больше двух дней, Telegram не даст удалить его автоматически. Тогда мы такой пост очистим, а здесь появится напоминание удалить пост вручную.</p>`);
    const apply = $("#imp-apply");
    apply.hidden = !(total || freshOk) || n.err > 0;
    apply.textContent = "Применить";
    gateApply();
    $("#imp-cancel").textContent = total && !n.err ? "Отмена" : "Закрыть";
    $("#import").hidden = false;
    $("#import .publish__card").scrollTop = 0;
  }
  function gateApply() {
    const d = imp.preview;
    if (!d) return;
    const needDel = d.missing.length > 0 && !$("#imp-del-check").checked;
    const needCat = (d.newCategories || []).length > 0 && !$("#imp-cat-check").checked;
    $("#imp-apply").disabled = needDel || needCat;
  }
  $("#imp-del-check").addEventListener("change", gateApply);
  $("#imp-cat-check").addEventListener("change", gateApply);
  $("#imp-cancel").addEventListener("click", () => { $("#import").hidden = true; imp.data = null; imp.preview = null; });
  $("#imp-apply").addEventListener("click", async () => {
    const d = imp.preview; if (!d || state.busy) return;
    if (d.missing.length && !$("#imp-del-check").checked) return;
    state.busy = true; $("#import").hidden = true;
    openPublish("Применяем таблицу", [
      ["pdf", "Пересобираем оптовый прайс", "PDF с миниатюрами"],
      ["site", "Сохраняем на сайт", "одним изменением в репозитории"],
      ["telegram", "Канал в Telegram", "подписи постов" + (d.missing.length ? " и удаление" : "")],
      ["app", "Каталог в Telegram", "Mini App"],
      ["deploy", "Сайт обновляется", "обычно 1–2 минуты"],
    ]);
    setStep("pdf", "run");
    const t = setTimeout(() => { setStep("pdf", "ok"); setStep("site", "run"); }, 6000);
    try {
      const r = await api("/import-apply", { body: {
        data: imp.data,
        signature: d.signature,
        confirmDelete: d.missing.length,
        confirmCategories: (d.newCategories || []).map((x) => x.name),
      } });
      clearTimeout(t);
      if (r.unchanged) { setStep("pdf", "ok", "не понадобилось"); setStep("site", "ok", "изменений нет"); setStep("telegram", "ok", "без изменений"); setStep("app", "ok", "без изменений"); setStep("deploy", "ok", "изменений нет"); }
      else {
        showReport(r, null);
        const c = r.counts || {};
        $("#pub-title").textContent = "Готово: " + [c.changed ? `изменено ${c.changed}` : "", c.added ? `добавлено ${c.added}` : "", c.deleted ? `удалено ${c.deleted}` : ""].filter(Boolean).join(", ");
        if (r.steps && r.steps.some((s) => s.step === "telegram" && s.jobs === 0)) setStep("telegram", "ok", "менять не понадобилось");
        if (c.deleted) blankHint();
      }
      imp.data = null; imp.preview = null;
      await reload();
      $("#pub-done").hidden = false; $("#pub-done").focus();
    } catch (ex) {
      clearTimeout(t);
      setStep("site", "fail", esc(ex.message));
      $("#pub-result").innerHTML = `<p class="form-error">Изменения не применены. ${esc(ex.message)}</p>`;
      $("#pub-done").hidden = false; $("#pub-done").textContent = "Закрыть";
    } finally { state.busy = false; }
  });
  function renderQueue() {
    const q = (state.data && state.data.tgQueue) || [];
    $("#tg-queue").hidden = !q.length;
    if (!q.length) return;
    const arts = q.slice(0, 6).map((x) => x.article).join(", ") + (q.length > 6 ? " и ещё " + (q.length - 6) : "");
    $("#tg-queue-text").textContent = `${q.length} ${plural(q.length, "пост в канале обновится", "поста в канале обновятся", "постов в канале обновятся")} автоматически в течение пары минут: ${arts}.`;
  }
  function blankHint() {
    const el = document.createElement("p");
    el.className = "imp-note";
    el.textContent = "Если посту больше двух дней, Telegram не даст удалить его автоматически. Тогда мы его очистим, а здесь появится напоминание удалить пост вручную. Новая модель может сама занять очищенный пост.";
    $("#pub-result").append(el);
  }
  function renderBlank() {
    const b = (state.data && state.data.blankPosts) || [];
    $("#tg-blank").hidden = !b.length;
    if (!b.length) return;
    $("#tg-blank-text").textContent = b.length === 1
      ? "Один пост в канале нужно удалить вручную. Модель с сайта убрана, а пост был старше двух дней, и Telegram не дал удалить его автоматически, поэтому мы его очистили. Откройте пост, удалите его в канале и отметьте здесь. Если раньше добавите новую модель, она сама займёт этот пост, и напоминание пропадёт."
      : `${b.length} ${plural(b.length, "пост", "поста", "постов")} в канале нужно удалить вручную. Модели с сайта убраны, а посты были старше двух дней, и Telegram не дал удалить их автоматически, поэтому мы их очистили. Откройте каждый пост, удалите его в канале и отметьте здесь. Новые модели будут сами занимать эти посты, и напоминания будут пропадать.`;
    $("#tg-blank-list").innerHTML = b.map((x) => {
      const mid = x.mids[0];
      const d = String(x.date || "").split("-").reverse().join(".");
      return `<li class="blank-item"><a href="https://t.me/eslavia_opt/${mid}" target="_blank" rel="noopener">Пост ${esc(x.article)}</a><span class="blank-item__meta">${esc([x.category, d ? "очищен " + d : ""].filter(Boolean).join(" · "))}</span><button class="btn btn--quiet btn--small" type="button" data-blank="${mid}">Я удалила пост</button></li>`;
    }).join("");
  }
  $("#tg-blank-list").addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-blank]"); if (!btn) return;
    btn.disabled = true; btn.textContent = "Отмечаем…";
    try {
      await api("/blank-done", { body: { mid: Number(btn.dataset.blank) } });
      state.data.blankPosts = (state.data.blankPosts || []).filter((x) => String(x.mids[0]) !== btn.dataset.blank);
      renderBlank();
      fileStatus("Отметили, напоминание убрано");
    } catch (ex) { btn.disabled = false; btn.textContent = "Я удалила пост"; fileStatus(ex.message, true); }
  });
  $("#tg-retry").addEventListener("click", async (e) => {
    const b = e.currentTarget; b.disabled = true; const label = b.textContent; b.textContent = "Проверяем…";
    try { await reload(); if (!(state.data.tgQueue || []).length) fileStatus("Посты в канале обновлены"); }
    finally { b.disabled = false; b.textContent = label; }
  });
  // ---------- change log
  const LOG_ACTIONS = {
    add: "Добавлена", edit: "Изменена", delete: "Удалена", import: "Импорт из Excel",
    "import-add": "Добавлена из Excel", "import-edit": "Изменена из Excel", "import-delete": "Удалена из Excel",
    tg: "Пост в канале", nav: "Навигация в канале", "blank-done": "Пустой пост удалён",
  };
  const LOG_FILTERS = [["", "Все"], ["edit", "Изменения"], ["add", "Добавления"], ["delete", "Удаления"], ["import", "Excel"], ["tg", "Канал"]];
  const MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
  const logState = { model: "", action: "", offset: 0, total: 0, seq: 0, timer: null, lastDay: "" };
  function logWhen(iso) {
    const m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(iso || "");
    if (!m) return { day: "", time: "" };
    const now = new Date(Date.now() + 3 * 3600_000).toISOString().slice(0, 10); // Moscow date
    const y = new Date(Date.now() - 21 * 3600_000).toISOString().slice(0, 10);
    const date = `${m[1]}-${m[2]}-${m[3]}`;
    const day = date === now ? "Сегодня" : date === y ? "Вчера" : `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]}${m[1] !== now.slice(0, 4) ? " " + m[1] : ""}`;
    return { day, time: `${m[4]}:${m[5]}` };
  }
  function renderLogFilters() {
    $("#log-filters").innerHTML = LOG_FILTERS.map(([k, label]) =>
      `<button type="button" class="filter" role="tab" data-act="${k}" aria-selected="${logState.action === k}">${esc(label)}</button>`).join("");
  }
  function logChanges(e) {
    const ch = e.changes || [];
    if (!ch.length) return "";
    const fresh = ch.every((c) => !c.old);
    if (fresh) return `<p class="log__fresh">${ch.map((c) => `<span>${esc(c.label)}: <b>${esc(c.new)}</b></span>`).join("")}</p>`;
    return `<dl class="log__ch">${ch.map((c) => `<div><dt>${esc(c.label)}</dt><dd>${c.old ? `<span class="imp-old">${esc(c.old)}</span><span class="imp-arrow">→</span>` : ""}<span class="imp-new">${esc(c.new || "пусто")}</span></dd></div>`).join("")}</dl>`;
  }
  function logItem(e) {
    const w = logWhen(e.t);
    const kind = (e.action || "").replace("import-", "");
    const who = e.article
      ? `<button type="button" class="log__model" data-model="${esc(e.article)}" title="Показать историю модели">${esc(e.article)}</button>${e.name && e.name !== e.article ? `<span class="log__name">${esc(e.name)}</span>` : ""}`
      : "";
    const bits = [];
    if (e.note) bits.push(esc(e.note.charAt(0).toUpperCase() + e.note.slice(1)));
    if (e.post) bits.push(`<a href="https://t.me/eslavia_opt/${Number(e.post)}" target="_blank" rel="noopener">пост ${Number(e.post)}</a>`);
    const meta = [w.time, e.src === "Автоматически" ? "автоматически" : ""].filter(Boolean);
    if (e.sha && state.data) meta.push(`<a href="https://github.com/${esc(state.data.repo)}/commit/${esc(e.sha)}" target="_blank" rel="noopener" title="Сохранение на сайте">${esc(e.sha.slice(0, 7))}</a>`);
    let head = "";
    if (w.day && w.day !== logState.lastDay) { logState.lastDay = w.day; head = `<li class="log__day">${esc(w.day)}</li>`; }
    return head + `<li class="log__item log__item--${esc(kind)}">
      <div class="log__top"><span class="log__act">${esc(LOG_ACTIONS[e.action] || e.action)}</span>${who}</div>
      ${logChanges(e)}
      ${bits.length ? `<p class="log__note">${bits.join(" · ")}</p>` : ""}
      <p class="log__meta">${meta.join(" · ")}</p>
    </li>`;
  }
  async function loadLog(more) {
    const seq = ++logState.seq;
    if (!more) { logState.offset = 0; logState.lastDay = ""; $("#log-list").innerHTML = '<li class="empty">Загружаем журнал…</li>'; $("#log-more").hidden = true; $("#log-empty").hidden = true; }
    const btn = $("#log-more"); btn.disabled = true; if (more) btn.textContent = "Загружаем…";
    const qs = new URLSearchParams({ offset: String(logState.offset), limit: "30" });
    if (logState.model) qs.set("model", logState.model);
    if (logState.action) qs.set("action", logState.action);
    try {
      const r = await api("/log?" + qs.toString());
      if (seq !== logState.seq) return;
      if (!more) $("#log-list").innerHTML = "";
      $("#log-list").insertAdjacentHTML("beforeend", r.entries.map(logItem).join(""));
      logState.offset += r.entries.length; logState.total = r.total;
      btn.hidden = logState.offset >= r.total;
      const left = r.total - logState.offset;
      btn.textContent = left > 0 ? `Показать ещё (${left})` : "Показать ещё";
      $("#log-empty").hidden = r.total > 0;
      $("#log-empty").textContent = logState.model || logState.action
        ? "По этому запросу записей нет. Попробуйте другой артикул или сбросьте фильтр."
        : "Записей пока нет. Здесь появятся все изменения каталога: кто что поменял и когда.";
    } catch (ex) {
      if (seq !== logState.seq) return;
      if (!more) $("#log-list").innerHTML = "";
      $("#log-empty").hidden = false; $("#log-empty").textContent = ex.message;
    } finally { btn.disabled = false; }
  }
  function openLog(model) {
    logState.model = model || ""; logState.action = "";
    $("#log-search").value = logState.model;
    renderLogFilters();
    $("#journal").hidden = false; document.body.style.overflow = "hidden";
    $("#log-body").scrollTop = 0;
    loadLog(false);
    setTimeout(() => (model ? $("#log-close") : $("#log-search")).focus({ preventScroll: true }), 60);
  }
  function closeLog() { $("#journal").hidden = true; if ($("#editor").hidden) document.body.style.overflow = ""; }
  $("#log-btn").addEventListener("click", () => openLog(""));
  $("#ed-log").addEventListener("click", () => { if (state.editing) openLog(state.editing.article); });
  $("#log-close").addEventListener("click", closeLog);
  $("#journal").addEventListener("click", (e) => { if (e.target.id === "journal") closeLog(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#journal").hidden) { e.stopImmediatePropagation(); closeLog(); } }, true);
  $("#log-search").addEventListener("input", (e) => {
    clearTimeout(logState.timer);
    logState.timer = setTimeout(() => { logState.model = e.target.value.trim(); loadLog(false); }, 300);
  });
  $("#log-filters").addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]"); if (!b) return;
    logState.action = b.dataset.act; renderLogFilters(); loadLog(false);
  });
  $("#log-list").addEventListener("click", (e) => {
    const b = e.target.closest("[data-model]"); if (!b) return;
    logState.model = b.dataset.model; $("#log-search").value = logState.model; loadLog(false);
  });
  $("#log-more").addEventListener("click", () => loadLog(true));

  function plural(n, one, few, many) { const a = Math.abs(n) % 100, b = a % 10; return a > 10 && a < 20 ? many : b > 1 && b < 5 ? few : b === 1 ? one : many; }

  // ---------- utils
  function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function num(v) { const n = Number(v); return Number.isInteger(n) ? String(n) : String(n).replace(".", ","); }
  function parseMoney(v) { const n = Number(String(v).replace(/\s|₽/g, "").replace(",", ".")); return Number.isFinite(n) ? n : NaN; }
  function money(v) { return Math.round(Number(v)).toLocaleString("ru-RU").replace(/\u00a0/g, " ") + " ₽"; }

  if (token()) openApp(); else showLogin();
})();
