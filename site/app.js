"use strict";
const main = document.querySelector("main");
const el = (tag, txt, cls) => {
  const n = document.createElement(tag);
  if (txt !== undefined) n.textContent = txt;
  if (cls) n.className = cls;
  return n;
};
const append = (parent, ...kids) => {
  parent.append(...kids);
  return parent;
};
const button = (label, fn, cls) => {
  const n = el("button", label, cls);
  n.type = "button";
  n.onclick = fn;
  return n;
};
const route = (...parts) => "#" + parts.map(encodeURIComponent).join("/");
const a = (label, url, cls) => {
  const n = el("a", label, cls);
  n.href = url;
  return n;
};
const external = (label, url) => {
  const n = a(label, url, "button");
  n.rel = "noopener noreferrer";
  n.target = "_blank";
  return n;
};
let data,
  frame = 0;
function thumb(mod, index = 0) {
  if (!mod.previews.length) return el("div", "No preview", "placeholder");
  const image = el("img");
  image.src = mod.previews[index];
  image.alt = mod.title + " preview " + (index + 1);
  image.onerror = () => image.replaceWith(el("div", "Preview unavailable", "placeholder"));
  return image;
}
function showDetail(g, m) {
  main.append(a("← " + g.title, route("game", g.titleId), "crumb"));
  const gallery = el("div", undefined, "gallery"),
    text = el("article");
  function paint() {
    gallery.replaceChildren(thumb(m, frame));
    if (m.previews.length > 1)
      gallery.append(
        append(
          el("div", undefined, "actions"),
          button("←", () => {
            frame = (frame + m.previews.length - 1) % m.previews.length;
            paint();
          }),
          el("span", frame + 1 + " / " + m.previews.length),
          button("→", () => {
            frame = (frame + 1) % m.previews.length;
            paint();
          }),
        ),
      );
    const keys = gallery.querySelectorAll("button");
    if (keys.length) {
      keys[0].ariaLabel = "Previous preview";
      keys[1].ariaLabel = "Next preview";
    }
  }
  paint();
  const facts = el("div", undefined, "facts");
  for (const [k, v] of [
    ["Category", m.category],
    ["Version", m.version],
    ["Published", m.published],
    ["License", m.license],
  ])
    if (v) facts.append(append(el("div"), el("small", k), el("strong", v)));
  append(
    text,
    el("h1", m.title),
    el("p", "by " + m.author, "by"),
    el("p", m.summary),
    el("p", m.description),
    facts,
  );
  if (m.download) {
    const dl = a("Download ZIP", m.download.url, "button primary");
    dl.download = "";
    append(
      text,
      el("h3", "Package"),
      dl,
      el("p", m.download.bytes.toLocaleString() + " bytes · SHA-256"),
      el("code", m.download.sha256),
    );
  }
  const mirrors = m.sources.filter((s) => s.url.split("#")[0] !== m.sources[0].url.split("#")[0]);
  if (mirrors.length) {
    text.append(el("h3", "Community hosts"));
    text.append(
      append(el("div", undefined, "actions"), ...mirrors.map((s) => external(s.label + " ↗", s.url))),
    );
  }
  main.append(append(el("div", undefined, "detail"), gallery, text));
}
function browse(g, filter = "", value = "") {
  const choose = el("select");
  choose.ariaLabel = "Choose a game";
  for (const game of data.games) {
    const option = el("option", game.title);
    option.value = game.titleId;
    option.selected = g === game;
    choose.add(option);
  }
  choose.onchange = () => {
    location.hash = route("game", choose.value);
  };
  main.append(append(el("div", undefined, "row"), el("h1", "Mod store"), choose));
  const tabs = el("nav", undefined, "tabs");
  tabs.ariaLabel = "Browse community mods";
  const categories = [...new Set(g.mods.map((m) => m.category))];
  for (const [label, key, v] of [
    ["Discover", "", ""],
    ...categories.map((c) => [c, "category", c]),
    ["Hosts", "hosts", ""],
  ]) {
    const tab = button(label, () => {
      location.hash = route("game", g.titleId, key, v);
    });
    tab.setAttribute(
      "aria-pressed",
      String((filter === key && value === v) || (key === "hosts" && filter === "host")),
    );
    tabs.append(tab);
  }
  main.append(tabs);
  if (filter === "hosts") {
    main.append(el("h2", "Community hosts"), el("p", "Choose a host to see its releases for this game."));
    const hosts = [...new Set(g.mods.flatMap((m) => m.sources.map((s) => s.label)))];
    for (const host of hosts) {
      const count = g.mods.filter((m) => m.sources.some((s) => s.label === host)).length;
      main.append(
        button(
          host + "  ·  " + count + (count === 1 ? " release" : " releases") + "  →",
          () => {
            location.hash = route("game", g.titleId, "host", host);
          },
          "host",
        ),
      );
    }
    return;
  }
  let items = g.mods.filter((m) =>
    filter === "host"
      ? m.sources.some((s) => s.label === value)
      : filter === "category"
        ? m.category === value
        : true,
  );
  if (!items.length) {
    main.append(el("h2", "No releases yet"));
    return;
  }
  if (!filter) {
    const m = items[0];
    const hero = el("article", undefined, "feature");
    append(
      hero,
      append(
        el("div"),
        el("h2", m.title),
        el("p", "by " + m.author + "   ·   " + m.sources[0].label, "by"),
        el("p", m.summary),
        a("View mod", route("mod", g.titleId, m.id), "button primary"),
      ),
      thumb(m),
    );
    main.append(hero);
    items = items.slice(1);
    if (items.length) main.append(el("h2", "More for this game"));
  } else main.append(el("h2", value));
  const cards = el("div", undefined, "cards");
  for (const m of items)
    cards.append(
      append(
        a("", route("mod", g.titleId, m.id), "card"),
        thumb(m),
        append(el("div"), el("h3", m.title), el("p", "by " + m.author + " · " + m.sources[0].label)),
      ),
    );
  main.append(cards);
}
function render() {
  if (!data) return;
  frame = 0;
  main.replaceChildren();
  let parts;
  try {
    parts = location.hash.slice(1).split("/").map(decodeURIComponent);
  } catch {
    parts = [];
  }
  const [kind, tid, tag, value] = parts;
  const g = data.games.find((g) => g.titleId === tid) || data.games[0];
  if (!g) {
    main.append(el("h1", "No games yet"));
    return;
  }
  const m = kind === "mod" && g.mods.find((m) => m.id === tag);
  if (m) showDetail(g, m);
  else browse(g, kind === "game" ? tag : "", value);
  document.title = (m ? m.title : g.title) + " · " + data.name;
  main.focus({ preventScroll: true });
}
addEventListener("hashchange", render);
fetch("./catalog.json")
  .then((r) => {
    if (!r.ok) throw Error();
    return r.json();
  })
  .then((v) => {
    if (v.format !== "moader.catalog.v1") throw Error();
    data = v;
    document.querySelector("#repo-name").textContent = v.name;
    render();
  })
  .catch(() => {
    main.replaceChildren(el("h1", "Catalog unavailable"), el("p", "Refresh the page to try again."));
  });
