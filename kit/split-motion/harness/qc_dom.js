// DOM QC: load the composition headless, seek the GSAP timeline to every beat, measure
// what each scene actually draws, and report anything outside the safe stage or in the
// Instagram danger zones. usage: node qc_dom.js INDEX.html BEATS.json OUT.json
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, beatsPath, out] = process.argv.slice(2);
  const beats = JSON.parse(fs.readFileSync(beatsPath, 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 2040 } });
  await page.goto('file://' + html, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.__timelines && window.__timelines.main, null, { timeout: 40000 });
  await page.evaluate(() => document.fonts.ready);
  const res = [];
  for (const b of beats) {
    if (!b.sid) continue;
    const t = b.t0 + Math.min(1.6, (b.t1 - b.t0) * 0.7);
    const r = await page.evaluate(([sid, t]) => {
      const tl = window.__timelines.main; tl.seek(t, false);
      const root = document.getElementById(sid);
      if (!root) return null;
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
      root.querySelectorAll('*').forEach((el) => {
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || +cs.opacity === 0) return;
        const hasInk = el.childElementCount === 0 || el.tagName === 'svg' || cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || cs.borderTopWidth !== '0px';
        if (!hasInk) return;
        const q = el.getBoundingClientRect();
        if (q.width < 2 || q.height < 2) return;
        x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom); n++;
      });
      return n ? { x0, y0, x1, y1, n } : null;
    }, [b.sid, t]);
    res.push({ sid: b.sid, t, layout: b.layout, box: r });
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(res, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
