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
  const data = await fetch("../data/entries.json").then(r => r.json());

  // Apply theme vars from settings.json
  const bg = settings.background || {};
  document.documentElement.style.setProperty("--bg", bg.color || "#0b0b0c");
  document.documentElement.style.setProperty("--fg", bg.text_color || "#f2f2f2");
  document.documentElement.style.setProperty("--muted", bg.muted_color || "#b8b8b8");
  document.documentElement.style.setProperty("--card", bg.card_color || "rgba(255,255,255,0.06)");
  document.documentElement.style.setProperty("--border", bg.border_color || "rgba(255,255,255,0.12)");
  document.documentElement.style.setProperty("--font", bg.font_family || "ui-sans-serif, system-ui");

  if (bg.image_url) {
    document.body.style.backgroundImage = `url("${bg.image_url}")`;
    document.body.style.backgroundSize = "cover";
    document.body.style.backgroundAttachment = "fixed";
  }

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

    return `
      <article class="entry">
        <div class="meta">
          <span class="date">${date}</span>
          <span class="cat">${emoji}${escapeHtml(e.category || "")}</span>
        </div>
        <div class="text">${text}${link}${photo}</div>
      </article>
    `;
  }).join("");
}

main().catch(err => {
  console.error(err);
  document.getElementById("entries").textContent = "Failed to load entries.";
});

