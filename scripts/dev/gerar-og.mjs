// Gera prototipo/og.png (prévia do link no WhatsApp) a partir de scripts/dev/og.html.
// Requer puppeteer-core (cache do npx do mermaid-cli) e o google-chrome-stable, como o testar-prototipo.mjs.
import puppeteer from '/home/erick/.npm/_npx/668c188756b835f3/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
const dir = new URL('../../', import.meta.url).pathname;
const b = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome-stable', args: ['--no-sandbox'] });
const p = await b.newPage();
await p.setViewport({ width: 1200, height: 630 });
await p.goto('file://' + dir + 'scripts/dev/og.html', { waitUntil: 'networkidle0' });
await p.evaluate(() => document.fonts.ready);
await p.screenshot({ path: dir + 'prototipo/og.png' });
await b.close();
console.log('ok: prototipo/og.png');
