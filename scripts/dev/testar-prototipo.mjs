// Testa o protótipo num Chrome automatizado. Uso: mkdir -p /tmp/prototipo-prints && node scripts/dev/testar-prototipo.mjs
// Requer puppeteer-core (hoje vem do cache do npx do mermaid-cli) e o google-chrome-stable.
import puppeteer from '/home/erick/.npm/_npx/668c188756b835f3/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
const url = 'file://' + new URL('../../prototipo/index.html', import.meta.url).pathname;
const b = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome-stable', args: ['--no-sandbox'] });
const p = await b.newPage();
const erros = [];
p.on('pageerror', e => erros.push('pageerror: ' + e.message));
p.on('console', m => { if (m.type() === 'error') erros.push('console: ' + m.text()); });
await p.setViewport({ width: 900, height: 950 });
const casos = [
 ['socorro','entrar'],['socorro','entrar-bloqueio'],['socorro','primeiro-acesso'],['socorro','instalar'],
 ['socorro','avisos'],['socorro','aviso/2'],['socorro','aviso/4'],['socorro','enquetes'],['socorro','enquete/1'],['socorro','enquete/2'],
 ['socorro','documentos'],['socorro','minha-unidade'],['socorro','novo-aviso'],['rafael','avisos'],
 ['carla','avisos'],['carla','aviso/2'],['carla','novo-aviso'],['carla','nova-enquete'],['carla','novo-documento'],['carla','leitura/2'],['carla','documentos'],
 ['erick','admin'],['erick','unidade/2304'],['erick','unidade/1101'],['erick','historico'],['socorro','publicos'],['socorro','esqueci-ok'],
];
await p.goto(url); await new Promise(r=>setTimeout(r,800));
for (const [perf, h] of casos) {
  await p.select('#perfil', perf);
  await p.evaluate(x => { location.hash = '#' + x; }, h);
  await new Promise(r => setTimeout(r, 120));
  const txt = await p.$eval('#app', e => e.innerText.slice(0, 60).replace(/\n/g,' | '));
  await p.screenshot({ path: `/tmp/prototipo-prints/${perf}-${h.replace('/','_')}.png` });
  console.log(perf.padEnd(8), h.padEnd(16), txt);
}
// interações: votar e publicar
await p.select('#perfil','rafael'); await p.evaluate(()=>location.hash='#enquete/1'); await new Promise(r=>setTimeout(r,100));
await p.click('input[name=op][value="1"]'); await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,100));
console.log('voto:', await p.$eval('#app', e => e.innerText.match(/Quinta à noite\s*\d+/)?.[0]));
await p.select('#perfil','carla'); await p.evaluate(()=>location.hash='#novo-aviso'); await new Promise(r=>setTimeout(r,100));
await p.type('#t','Teste de aviso'); await p.type('#x','Texto'); await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,150));
console.log('publicado:', (await p.$eval('#app', e => e.innerText)).includes('Teste de aviso'));
for (const [m,t,perf,h] of [['pc','claro','socorro','avisos'],['pc','claro','carla','aviso/2'],['pc','claro','erick','admin'],['pc','claro','socorro','entrar'],['pc','claro','socorro','enquete/1'],['pc','claro','carla','nova-enquete'],['cel','escuro','socorro','avisos'],['cel','escuro','socorro','enquete/1'],['pc','escuro','erick','admin'],['cel','escuro','socorro','entrar']]) {
  await p.select('#modo', m); await p.select('#tema', t); await p.select('#perfil', perf);
  await p.evaluate(x => { location.hash = '#' + x; }, h); await new Promise(r => setTimeout(r, 150));
  await p.setViewport({ width: m==='pc'?1300:900, height: 950 });
  await p.screenshot({ path: `/tmp/prototipo-prints/${m}-${t}-${perf}-${h.replace('/','_')}.png` });
}
const larg = await p.evaluate(() => document.querySelector('.conteudo').scrollWidth > document.querySelector('.conteudo').clientWidth);
console.log('rolagem horizontal no pc:', larg);
await p.select('#modo','cel'); await p.select('#tema','claro');
await p.setViewport({ width: 390, height: 844 }); await p.evaluate(()=>location.hash='#avisos'); await new Promise(r=>setTimeout(r,100));
await p.screenshot({ path: '/tmp/prototipo-prints/mobile-avisos.png' });
console.log('ERROS:', erros.length ? erros : 'nenhum');
await b.close();
