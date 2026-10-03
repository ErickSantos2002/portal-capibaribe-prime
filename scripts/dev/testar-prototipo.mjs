// Testa o protótipo num Chrome automatizado. Uso: node scripts/dev/testar-prototipo.mjs
// Sai com código 1 se alguma checagem falhar, para o pre-commit barrar o commit.
// Requer puppeteer-core (hoje vem do cache do npx do mermaid-cli) e o google-chrome-stable.
import puppeteer from '/home/erick/.npm/_npx/668c188756b835f3/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
const url = 'file://' + new URL('../../prototipo/index.html', import.meta.url).pathname + '?dev';
const b = await puppeteer.launch({ executablePath: '/usr/bin/google-chrome-stable', args: ['--no-sandbox'] });
import { mkdirSync } from 'node:fs';
mkdirSync('/tmp/prototipo-prints', { recursive: true });
const p = await b.newPage();
const erros = [], falhas = [];
// checagem: imprime como antes e anota a falha se algum valor der false
const ok = (nome, ...v) => { console.log(nome, ...v); if (v.includes(false)) falhas.push(nome); };
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
ok('boas-vindas aberta:', await p.$eval('#boasVindas', d => d.open));
await p.screenshot({ path: '/tmp/prototipo-prints/boas-vindas.png' });
await p.click('#boasVindas button'); await new Promise(r=>setTimeout(r,100));
ok('boas-vindas fechada:', !(await p.$eval('#boasVindas', d => d.open)));
// login com a unidade de quem testa; número que não existe cai no erro
await p.evaluate(()=>location.hash='#entrar'); await new Promise(r=>setTimeout(r,100));
await p.screenshot({ path: '/tmp/prototipo-prints/entrar-vazio.png' });
const entrar = async (bl, ap) => {
  await p.click(`.blocos-op input[value="${bl}"] + span`); await p.$eval('#login', e => e.value = '');
  await p.type('#login', ap); await p.type('#senha','x'); await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,100));
};
await p.$eval('#login', e => e.value = ''); await p.type('#login', '5a-02x9');
ok('apto só aceita número e 3 dígitos:', await p.$eval('#login', e => e.value) === '502');
await entrar(2, '999');
ok('Bloco 2, apto 999 dá erro sem apagar o formulário:', await p.evaluate(() => !!document.querySelector('#msg-entrar [role=alert]')
  && document.getElementById('login').value === '999' && document.querySelector('input[name=bloco]:checked')?.value === '2'));
