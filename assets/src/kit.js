// Turns <div class="win dark" data-src="app/home-dark.png"></div> into a framed window,
// and <svg class="wave"> into the noisy-to-clean waveform used on the banner.
document.querySelectorAll(".win[data-src]").forEach((w) => {
  const dark = w.classList.contains("dark");
  const stroke = dark ? "#C9C9CF" : "#3A3A40";
  const line = (d) => `<svg viewBox="0 0 46 32"><path d="${d}" stroke="${stroke}" stroke-width="1" fill="none"/></svg>`;
  w.innerHTML = `
    <div class="bar"><img src="../logo.svg" alt=""><span>NoiseFree</span>
      <span class="ctl">${line("M18 16.5h10")}${line("M18.5 11.5h9v9h-9z")}${line("M18 11l10 10M28 11L18 21")}</span>
    </div>
    <img class="app" src="${w.dataset.src}" alt="">`;
});

function rand(seed) {
  return () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
}

document.querySelectorAll("svg.wave").forEach((svg) => {
  const W = +svg.getAttribute("width"), H = +svg.getAttribute("height");
  const mid = H / 2, bars = +svg.dataset.bars || 64, gap = W / bars, r = rand(7);
  const hub = W / 2, hubR = +svg.dataset.hub || 54;
  let out = "";
  for (let i = 0; i < bars; i++) {
    const x = i * gap + gap / 2;
    if (Math.abs(x - hub) < hubR + gap) continue;
    // speech envelope: two syllables per side
    const t = i / bars;
    const voice = Math.max(0, Math.sin(t * Math.PI * 6)) ** 1.6 * 0.82;
    const clean = x > hub;
    const noise = clean ? 0.02 : 0.08 + r() * 0.22;
    const h = Math.max(4, (clean ? voice : Math.min(1, voice * 0.85 + noise * (0.5 + r()))) * (H - 8));
    const color = clean ? "var(--teal-400)" : "rgba(160,176,173,.55)";
    out += `<rect x="${x - gap * 0.28}" y="${mid - h / 2}" width="${gap * 0.56}" height="${h}" rx="${gap * 0.28}" fill="${color}"/>`;
  }
  out += `<circle cx="${hub}" cy="${mid}" r="${hubR + 14}" fill="rgba(45,212,191,.10)"/>`;
  out += `<image href="../logo.svg" x="${hub - hubR}" y="${mid - hubR}" width="${hubR * 2}" height="${hubR * 2}"/>`;
  svg.innerHTML = out;
});
