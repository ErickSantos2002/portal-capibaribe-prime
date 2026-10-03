// Testa o protótipo num Chrome automatizado. Uso: mkdir -p /tmp/prototipo-prints && node scripts/dev/testar-prototipo.mjs
// Requer puppeteer-core (hoje vem do cache do npx do mermaid-cli) e o google-chrome-stable.
import puppeteer from '/home/erick/.npm/_npx/668c188756b835f3/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
const url = 'file://' + new URL('../../prototipo/index.html', import.meta.url).pathname + '?dev';
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
// boas-vindas abre sozinha na 1ª visita e fecha no "Começar"
console.log('boas-vindas aberta:', await p.$eval('#boasVindas', d => d.open));
await p.screenshot({ path: '/tmp/prototipo-prints/boas-vindas.png' });
await p.click('#boasVindas button'); await new Promise(r=>setTimeout(r,100));
console.log('boas-vindas fechada:', !(await p.$eval('#boasVindas', d => d.open)));
// login com a unidade de quem testa; número que não existe cai no erro
await p.evaluate(()=>location.hash='#entrar'); await new Promise(r=>setTimeout(r,100));
await p.type('#login','9999'); await p.type('#senha','x'); await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,100));
console.log('9999 dá erro:', await p.evaluate(()=>location.hash) === '#entrar-erro');
await p.$eval('#login', e => e.value = ''); await p.type('#login','2704'); await p.type('#senha','x'); await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,100));
console.log('2704 vê a própria placa:', (await p.$eval('#app', e => e.innerText)).includes('Bloco 2, apartamento 704'));
await p.select('#perfil','voce'); await p.evaluate(()=>location.hash='#avisos'); await new Promise(r=>setTimeout(r,100));
console.log('2704 no mural:', (await p.$eval('#app', e => e.innerText)).includes('704'));
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
const alt = await p.evaluate(() => [document.querySelector('.proto').offsetHeight, document.documentElement.scrollHeight, innerHeight]);
console.log('celular: barra', alt[0] + 'px, página', alt[1], 'x tela', alt[2], alt[1] <= alt[2] ? '(sem rolar a página)' : '(PÁGINA ROLA)');
// sem ?dev (o link do grupo): sem barra; no computador abre na versão de computador
await p.setViewport({ width: 1300, height: 900 }); await p.goto(url.replace('?dev', '') + '#avisos'); await new Promise(r=>setTimeout(r,500));
console.log('público: barra escondida', await p.$eval('.proto', e => e.offsetHeight === 0), '| modo pc', await p.$eval('#app', e => e.classList.contains('pc')));
await p.evaluate(() => boasVindas.close()); await p.screenshot({ path: '/tmp/prototipo-prints/publico-pc.png' });
await p.setViewport({ width: 390, height: 844 }); await p.reload(); await new Promise(r=>setTimeout(r,500)); await p.evaluate(() => boasVindas.open && boasVindas.close());
await p.screenshot({ path: '/tmp/prototipo-prints/publico-cel.png' });
// tema: aparelho no escuro ainda abre no claro; o botão troca e a escolha fica gravada
await p.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
await p.evaluate(() => localStorage.removeItem('portal-tema')); await p.reload(); await new Promise(r=>setTimeout(r,400));
await p.evaluate(() => boasVindas.open && boasVindas.close());
console.log('tema: aparelho escuro abre claro', !(await p.$eval('#app', e => e.classList.contains('escuro'))));
await p.click('.tema-btn'); await new Promise(r=>setTimeout(r,100));
console.log('tema: botão escurece', await p.$eval('#app', e => e.classList.contains('escuro')), '| rótulo', await p.$eval('.tema-btn svg', e => e.getAttribute('aria-label')));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-cel-escuro.png' });
await p.reload(); await new Promise(r=>setTimeout(r,400));
console.log('tema: escolha sobrevive ao recarregar', await p.$eval('#app', e => e.classList.contains('escuro')));
await p.evaluate(() => { location.hash = '#entrar'; }); await new Promise(r=>setTimeout(r,100));
await p.click('.tema-btn'); await new Promise(r=>setTimeout(r,100));
console.log('tema: botão da entrada clareia', !(await p.$eval('#app', e => e.classList.contains('escuro'))));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-cel-entrar-claro.png' });
await p.setViewport({ width: 1300, height: 900 }); await p.reload(); await new Promise(r=>setTimeout(r,400));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-pc-entrar.png' });
await p.evaluate(() => { location.hash = '#avisos'; }); await new Promise(r=>setTimeout(r,100));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-pc-avisos.png' });
console.log('ERROS:', erros.length ? erros : 'nenhum');
await b.close();
