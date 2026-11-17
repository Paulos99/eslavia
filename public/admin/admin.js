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
        "Сорочки": "сорочка домашняя", "Халаты": "халат домашний", "Туники": "туника домашняя" }[$("#f-category").value] || "";
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
    const tgText = tg.dry_run && dryText[tg.action] ? dryText[tg.action] : tg.dry_run && String(tg.action || "").startsWith("edited") ? "пост не изменён (" + tg.action.slice(8) + ")" : { posted: "новый пост опубликован", unchanged: "менять не понадобилось", failed: "не получилось, см. ниже", kept: "пост оставлен", deleted: "пост удалён" }[tg.action]
      || (String(tg.action || "").startsWith("edited") ? "обновлено: " + tg.action.slice(8) : "без изменений");
    const tgLink = tg.post && !tg.dry_run ? ` · <a href="${esc(tg.post)}" target="_blank" rel="noopener">открыть пост</a>` : "";
    setStep("telegram", tg.action === "failed" ? "fail" : tg.dry_run ? "warn" : "ok", (tg.dry_run ? "тестовый режим: " : "") + tgText + tgLink);
    if (by.app) setStep("app", "ok", "обновлён");
    else setStep("app", (r.warnings || []).some((w) => /Mini App/.test(w)) ? "fail" : "ok", (r.warnings || []).some((w) => /Mini App/.test(w)) ? "не обновился" : "обновлён вместе с сайтом");
    if (r.warnings && r.warnings.length) {
      $("#pub-result").innerHTML = `<ul class="warn-list">${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`;
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
      (withPost ? "Пост в канале тоже будет удалён." : "Пост в канале останется.");
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
        closeEditor(); await reload();
        $("#pub-done").hidden = false; $("#pub-done").focus();
      } catch (ex) {
        setStep("site", "fail", esc(ex.message));
        $("#pub-done").hidden = false; $("#pub-done").textContent = "Закрыть";
      } finally { state.busy = false; }
    };
  });

  // ---------- utils
  function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function num(v) { const n = Number(v); return Number.isInteger(n) ? String(n) : String(n).replace(".", ","); }
  function parseMoney(v) { const n = Number(String(v).replace(/\s|₽/g, "").replace(",", ".")); return Number.isFinite(n) ? n : NaN; }
  function money(v) { return Math.round(Number(v)).toLocaleString("ru-RU").replace(/\u00a0/g, " ") + " ₽"; }

  if (token()) openApp(); else showLogin();
})();
