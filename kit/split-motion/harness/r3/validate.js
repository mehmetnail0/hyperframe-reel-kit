// Validate a round-3 composition headless: JS errors, overflow / device clipping, density per section.
// usage: node validate.js PAGE.html SECTIONS.json OUT.json      (SECTIONS = [{sid,t0,t1}], panel geometry from G in page)
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, secPath, out] = process.argv.slice(2);
  const secs = JSON.parse(fs.readFileSync(secPath, 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 2040 } });
  const errs = [];
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message.slice(0, 300)));
  page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });
  await page.goto('file://' + html, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => !!(window.__timelines && window.__timelines.main), null, { timeout: 40000, polling: 200 });
  const res = { errors: errs, sections: [] };
  res.r3err = await page.evaluate(() => window.__r3err || []);
  for (const s of secs) {
    const r = await page.evaluate(([sid, t0, t1, skip]) => {
      const tl = window.__timelines.main, G = window.G;
      const sec = document.getElementById(sid);
      const vis = (el) => el.checkVisibility({ opacityProperty: true, visibilityProperty: true });
      const samples = [], over = new Set(), dev = new Set();
      for (let t = t0 + .5; t < t1 - .45; t += .1) {
        if ((skip || []).some(([a, b]) => t >= a - .1 && t < b + .3)) continue;  // full-screen speaker: panel hidden
        tl.seek(t, false);
        let n = 0, groups = new Set();
        sec.querySelectorAll('.r3-el').forEach((el) => {
          if (!vis(el)) return;
          const op = +getComputedStyle(el).opacity; if (op < .08) return;
          const b = el.getBoundingClientRect(); if (b.width < 3 || b.height < 3) return;
          if (b.bottom < 0 || b.top > G.H || b.right < 0 || b.left > 1080) return;
          n++;
          // top-level structure this element belongs to (direct child of a layer)
          let p = el; while (p.parentElement && !p.parentElement.classList.contains('r3-layer')) p = p.parentElement;
          groups.add(p);
          if (b.left < 14 || b.right > 1066 || b.top < 136 || b.bottom > G.bottom + 14) over.add((el.className || '').toString().slice(0, 30) + '@' + t.toFixed(1) + ` box ${Math.round(b.left)},${Math.round(b.top)}-${Math.round(b.right)},${Math.round(b.bottom)}`);
          const d = el.closest('[data-device]');
          if (d && d !== el) { const D = d.getBoundingClientRect(); if (b.left < D.left - 2 || b.right > D.right + 2 || b.top < D.top - 2 || b.bottom > D.bottom + 2) dev.add(t.toFixed(1)); }
        });
        samples.push([n, groups.size]);
      }
      const N = samples.length || 1;
      return { sid, n: samples.length,
        share_ge3: samples.filter((x) => x[0] >= 3).length / N,
        lonely_share: samples.filter((x) => x[0] <= 1 || x[1] <= 1 && x[0] <= 2).length / N,
        mean_elements: samples.reduce((a, x) => a + x[0], 0) / N,
        overflow: [...over].slice(0, 8), device_overflow: [...dev].slice(0, 8) };
    }, [s.sid, s.t0, s.t1, s.skip || []]);
    res.sections.push(r);
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(res, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
