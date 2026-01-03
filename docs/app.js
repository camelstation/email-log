function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function main() {
  const settings = await fetch("./settings.json").then(r => r.json());
  const data = await fetch("./data/entries.json").then(r => r.json());

  // Theme + background
  const bg = settings.background || {};

  // text colors
  document.documentElement.style.setProperty("--fg", bg.text_color || "#ffffff");
  document.documentElement.style.setProperty("--muted", bg.muted_color || "rgba(255,255,255,0.78)");

  // choose a background (store in --bg so CSS always uses it)
  if (bg.type === "random_gradient" && Array.isArray(bg.gradients) && bg.gradients.length > 0) {
    const key = "email-log-gradient-v1";
    const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

    let idx = null;
    try {
      const cached = JSON.parse(localStorage.getItem(key) || "null");
      if (cached && cached.date === today && typeof cached.index === "number") idx = cached.index;
    } catch {}

    if (idx === null) {
      idx = Math.floor(Math.random() * bg.gradients.length);
      localStorage.setItem(key, JSON.stringify({ date: today, index: idx }));
    }

    document.documentElement.style.setProperty("--bg", bg.gradients[idx]);
  } else if (bg.type === "gradient" && bg.gradient) {
    document.documentElement.style.setProperty("--bg", bg.gradient);
  } else {
    document.documentElement.style.setProperty("--bg", bg.color || "#0b0b0c");
  }

  // header/footer text
  document.title = settings.title || "Log";
  document.getElementById("title").textContent = settings.title || "Log";
  document.getElementById("header").textContent = settings.header || "";
  document.getElementById("footer").textContent = settings.footer || "";

  // render entries
  const entriesEl = document.getElementById("entries");
  const entries = (data.entries || []);
  const categories = settings.categories || {};

  entriesEl.innerHTML = entries.map(e => {
    const emoji = (e.category && categories[e.category.toLowerCase()])
      ? categories[e.category.toLowerCase()] + " "
      : "";

    const date = escapeHtml(e.date || "");
    const text = escapeHtml(e.text || "");

    const link = e.link_url
      ? ` <a href="${escapeHtml(e.link_url)}" target="_blank" rel="noopener">[link]</a>`
      : "";

    const photo = e.photo_url
      ? ` <a href="${escapeHtml(e.photo_url)}" target="_blank" rel="noopener">[photo]</a>`
      : "";

    const cat = e.category ? escapeHtml(e.category) : "";

    return `
      <article class="entry">
        <div class="line">
          <span class="date">${date}</span>
          <span class="cat">${emoji}${cat}</span>
          <span class="text">${text}${link}${photo}</span>
        </div>
      </article>
    `;
  }).join("");
}

main().catch(err => {
  console.error(err);
  const el = document.getElementById("entries");
  if (el) el.textContent = "Failed to load entries.";
});

