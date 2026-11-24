// Browser acceptance for Lab 04 (B1-B8) using Playwright + installed Chrome.
// Start the Flask server first. Run from the project root:
//   node tests/acceptance.js after    (or: before)
// Requires `playwright-core` resolvable via NODE_PATH or a local node_modules.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:5000';
const PHASE = process.argv[2] === 'after' ? 'after' : 'before';
const OUT = path.resolve(__dirname, '..', 'docs', 'captures');
fs.mkdirSync(OUT, { recursive: true });

const results = [];
function record(id, ok, detail) {
  results.push({ id, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${id} :: ${detail}`);
}
const shot = (name) => path.join(OUT, `${PHASE}-${name}.png`);

const SIM_DEFAULTS = {
  VCC: '12', R1: '100', R2: '22', RC: '2.2', RE: '1.0',
  RL: '10', CIN: '10', COUT: '10', amp_mv: '10', freq_hz: '1000',
};

async function setSim(page, values) {
  for (const [key, value] of Object.entries(values)) {
    await page.fill(`#sim_${key}`, String(value));
  }
}

async function runSim(page, analysis, values) {
  await setSim(page, values);
  await page.check(`input[name="analysis"][value="${analysis}"]`, { force: true });
  await page.click('.run-button');
  await page.waitForLoadState('domcontentloaded');
  // Either a success bar or an error block must appear.
  await page.waitForSelector('.run-bar, .sim-card .errors', { timeout: 90000 });
}

async function dcCalculator(page, mode, values) {
  if (mode) {
    await page.check(`input[name="mode"][value="${mode}"]`, { force: true });
    await page.click('button.ghost');           // "Change mode" (GET)
    await page.waitForLoadState('domcontentloaded');
  }
  for (const [key, value] of Object.entries(values)) {
    await page.fill(`#${key}`, String(value));
  }
  await page.click('button:has-text("Calculate DC Bias")');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('.result-card .hero-value', { timeout: 30000 });
  return (await page.textContent('.result-card')).replace(/\s+/g, ' ').trim();
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await desktop.newPage();
  page.on('console', (m) => { if (m.type() === 'error') console.log('  console.error:', m.text()); });

  // ---- B1: Lab 3 regression, all three bias modes ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  const divider = await dcCalculator(page, null, {
    VCC: '12', R1: '100', R2: '22', RC: '2.2', RE: '1.0', beta: '100', VBE: '0.70',
  });
  const okDivider = /1\.23/.test(divider) && /8\.05/.test(divider);
  record('B1a divider regression', okDivider, okDivider ? 'IC ~1.23 mA, VCE ~8.05 V' : divider.slice(0, 120));

  const fixed = await dcCalculator(page, 'fixed', {
    VCC: '12', RB: '1000', RC: '2.2', beta: '100', VBE: '0.70',
  });
  const okFixed = /1\.13/.test(fixed) && /9\.51/.test(fixed);
  record('B1b fixed regression', okFixed, okFixed ? 'IC ~1.13 mA, VCE ~9.51 V' : fixed.slice(0, 120));

  const emitter = await dcCalculator(page, 'emitter', {
    VCC: '12', RB: '1000', RC: '2.2', RE: '1.0', beta: '100', VBE: '0.70',
  });
  const okEmitter = /1\.03/.test(emitter) && /8\.71/.test(emitter);
  record('B1c emitter regression', okEmitter, okEmitter ? 'IC ~1.03 mA, VCE ~8.71 V' : emitter.slice(0, 120));
  await page.screenshot({ path: shot('b1-regression'), fullPage: true });

  // ---- B2: DC SPICE ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'dc', SIM_DEFAULTS);
  const dcText = (await page.textContent('.sim-card')).replace(/\s+/g, ' ').trim();
  const okDc = /Success/.test(dcText) && /ngspice-/.test(dcText) && /operating point/i.test(dcText) && /7\.75/.test(dcText);
  record('B2 DC SPICE', okDc, okDc ? 'real .op: VCE ~7.75 V, IC ~1.32 mA' : dcText.slice(0, 160));
  await page.screenshot({ path: shot('b2-dc-spice'), fullPage: true });

  // ---- B3: change RE and re-run, values must move ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'dc', { ...SIM_DEFAULTS, RE: '2.0' });
  const dc2 = (await page.textContent('.sim-card')).replace(/\s+/g, ' ').trim();
  const okRe = /Success/.test(dc2) && /9\.03/.test(dc2) && !/7\.754/.test(dc2);
  record('B3 change RE', okRe, okRe ? 'RE 2k changed .op (IC dropped, VCE changed)' : dc2.slice(0, 160));
  await page.screenshot({ path: shot('b3-re-change'), fullPage: true });

  // ---- B4: AC sweep ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'ac', SIM_DEFAULTS);
  const acCharts = await page.locator('svg.chart').count();
  const acText = (await page.textContent('.sim-card')).replace(/\s+/g, ' ').trim();
  const okAc = /Success/.test(acText) && /Gain at 1 kHz/.test(acText) && acCharts >= 2 && /Frequency \(Hz\)/.test(await page.innerHTML('.sim-card'));
  record('B4 AC sweep', okAc, okAc ? `gain + phase Bode, ${acCharts} SVG charts` : `charts=${acCharts}`);
  await page.screenshot({ path: shot('b4-ac'), fullPage: true });

  // ---- B5: Transient ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'tran', SIM_DEFAULTS);
  const tranText = (await page.textContent('.sim-card')).replace(/\s+/g, ' ').trim();
  const tranCharts = await page.locator('svg.chart').count();
  const okTran = /Success/.test(tranText) && /Vin peak/.test(tranText) && /inverted/.test(tranText) && tranCharts === 1;
  record('B5 transient', okTran, okTran ? 'Vin/Vout waveform, inverted (180 deg)' : tranText.slice(0, 160));
  await page.screenshot({ path: shot('b5-tran'), fullPage: true });

  // ---- B6: change source, waveform must change ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'tran', { ...SIM_DEFAULTS, amp_mv: '20', freq_hz: '2000' });
  const tran2 = (await page.textContent('.sim-card')).replace(/\s+/g, ' ').trim();
  const okSrc = /Success/.test(tran2) && /20\.00 mV/.test(tran2);
  record('B6 change source', okSrc, okSrc ? '20 mV / 2 kHz run reflected in Vin peak' : tran2.slice(0, 160));
  await page.screenshot({ path: shot('b6-source-change'), fullPage: true });

  // ---- B7: invalid input must fail loudly, no fake success ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'dc', { ...SIM_DEFAULTS, RE: '0' });
  const errText = (await page.textContent('.sim-card')).replace(/\s+/g, ' ').trim();
  const successBars = await page.locator('.run-bar').count();
  const okErr = /Simulation stopped/.test(errText) && /RE must be greater than/.test(errText) && successBars === 0;
  record('B7 invalid / fail', okErr, okErr ? 'RE=0 blocked with alert, no success bar' : errText.slice(0, 160));
  await page.screenshot({ path: shot('b7-error'), fullPage: true });

  // ---- B8: responsive UI (desktop + phone) ----
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(page, 'ac', SIM_DEFAULTS);
  await page.screenshot({ path: shot('b8-desktop'), fullPage: true });
  const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record('B8a desktop 1280', !desktopOverflow, desktopOverflow ? 'horizontal overflow' : 'no horizontal overflow at 1280px');

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
  const mpage = await mobile.newPage();
  await mpage.goto(BASE + '/', { waitUntil: 'networkidle' });
  await runSim(mpage, 'ac', SIM_DEFAULTS);
  await mpage.screenshot({ path: shot('b8-mobile'), fullPage: true });
  const mobileOverflow = await mpage.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record('B8b mobile 390', !mobileOverflow, mobileOverflow ? 'horizontal overflow' : 'no horizontal overflow at 390px');

  const chartScroll = await mpage.evaluate(() => {
    const el = document.querySelector('.chart-scroll');
    return el ? { scroll: el.scrollWidth, client: el.clientWidth } : null;
  });
  const chartScrollable = !!chartScroll && chartScroll.scroll > chartScroll.client;
  record('B8c mobile chart scroll', chartScrollable,
    chartScrollable ? `chart ${chartScroll.scroll}px wide in ${chartScroll.client}px, scrollable` : 'chart did not scroll');

  await browser.close();

  const summary = results.map((r) => `${r.ok ? 'PASS' : 'FAIL'} | ${r.id} | ${r.detail}`).join('\n');
  fs.writeFileSync(path.join(OUT, `${PHASE}-results.txt`), summary + '\n', 'utf8');
  const failures = results.filter((r) => !r.ok).length;
  console.log(`\n${PHASE}: ${results.length - failures}/${results.length} passed`);
  process.exit(failures ? 1 : 0);
})().catch((err) => { console.error(err); process.exit(2); });