await entrar(1, '7');
ok('Bloco 1, apto 7 vira 1007:', (await p.$eval('#app', e => e.innerText)).includes('Bloco 1, apartamento 007'));
await p.evaluate(()=>location.hash='#entrar'); await new Promise(r=>setTimeout(r,100));
await p.click('.blocos-op input[value="2"] + span'); await p.type('#login', '704');
await p.screenshot({ path: '/tmp/prototipo-prints/entrar-preenchido.png' });
await p.type('#senha','x'); await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,100));
ok('2704 vê a própria placa:', (await p.$eval('#app', e => e.innerText)).includes('Bloco 2, apartamento 704'));
await p.select('#perfil','voce'); await p.evaluate(()=>location.hash='#avisos'); await new Promise(r=>setTimeout(r,100));
ok('2704 no mural:', (await p.$eval('#app', e => e.innerText)).includes('704'));
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
ok('publicado:', (await p.$eval('#app', e => e.innerText)).includes('Teste de aviso'));
for (const [m,t,perf,h] of [['pc','claro','socorro','avisos'],['pc','claro','carla','aviso/2'],['pc','claro','erick','admin'],['pc','claro','socorro','entrar'],['pc','claro','socorro','enquete/1'],['pc','claro','carla','nova-enquete'],['cel','escuro','socorro','avisos'],['cel','escuro','socorro','enquete/1'],['pc','escuro','erick','admin'],['cel','escuro','socorro','entrar']]) {
  await p.select('#modo', m); await p.select('#tema', t); await p.select('#perfil', perf);
  await p.evaluate(x => { location.hash = '#' + x; }, h); await new Promise(r => setTimeout(r, 150));
  await p.setViewport({ width: m==='pc'?1300:900, height: 950 });
  await p.screenshot({ path: `/tmp/prototipo-prints/${m}-${t}-${perf}-${h.replace('/','_')}.png` });
}
const larg = await p.evaluate(() => document.querySelector('.conteudo').scrollWidth > document.querySelector('.conteudo').clientWidth);
ok('sem rolagem horizontal no pc:', !larg);
await p.select('#modo','cel'); await p.select('#tema','claro');
await p.setViewport({ width: 390, height: 844 }); await p.evaluate(()=>location.hash='#avisos'); await new Promise(r=>setTimeout(r,100));
await p.screenshot({ path: '/tmp/prototipo-prints/mobile-avisos.png' });
const alt = await p.evaluate(() => [document.querySelector('.proto').offsetHeight, document.documentElement.scrollHeight, innerHeight]);
ok('celular: barra ' + alt[0] + 'px, página ' + alt[1] + ' x tela ' + alt[2] + ', sem rolar a página:', alt[1] <= alt[2]);
// sem ?dev (o link do grupo): sem barra; no computador abre na versão de computador
await p.setViewport({ width: 1300, height: 900 }); await p.goto(url.replace('?dev', '') + '#avisos'); await new Promise(r=>setTimeout(r,500));
ok('público: barra escondida', await p.$eval('.proto', e => e.offsetHeight === 0), '| modo pc', await p.$eval('#app', e => e.classList.contains('pc')));
await p.evaluate(() => boasVindas.close()); await p.screenshot({ path: '/tmp/prototipo-prints/publico-pc.png' });
await p.setViewport({ width: 390, height: 844 }); await p.reload(); await new Promise(r=>setTimeout(r,500)); await p.evaluate(() => boasVindas.open && boasVindas.close());
await p.screenshot({ path: '/tmp/prototipo-prints/publico-cel.png' });
// tema: aparelho no escuro ainda abre no claro; o botão troca e a escolha fica gravada
await p.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
await p.evaluate(() => localStorage.removeItem('portal-tema')); await p.reload(); await new Promise(r=>setTimeout(r,400));
await p.evaluate(() => boasVindas.open && boasVindas.close());
ok('tema: aparelho escuro abre claro', !(await p.$eval('#app', e => e.classList.contains('escuro'))));
await p.click('.tema-btn'); await new Promise(r=>setTimeout(r,100));
ok('tema: botão escurece', await p.$eval('#app', e => e.classList.contains('escuro')), '| rótulo', await p.$eval('.tema-btn svg', e => e.getAttribute('aria-label')));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-cel-escuro.png' });
await p.reload(); await new Promise(r=>setTimeout(r,400));
ok('tema: escolha sobrevive ao recarregar', await p.$eval('#app', e => e.classList.contains('escuro')));
await p.evaluate(() => { location.hash = '#entrar'; }); await new Promise(r=>setTimeout(r,100));
await p.click('.tema-btn'); await new Promise(r=>setTimeout(r,100));
ok('tema: botão da entrada clareia', !(await p.$eval('#app', e => e.classList.contains('escuro'))));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-cel-entrar-claro.png' });
await p.setViewport({ width: 1300, height: 900 }); await p.reload(); await new Promise(r=>setTimeout(r,400));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-pc-entrar.png' });
await p.evaluate(() => { location.hash = '#avisos'; }); await new Promise(r=>setTimeout(r,100));
await p.screenshot({ path: '/tmp/prototipo-prints/publico-pc-avisos.png' });

