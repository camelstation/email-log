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

  // ---- Theme + random gradient background (from settings.json) ----
  const bg = (settings && settings.background) ? settings.background : {};

  // Apply text colors as CSS variables (your CSS should use --fg and --muted)
  if (bg.text_color) document.documentElement.style.setProperty("--fg", bg.text_color);
  if (bg.muted_color) document.documentElement.style.setProperty("--muted", bg.muted_color);

  // Choose background
  if (bg.type === "random_gradient" && Array.isArray(bg.gradients) && bg.gradients.length > 0) {
    // Pick one per day (stable across refreshes)
    const key = "email-log-gradient-v1";
    const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

    let chosenIndex = null;
    try {
      const cached = JSON.parse(localStorage.getItem(key) || "null");
      if (cached && cached.date === today && typeof cached.index === "number") {
        chosenIndex = cached.index;
      }
    } catch {}

    if (chosenIndex === null) {
      chosenIndex = Math.floor(Math.random() * bg.gradients.length);
      localStorage.setItem(key, JSON.stringify({ date: today, index: chosenIndex }));
    }

    document.body.style.background = bg.gradients[chosenIndex];

  } else if (bg.type === "gradient" && bg.gradient) {
    document.body.style.background = bg.gradient;

  } else if (bg.color) {
    document.body.style.background = bg.color;
  }


  const data = await fetch("./data/entries.json").then(r => r.json());

  // Apply theme vars from settings.json
  const bg = settings.background || {};
  document.documentElement.style.setProperty("--bg", bg.color || "#0b0b0c");
  document.documentElement.style.setProperty("--fg", bg.text_color || "#f2f2f2");
  document.documentElement.style.setProperty("--muted", bg.muted_color || "#b8b8b8");
  document.documentElement.style.setProperty("--card", bg.card_color || "rgba(255,255,255,0.06)");
  document.documentElement.style.setProperty("--border", bg.border_color || "rgba(255,255,255,0.12)");
  document.documentElement.style.setProperty("--font", bg.font_family || "ui-sans-serif, system-ui");

  document.title = settings.title || "Log";
  document.getElementById("title").textContent = settings.title || "Log";
  document.getElementById("header").textContent = settings.header || "";
  document.getElementById("footer").textContent = settings.footer || "";

  const entriesEl = document.getElementById("entries");
  const entries = (data.entries || []);

  const categories = settings.categories || {};

  entriesEl.innerHTML = entries.map(e => {
    const emoji = (e.category && categories[e.category.toLowerCase()]) ? categories[e.category.toLowerCase()] + " " : "";
    const date = escapeHtml(e.date || "");
    const text = escapeHtml(e.text || "");

    const link = e.link_url ? ` <a href="${escapeHtml(e.link_url)}" target="_blank" rel="noopener">[link]</a>` : "";
    const photo = e.photo_url ? ` <a href="${escapeHtml(e.photo_url)}" target="_blank" rel="noopener">[photo]</a>` : "";

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
  document.getElementById("entries").textContent = "Failed to load entries.";
});