// ---- regressões da revisão independente de 03/10/2026 (um revisor de UX e um de código) ----
await p.goto(url); await new Promise(r=>setTimeout(r,300));
await p.evaluate(() => document.getElementById('boasVindas').open && document.getElementById('boasVindas').close());
const ir = async (perf, h) => { await p.select('#perfil', perf); await p.evaluate(x => { location.hash = '#' + x; }, h); await new Promise(r => setTimeout(r, 120)); };
const texto = () => p.$eval('#app', e => e.innerText);
await ir('erick', "unidade/1');alert(1);('");
ok('rota de unidade inválida não monta tela (XSS):', (await texto()).includes('Não encontrado'));
await ir('socorro', 'aviso/3');
ok('aviso de outro bloco não abre:', (await texto()).includes('Não encontrado'));
await ir('socorro', 'leitura/2');
ok('"quem leu" é só da gestão:', (await texto()).includes('Sem permissão'));
for (const h of ['leitura/99', 'enquete/99', 'enquete']) { await ir('carla', h); ok(`#${h} mostra "não encontrado":`, (await texto()).includes('Não encontrado')); }
await ir('socorro', 'entrar');
const colar = v => p.$eval('#login', (e, v) => { e.value = v; e.dispatchEvent(new InputEvent('input', { inputType: 'insertFromPaste', bubbles: true })); return e.value; }, v);
ok('colar "Apto 502" vira 502:', await colar('Apto 502') === '502');
ok('colar " 502" vira 502:', await colar(' 502') === '502');
ok('colar "1203" marca o Bloco 1 e deixa 203:', await colar('1203') === '203' && await p.$eval('input[name=bloco]:checked', e => e.value) === '1');
await ir('rafael', 'avisos');
const ordem = await p.$$eval('#lista h3', hs => hs.map(h => h.textContent));
ok('mural do mais novo pro mais antigo:', ordem[0].startsWith('Vistoria') && ordem[1].startsWith('Fundação') && ordem[2].startsWith('Reunião'));
await p.evaluate(() => filtrar('fundacao'));
ok('busca sem acento acha "Fundação":', (await p.$eval('#lista', e => e.innerText)).includes('Fundação'));
await p.evaluate(() => filtrar('bem-vindos'));
ok('busca acha o aviso fixado:', (await p.$eval('#lista', e => e.innerText)).includes('Bem-vindos'));
await ir('socorro', 'documentos');
await p.type('#bd', 'cronograma');
ok('busca de documentos filtra:', await p.$$eval('#lista-docs .item', i => i.length) === 1);
await ir('carla', 'novo-aviso');
await p.type('#t', '   '); await p.type('#x', 'x'); await p.click('form button[type=submit]');
ok('título só de espaços é recusado:', !!(await p.$('.erro-form')) && (await p.evaluate(() => location.hash)) === '#novo-aviso');
await p.$eval('#t', e => e.value = ''); await p.type('#t', 'Teste de bloco 4'); await p.$eval('#x', e => e.value = '');
await p.type('#x', 'Linha 1'); await p.keyboard.down('Shift'); await p.keyboard.press('Enter'); await p.keyboard.up('Shift'); await p.type('#x', 'Linha 2');
await p.click('.chip[data-bloco="4"]'); await p.click('input[name=fixar]'); await p.click('form button[type=submit]');
ok('primeiro clique mostra a prévia:', (await p.$eval('#previa', e => e.innerText)).includes('64 apartamentos'));
await p.click('form button[type=submit]'); await new Promise(r=>setTimeout(r,150));
await ir('socorro', 'avisos');
ok('aviso do Bloco 4 não aparece pro Bloco 1:', !(await texto()).includes('Teste de bloco 4'));
await ir('rafael', 'avisos');
ok('aviso do Bloco 4 aparece fixado pro Bloco 4:', (await p.$$eval('.fixado h3', hs => hs.map(h => h.textContent))).includes('Teste de bloco 4'));
await p.evaluate(() => { location.hash = '#aviso/' + avisos.length; }); await new Promise(r=>setTimeout(r,120));
ok('quebra de linha simples continua no aviso:', (await p.$eval('.texto-aviso', e => e.innerText)).includes('Linha 1\nLinha 2'));
await ir('socorro', 'primeiro-acesso');
await p.type('#s1', 'abc'); await p.type('#s2', 'zzz'); await p.type('#nm', 'X'); await p.type('#cel', 'abc'); await p.click('form button[type=submit]');
ok('primeiro acesso recusa senha curta:', (await p.evaluate(() => location.hash)) === '#primeiro-acesso' && !!(await p.$('.erro-form')));
await ir('socorro', 'esqueci'); await p.evaluate(() => document.querySelector('form').requestSubmit());
ok('esqueci a senha não avança vazio:', (await p.evaluate(() => location.hash)) === '#esqueci');
await ir('carla', 'documentos');
await p.$eval('.conteudo', e => e.scrollTop = e.scrollHeight); await new Promise(r=>setTimeout(r,100));
ok('botão flutuante não cobre o último documento:', await p.evaluate(() => { const i = [...document.querySelectorAll('.item')].pop().getBoundingClientRect(), f = document.querySelector('.flutuante').getBoundingClientRect(); return i.bottom <= f.top; }));
await ir('erick', 'admin');
ok('grade começa no 701:', (await p.$eval('.grade a', a => a.textContent)) === '701');
ok('título da aba acompanha a tela:', (await p.title()).startsWith('Unidades'));
ok('#app sem aria-live (o leitor não relê a tela toda):', !(await p.$eval('#app', e => e.hasAttribute('aria-live'))));
const p2 = await b.newPage(); await p2.goto(url.replace('?dev', '') + '#aviso/2'); await new Promise(r=>setTimeout(r,300));
await p2.evaluate(() => document.getElementById('boasVindas').open && document.getElementById('boasVindas').close());
await p2.click('.voltar'); await new Promise(r=>setTimeout(r,200));
ok('voltar sem histórico vai pro mural, não sai do Portal:', (await p2.evaluate(() => location.hash)) === '#avisos');
await p2.close();
console.log('ERROS:', erros.length ? erros : 'nenhum');
await b.close();
if (falhas.length || erros.length) { console.log('FALHOU:', falhas); process.exit(1); }
