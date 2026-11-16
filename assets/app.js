/* Avos · Painel da Diretoria
   Os dados ficam criptografados (AES-256-GCM) em dados/dados.enc.js.
   A chave é derivada de usuário + senha (PBKDF2-SHA256); sem a senha correta nada é exibido. */
(function () {
  'use strict';

  /* ===================== CRIPTOGRAFIA / LOGIN ===================== */
  const enc = new TextEncoder();
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const toB64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf)));
  const P = window.AVOS_PAYLOAD;
  const SKEY = 'avos_painel_k';

  async function deriveKey(user, pass) {
    const base = await crypto.subtle.importKey('raw', enc.encode(user.trim().toLowerCase() + ':' + pass), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b64(P.salt), iterations: P.iter, hash: 'SHA-256' },
      base, { name: 'AES-GCM', length: 256 }, true, ['decrypt']);
  }
  async function decrypt(key) {
    const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(P.iv) }, key, b64(P.ct));
    return JSON.parse(new TextDecoder().decode(pt));
  }
  function ssGet() { try { return sessionStorage.getItem(SKEY); } catch (e) { return null; } }
  function ssSet(v) { try { v ? sessionStorage.setItem(SKEY, v) : sessionStorage.removeItem(SKEY); } catch (e) {} }

  const $ = s => document.querySelector(s);
  $('#loginForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const btn = $('#loginBtn'), msg = $('#loginMsg');
    msg.textContent = ''; btn.disabled = true; btn.textContent = 'Verificando…';
    try {
      const key = await deriveKey($('#user').value, $('#pass').value);
      const D = await decrypt(key);
      ssSet(toB64(await crypto.subtle.exportKey('raw', key)));
      start(D);
    } catch (e) {
      msg.textContent = (window.crypto && crypto.subtle) ? 'Usuário ou senha inválidos.' : 'Navegador sem suporte a criptografia. Abra pelo link https.';
    } finally { btn.disabled = false; btn.textContent = 'Entrar'; }
  });
  $('#logout').addEventListener('click', () => { ssSet(null); location.reload(); });

  (async function auto() {
    const k = ssGet(); if (!k) return;
    try {
      const key = await crypto.subtle.importKey('raw', b64(k), 'AES-GCM', false, ['decrypt']);
      start(await decrypt(key));
    } catch (e) { ssSet(null); }
  })();

  /* ===================== FORMATAÇÃO ===================== */
  const nf = (d) => new Intl.NumberFormat('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
  const N0 = nf(0), N1 = nf(1), N2 = nf(2);
  const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  function money(v, short) {
    if (v == null || isNaN(v)) return '–';
    const a = Math.abs(v), s = v < 0 ? '−' : '';
    if (a >= 1e9) return s + 'R$ ' + N2.format(a / 1e9) + ' bi';
    if (a >= 1e6) return s + 'R$ ' + N1.format(a / 1e6) + ' mi';
    if (a >= 1e3) return s + 'R$ ' + N0.format(a / 1e3) + (short ? ' mil' : ' mil');
    return s + 'R$ ' + N0.format(a);
  }
  const full = v => (v < 0 ? '−' : '') + 'R$ ' + N0.format(Math.abs(v));
  const mil = v => { if (v == null || isNaN(v)) return '–'; const r = Math.round(v / 1000); return r === 0 ? '<span class="dim">–</span>' : (r < 0 ? '<span class="neg">(' + N0.format(-r) + ')</span>' : N0.format(r)); };
  const pct = (v, d = 1) => (v == null || isNaN(v)) ? 'n.a.' : nf(d).format(v * 100) + '%';
  const int = v => N0.format(v);
  const ym = s => { const [y, m] = s.split('-'); return MESES[+m - 1] + '/' + y.slice(2); };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const title = s => String(s).toLowerCase().replace(/(^|[\s\-/(])([a-zà-ú])/g, (m, a, b) => a + b.toUpperCase());

  /* ===================== CORES ===================== */
  const C = { s1: '#2a78d6', s2: '#eb6834', s3: '#1baf7a', s4: '#eda100', s5: '#e87ba4', s6: '#008300', s7: '#6250d6', s8: '#e34948',
    ink: '#1c1c1b', b700: '#0d366b', b600: '#184f95', b550: '#1c5cab', b450: '#2a78d6', b350: '#5598e7', b250: '#86b6ef', b200: '#9ec5f4', b100: '#cde2fb',
    crit: '#d03b3b', grid: '#efeee9', text2: '#52514e', muted: '#8a8984' };
  const EMPS = ['ALOHI', 'BELLEVIE', 'KALA', 'KOA', 'LOTE COMERCIAL', 'NALU', 'VILLA NOAH'];
  const EMP_COLOR = { ALOHI: C.s1, BELLEVIE: C.s2, KALA: C.s3, KOA: C.s4, 'LOTE COMERCIAL': C.s5, NALU: C.s6, 'VILLA NOAH': C.s7 };
  const sw = c => `<span class="sw" style="background:${c}"></span>`;

  /* ===================== CHART.JS BASE ===================== */
  function setupChart() {
    Chart.defaults.font.family = 'Inter, "Segoe UI", system-ui, sans-serif';
    Chart.defaults.font.size = 11.5;
    Chart.defaults.color = C.text2;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.animation.duration = 500;
    Chart.defaults.plugins.legend.position = 'top';
    Chart.defaults.plugins.legend.align = 'start';
    Chart.defaults.plugins.legend.labels.boxWidth = 10;
    Chart.defaults.plugins.legend.labels.boxHeight = 10;
    Chart.defaults.plugins.legend.labels.useBorderRadius = true;
    Chart.defaults.plugins.legend.labels.borderRadius = 2;
    Chart.defaults.plugins.tooltip.backgroundColor = '#111';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 6;
    Chart.defaults.plugins.tooltip.boxPadding = 4;
    Chart.defaults.elements.bar.borderRadius = 3;
    Chart.defaults.elements.line.borderWidth = 2;
    Chart.defaults.elements.point.radius = 0;
    Chart.defaults.elements.point.hoverRadius = 5;
  }
  const moneyAxis = { grid: { color: C.grid }, border: { display: false }, ticks: { callback: v => money(v), maxRotation: 0, autoSkipPadding: 14 } };
  const plainAxis = { grid: { display: false }, border: { color: '#d9d7d0' }, ticks: { maxRotation: 0, autoSkipPadding: 8 } };
  const moneyTip = { callbacks: { label: c => ' ' + c.dataset.label + ': ' + full(c.parsed[c.chart.options.indexAxis === 'y' ? 'x' : 'y']) } };
  const charts = {};
  function chart(id, cfg) {
    const el = document.getElementById(id); if (!el) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(el, cfg);
  }
  const bar = (label, data, color, extra) => Object.assign({ type: 'bar', label, data, backgroundColor: color, hoverBackgroundColor: color, maxBarThickness: 34, categoryPercentage: .72, barPercentage: .9 }, extra || {});

  /* ===================== HELPERS DE HTML ===================== */
  const kpi = (lbl, val, det, hero) => `<div class="kpi${hero ? ' hero' : ''}"><div class="lbl">${lbl}</div><div class="val">${val}</div><div class="det">${det || ''}</div></div>`;
  const card = (t, note, body, cls) => `<div class="card ${cls || ''}"><h3>${t}</h3><div class="note">${note || ''}</div>${body}</div>`;
  const cv = (id, cls) => `<div class="chart ${cls || ''}"><canvas id="${id}" role="img"></canvas></div>`;
  function statusChip(s) {
    const m = { 'Saudável': ['good', '✓'], 'Esgotado': ['neutral', '●'], 'Giro lento': ['warn', '▲'], 'Estoque parado': ['bad', '■'], 'Entregue': ['good', '✓'], 'Holding': ['neutral', '◆'], 'Não lançado': ['neutral', '○'],
      'Credora líquida': ['good', '↓'], 'Devedora líquida': ['warn', '↑'], 'Cobrança': ['warn', '▲'], 'Negociação': ['neutral', '↔'], 'Concluído': ['good', '✓'], 'Sem registro': ['bad', '!'] };
    const [k, i] = m[s] || ['neutral', '•'];
    return `<span class="chip ${k}"><i>${i}</i>${esc(s)}</span>`;
  }

  /* ===================== APP ===================== */
  let D;
  const built = {};
  const PAGES = {};

  function start(data) {
    D = data;
    setupChart();
    $('#login').hidden = true; $('#app').hidden = false;
    $('#geradoEm').innerHTML = D.gerado_em ? 'Atualizado em ' + esc(D.gerado_em) : '';
    document.querySelectorAll('#nav a').forEach(a => a.addEventListener('click', () => go(a.dataset.page)));
    window.addEventListener('hashchange', () => go(location.hash.slice(1) || 'visao', true));
    go(location.hash.slice(1) || 'visao', true);
  }

  function go(p, fromHash) {
    if (!PAGES[p]) p = 'visao';
    if (!fromHash && location.hash.slice(1) !== p) { history.replaceState(null, '', '#' + p); }
    document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('active', a.dataset.page === p));
    const pg = PAGES[p];
    $('#pageTitle').textContent = pg.title; $('#pageSub').textContent = pg.sub;
    document.querySelectorAll('#pages > section').forEach(s => s.hidden = true);
    if (!built[p]) {
      const s = document.createElement('section'); s.id = 'pg-' + p; s.innerHTML = pg.html();
      $('#pages').appendChild(s); built[p] = true; pg.charts && pg.charts(); pg.after && pg.after();
    }
    $('#pg-' + p).hidden = false;
    window.scrollTo(0, 0);
  }

  /* ---------------- helpers de dados ---------------- */
  const realized = () => D.fluxo_mensal.filter(m => m.m <= '2026-10');
  const projected = () => D.fluxo_mensal.filter(m => m.m > '2026-10');
  const COST_KEYS = [['obra', 'Obra'], ['terreno', 'Terreno'], ['impostos', 'Impostos'], ['comissao', 'Comissão'], ['adm', 'Administrativo'], ['marketing', 'Marketing e plantão'], ['aprovacao', 'Aprovação'], ['taxa', 'Taxa de administração']];
  const costSum = m => COST_KEYS.reduce((a, [k]) => a + m[k], 0);

  /* ================================================================= */
  /*                            VISÃO GERAL                            */
  /* ================================================================= */
  PAGES.visao = {
    title: 'Visão geral', sub: 'Resumo consolidado de caixa, VGV e carteira · grupo Avos',
    html() {
      const k = D.cx_kpi, v = D.vgv_kpi, r = D.cr_kpi;
      const alerts = D.vgv_emp.filter(e => e.alertas && e.nome !== 'Total');
      return `
      <div class="kpis">
        ${kpi('Geração líquida de caixa', money(k.geracao), 'acumulado 2019 → 31/10/2026', true)}
        ${kpi('Receita líquida (caixa)', money(k.receita), 'margem operacional ' + pct(k.margem))}
        ${kpi('VGV total', money(v.vgv), pct(v.pct) + ' do VGV já vendido')}
        ${kpi('Estoque a tabela', money(v.estoque), int(v.disp) + ' lotes · ' + N0.format(v.meses) + ' meses de estoque')}
        ${kpi('Carteira a receber', money(r.avencer), 'já recebido ' + money(r.recebido))}
        ${kpi('Inadimplência', pct(r.inad, 2), 'vencido ' + money(r.vencido))}
      </div>
      <div class="grid g2">
        ${card('Receita líquida e resultado operacional por ano', 'Regime de caixa · 2026 até outubro', cv('c_vis_anual'))}
        ${card('Saldo de caixa acumulado', 'Realizado até out/26 · projeção pelas parcelas a vencer e obra prevista, antes de futuras distribuições', cv('c_vis_saldo'))}
      </div>
      <div class="grid g32">
        ${card('VGV por empreendimento', 'Vendido, estoque a preço de tabela e em proposta', cv('c_vis_vgv', 'tall'))}
        ${card('Pontos de atenção', 'Alertas do painel de VGV', `<ul class="alerts">${alerts.map(e => `<li><div class="an">${esc(title(e.nome))}<div style="margin-top:6px">${statusChip(e.status)}</div></div><div class="at">${esc(e.alertas).split(' · ').map(x => '• ' + x).join('<br>')}</div></li>`).join('')}
          <li><div class="an">Cobrança</div><div class="at">• ${money(D.cob_kpi.vencido)} vencidos em ${int(D.cob_kpi.parcelas)} parcelas (visão 100%)<br>• ${pct(D.aging[3][3] + D.aging[4][3] + D.aging[5][3])} do vencido tem mais de 90 dias</div></li></ul>`)}
      </div>`;
    },
    charts() {
      const a = D.cx_anual;
      chart('c_vis_anual', { data: { labels: a.anos, datasets: [bar('Receita líquida', a.receita, C.s1), bar('Resultado operacional', a.resultado, C.s2)] },
        options: { scales: { x: plainAxis, y: moneyAxis }, plugins: { tooltip: moneyTip } } });
      saldoChart('c_vis_saldo');
      const e = D.vgv_emp.filter(x => x.nome !== 'Total');
      chart('c_vis_vgv', { data: { labels: e.map(x => title(x.nome)), datasets: [
        bar('VGV vendido', e.map(x => x.vgv_vendido), C.b550, { stack: 's' }),
        bar('Estoque a tabela', e.map(x => x.estoque), C.b200, { stack: 's' }),
        bar('Em proposta', e.map(x => x.em_proposta), C.s4, { stack: 's' })] },
        options: { indexAxis: 'y', scales: { x: Object.assign({ stacked: true }, moneyAxis), y: Object.assign({ stacked: true }, plainAxis) },
          plugins: { tooltip: { callbacks: { label: c => ' ' + c.dataset.label + ': ' + full(c.parsed.x), footer: it => { const x = e[it[0].dataIndex]; return pct(x.pct) + ' vendido · ' + int(x.disp) + ' lotes disponíveis'; } } } } } });
    }
  };

  function saldoChart(id) {
    const all = D.fluxo_mensal.filter(m => m.m <= '2039-12');
    const cut = all.findIndex(m => m.m === '2026-10');
    chart(id, { type: 'line', data: { labels: all.map(m => ym(m.m)), datasets: [
      { label: 'Realizado', data: all.map((m, i) => i <= cut ? m.saldo : null), borderColor: C.ink, backgroundColor: C.ink, fill: false, tension: .2 },
      { label: 'Projetado', data: all.map((m, i) => i >= cut ? m.saldo : null), borderColor: C.s1, backgroundColor: C.s1, borderDash: [5, 4], fill: false, tension: .2 }] },
      options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({}, plainAxis, { ticks: { maxTicksLimit: 10, maxRotation: 0 } }), y: moneyAxis },
        plugins: { legend: { labels: { usePointStyle: true, pointStyle: 'line', pointStyleWidth: 22 } }, tooltip: { callbacks: { label: c => c.parsed.y == null ? null : ' ' + c.dataset.label + ': ' + full(c.parsed.y) } } } } });
  }

  /* ================================================================= */
  /*                          CAIXA E RESULTADO                        */
  /* ================================================================= */
  PAGES.caixa = {
    title: 'Caixa e resultado', sub: 'Painel executivo, fluxo do grupo e projeção · regime de caixa, acumulado desde 2019 até 31/10/2026',
    html() {
      const k = D.cx_kpi;
      const RA = D.receita_avos || {};
      const partOf = e => RA[e.nome] && RA[e.nome].pct != null ? RA[e.nome].pct : null;
      const avosOf = e => RA[e.nome] ? RA[e.nome].avos : null;
      const recAvosTot = Object.entries(RA).reduce((t, [n, x]) => t + (n !== 'Total do grupo' && x.avos ? x.avos : 0), 0);
      const rows = D.cx_emp.map(e => {
        const T = e.nome === 'Total do grupo', x = RA[e.nome] || {};
        return `<tr class="${T ? 'total' : ''}"><td>${esc(T ? 'Total do grupo' : title(e.nome))}</td><td class="l">${e.status ? statusChip(e.status) : ''}</td>
        <td class="dim">${x.pct == null ? '–' : pct(x.pct, Math.abs(x.pct * 100 - Math.round(x.pct * 100)) > 1e-6 ? 2 : 0)}</td>
        <td class="avos">${T ? mil(recAvosTot) : x.avos == null ? '<span class="dim">–</span>' : mil(x.avos)}</td>
        <td>${mil(x.receitas)}</td><td>${mil(x.custos)}</td><td>${mil(x.resultado)}</td><td>${x.margem == null ? '<span class="dim">n.a.</span>' : pct(x.margem)}</td>
        <td>${mil(x.fin)}</td><td>${mil(x.aportes)}</td><td>${mil(x.retirada)}</td><td>${mil(x.distrib)}</td><td><b>${mil(x.geracao)}</b></td></tr>`; }).join('');
      const Y = {};
      D.fluxo_mensal.forEach(m => {
        const y = m.m.slice(0, 4), o = Y[y] = Y[y] || { receita: 0, custos: 0, fin: 0, socios: 0, geracao: 0, real: 0 };
        const rec = m.receita + m.distrato + m.avencer + m.comissao + m.impostos, cus = costSum(m) - m.comissao - m.impostos;
        o.receita += rec; o.custos += cus; o.fin += m.fin; o.socios += m.aporte_cap + m.aporte_soc + m.retirada + m.lucro_grupo + m.lucro_terc; o.geracao += m.geracao;
      });
      const anos = Object.keys(Y).filter(y => Object.values(Y[y]).some(v => Math.abs(v) > 500));
      anos.forEach(y => { const o = Y[y]; o.resultado = o.receita + o.custos; o.margem = o.receita ? o.resultado / o.receita : null; });
      const R = realized(), RT = { receita: 0, custos: 0, fin: 0, socios: 0, geracao: 0 };
      R.forEach(m => { RT.receita += m.receita + m.distrato + m.comissao + m.impostos; RT.custos += costSum(m) - m.comissao - m.impostos; RT.fin += m.fin; RT.socios += m.aporte_cap + m.aporte_soc + m.retirada + m.lucro_grupo + m.lucro_terc; RT.geracao += m.geracao; });
      RT.resultado = RT.receita + RT.custos; RT.margem = RT.resultado / RT.receita;
      const TT = {}; ['receita', 'custos', 'resultado', 'fin', 'socios', 'geracao'].forEach(kk => TT[kk] = anos.reduce((t, y) => t + Y[y][kk], 0)); TT.margem = TT.resultado / TT.receita;
      const lin = [['Receita líquida', 'receita'], ['Custos operacionais', 'custos'], ['Resultado operacional', 'resultado'], ['Margem operacional', 'margem'], ['Resultado financeiro', 'fin'], ['Sócios e distribuições', 'socios'], ['Geração líquida de caixa', 'geracao']];
      const fv = (kk, v) => kk === 'margem' ? (v == null ? '<span class="dim">–</span>' : pct(v)) : mil(v);
      const evo = lin.map(([n, kk]) => `<tr class="${kk === 'geracao' ? 'total' : ''}${kk === 'margem' ? ' mrow' : ''}"><td class="stick">${n}</td><td class="acc"><b>${fv(kk, RT[kk])}</b></td><td class="acc">${fv(kk, TT[kk])}</td>${anos.map(y => `<td class="${y > '2026' ? 'proj' : ''}">${fv(kk, Y[y][kk])}</td>`).join('')}</tr>`).join('');
      const evoHead = `<th class="stick">Indicador</th><th class="acc">Realizado<br>até out/26</th><th class="acc">Total c/<br>projeção</th>${anos.map(y => `<th class="${y > '2026' ? 'proj' : ''}">${y === '2026' ? '2026*' : y}${y > '2026' ? '<br><span>proj.</span>' : y === '2026' ? '<br><span>real+proj.</span>' : '<br><span>real</span>'}</th>`).join('')}`;
      return `
      <div class="kpis">
        ${kpi('Receita líquida', money(k.receita), 'vendas − distratos')}
        ${kpi('Custos operacionais', money(k.custos), 'obra, comissões, impostos, adm.')}
        ${kpi('Resultado operacional', money(k.resultado), 'receita − custos')}
        ${kpi('Margem operacional', pct(k.margem), 'resultado ÷ receita líquida')}
        ${kpi('Distribuições', money(k.distrib), 'lucro a terceiros + grupo')}
        ${kpi('Geração líquida', money(k.geracao), 'após sócios e financeiro', true)}
      </div>
      ${card('Desempenho por empreendimento · fluxo completo (realizado + previsão)', 'R$ mil · mesmos totais da aba Fluxo grupo de cada empreendimento: Receitas = receita − distratos + parcelas a vencer; Custos = impostos, terreno, aprovação, obra (com previsão), comissão, marketing, administrativo e taxa; Distribuições = lucro grupo + lucro a terceiros · Receita Avos = coluna "Total Avos" da aba Fluxo grupo: (receitas realizadas − distratos + parcelas a vencer) × % de participação Avos (lista depara; Todos Bambuzal = 60%; sem % cadastrado = 100%); total = soma das linhas · AVOS = holding',
        `<div class="tbl-wrap"><table class="t"><thead><tr><th>Empreendimento</th><th class="l">Status</th><th>% Avos</th><th>Receita Avos</th><th>Receitas</th><th>Custos oper.</th><th>Resultado oper.</th><th>Margem</th><th>Financeiro</th><th>Aportes</th><th>Retirada sócios</th><th>Distribuições</th><th>Geração líq.</th></tr></thead><tbody>${rows}</tbody></table></div>`)}
      <div style="margin-top:16px">${card('Evolução anual consolidada · todos os anos do fluxo', 'R$ mil · realizado até out/26; *2026 = jan–out realizado + nov–dez projetado; a partir de 2027, projeção pelas parcelas a vencer, impostos (4%) e obra prevista · receita líquida = vendas − distratos − comissões − impostos, como no Painel executivo · role para o lado para ver todos os anos', `<div class="tbl-wrap"><table class="t evo"><thead><tr>${evoHead}</tr></thead><tbody>${evo}</tbody></table></div>`)}</div>
      <div class="grid g2" style="margin-top:16px">
        ${card('Fluxo mensal realizado · últimos 24 meses', 'Entradas (receita − distratos) e saídas operacionais', cv('c_cx_mensal'))}
        ${card('Composição das saídas operacionais', 'Acumulado de todo o período (inclui previsão de obra)', cv('c_cx_comp'))}
      </div>
      <div class="grid g2">
        ${card('Projeção a partir de nov/26', 'Receita a vencer (parcelas) e custos previstos (obra + impostos), por ano', cv('c_cx_proj'))}
        ${card('Saldo de caixa acumulado', 'Realizado até out/26 e projetado (antes de futuras distribuições)', cv('c_cx_saldo'))}
      </div>`;
    },
    charts() {
      const r = realized().slice(-24);
      chart('c_cx_mensal', { data: { labels: r.map(m => ym(m.m)), datasets: [
        bar('Entradas', r.map(m => m.receita + m.distrato), C.s1), bar('Saídas operacionais', r.map(m => -costSum(m)), C.s2)] },
        options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({}, plainAxis, { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } }), y: moneyAxis }, plugins: { tooltip: moneyTip } } });
      const t = D.fluxo_total;
      const comp = COST_KEYS.map(([kk, n]) => [n, -t[kk]]).sort((x, y) => y[1] - x[1]);
      chart('c_cx_comp', { data: { labels: comp.map(x => x[0]), datasets: [bar('Saídas', comp.map(x => x[1]), C.ink)] },
        options: { indexAxis: 'y', scales: { x: moneyAxis, y: plainAxis }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ' ' + full(c.parsed.x) + ' · ' + pct(c.parsed.x / comp.reduce((a, b) => a + b[1], 0)) } } } } });
      const byY = {};
      projected().forEach(m => { const y = m.m.slice(0, 4); byY[y] = byY[y] || [0, 0]; byY[y][0] += m.avencer; byY[y][1] += -(m.obra + m.impostos); });
      const ys = Object.keys(byY).filter(y => byY[y][0] + byY[y][1] > 500);
      saldoChart('c_cx_saldo');
      chart('c_cx_proj', { data: { labels: ys.map(y => y === '2026' ? 'nov–dez/26' : y), datasets: [bar('Receita a vencer', ys.map(y => byY[y][0]), C.s1), bar('Obra + impostos previstos', ys.map(y => byY[y][1]), C.s2)] },
        options: { scales: { x: plainAxis, y: moneyAxis }, plugins: { tooltip: moneyTip } } });
    }
  };

  /* ================================================================= */
  /*                               DRE                                 */
  /* ================================================================= */
  PAGES.dre = {
    title: 'DRE Empreendimentos', sub: 'DRE gerencial de caixa por empreendimento · R$ mil · % sobre a receita bruta',
    html() {
      const R = D.dre_all;
      const nome = o => o === 'Todos' ? 'Todos' : o === 'Todos Bambuzal' ? 'Todos Bambuzal' : title(o);
      return `
      <div class="selbar">
        <label for="dreSel">Empreendimento</label>
        <select id="dreSel">${R.opcoes.map(o => `<option value="${esc(o)}"${o === 'Todos' ? ' selected' : ''}>${esc(nome(o))}</option>`).join('')}</select>
        <span class="selhint">selecione na lista (ou "Todos")</span>
      </div>
      ${card('Demonstrativo por ano', 'Igual à aba DRE por empreendimento: montado a partir da Fluxo grupo do empreendimento selecionado · *2026 = jan–out realizado + nov–dez projetado · 2027+ = previsão (parcelas a vencer, impostos 4% e obra prevista) · valores negativos entre parênteses', '<div class="tbl-wrap" id="dreTbl"></div>')}
      <div class="grid g23" style="margin-top:16px">
        ${card('Indicadores do empreendimento', 'Produto, custo de obra, rentabilidade e exposição', '<div class="ind" id="dreInd"></div>')}
        ${card('Saldo acumulado antes dos sócios', '<span id="dreChartNote"></span>', cv('c_dre_saldo', 'xtall'))}
      </div>`;
    },
    after() {
      const R = D.dre_all;
      const fmtI = ([t, v]) => t === 'n' ? (Number.isInteger(v) ? int(v) : N1.format(v)) : t === 'r' ? full(v) : t === 'p' ? pct(v) : t === 'x' ? N2.format(v) + 'x' : t === 'i' ? int(v) : esc(v);
      const render = () => {
        const sel = $('#dreSel').value, X = R.dados[sel];
        const keep = R.anos.map((y, i) => i);
        const pj = y => typeof y === 'string' ? 'proj' : '';
        const hd = y => typeof y === 'string' ? '2027+<br><span>previsão</span>' : `${y === 2026 ? '2026*' : y}<br><span>${y === 2026 ? 'real+proj.' : 'real'}</span>`;
        const rows = X.linhas.map(l => {
          const isM = /^Margem/.test(l.lin), isT = /^\(=\)/.test(l.lin) || /^Saldo de caixa final/.test(l.lin);
          const f = v => isM ? pct(v) : mil(v * 1000);
          return `<tr class="${isT ? 'total' : ''}${isM ? ' mrow' : ''}"><td class="stick">${esc(l.lin)}</td><td class="acc"><b>${f(l.tot)}</b></td><td class="dim acc">${l.pct == null ? '' : pct(l.pct)}</td>${keep.map(i => `<td class="${pj(R.anos[i])}">${f(l.anos[i])}</td>`).join('')}</tr>`;
        }).join('');
        $('#dreTbl').innerHTML = keep.length ? `<table class="t evo"><thead><tr><th class="stick">R$ mil</th><th class="acc">Total</th><th class="acc">% rec.</th>${keep.map(i => `<th class="${pj(R.anos[i])}">${hd(R.anos[i])}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`
          : '<div class="dim" style="padding:20px 0">Sem movimentação registrada para esta seleção.</div>';
        $('#dreInd').innerHTML = X.ind.map(([n, v]) => v == null ? `<div class="h">${esc(n)}</div>` : `<div class="r"><span>${esc(n)}</span><b>${fmtI(v)}</b></div>`).join('');
        const first = X.saldo.findIndex(x => Math.abs(x[1]) > 0.5);
        const s = first < 0 ? [] : X.saldo.slice(first);
        $('#dreChartNote').textContent = 'Fluxo mensal acumulado (receitas + custos + financeiro), jan/19 a dez/26 · ' + $('#dreSel').selectedOptions[0].text;
        chart('c_dre_saldo', { type: 'line', data: { labels: s.map(x => ym(x[0])), datasets: [{ label: 'Saldo acumulado', data: s.map(x => x[1]), borderColor: C.ink, backgroundColor: 'rgba(28,28,27,.06)', fill: true, tension: .2 }] },
          options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({}, plainAxis, { ticks: { maxRotation: 0, maxTicksLimit: 14 } }), y: moneyAxis }, plugins: { legend: { display: false }, tooltip: moneyTip } } });
      };
      $('#dreSel').addEventListener('change', render);
      render();
    }
  };

  /* ================================================================= */
  /*                             VGV E VENDAS                          */
  /* ================================================================= */
  PAGES.vgv = {
    title: 'VGV e vendas', sub: 'Painel de VGV e carteira · loteamentos Avos · data base 31/10/2026',
    html() {
      const v = D.vgv_kpi;
      const rows = D.vgv_emp.map(e => { const T = e.nome === 'Total'; return `<tr class="${T ? 'total' : ''}"><td>${T ? 'Total' : sw(EMP_COLOR[e.nome]) + esc(title(e.nome)) + '<div style="margin:4px 0 0 16px">' + statusChip(e.status) + '</div>'}</td>
        <td>${int(e.lotes)}</td><td>${int(e.vendidos)}</td><td>${int(e.disp)}</td><td>${pct(e.pct)}</td>
        <td>${mil(e.vgv_vendido)}</td><td>${mil(e.estoque)}</td><td>${mil(e.vgv_total)}</td><td>${mil(e.ticket_v)}</td>
        <td>${pct(e.desconto)}</td><td>${int(e.v90)}</td><td>${e.meses ? N1.format(e.meses) : '<span class="dim">–</span>'}</td><td>${pct(e.vso)}</td><td>${pct(e.com_pct)}</td><td>${int(e.distratos)}</td></tr>`; }).join('');
      return `
      <div class="kpis k4">
        ${kpi('VGV total', money(v.vgv), int(v.lotes) + ' lotes', true)}
        ${kpi('VGV vendido', money(v.vendido), pct(v.pct) + ' do VGV')}
        ${kpi('Estoque a tabela', money(v.estoque), int(v.disp) + ' lotes disponíveis')}
        ${kpi('VSO 90 dias', pct(v.vso), int(v.vendas90) + ' vendas em 90 dias')}
        ${kpi('Vendas / mês (6m)', N1.format(v.vendasmes), 'lotes por mês')}
        ${kpi('Meses de estoque', N1.format(v.meses), 'no ritmo atual')}
        ${kpi('Desconto vs. tabela', pct(v.desc), 'média ponderada')}
        ${kpi('Comissão média', pct(v.comissao), 'sobre o valor vendido')}
      </div>
      ${card('Desempenho por empreendimento', 'Valores em R$ mil · VSO = vendas ÷ (vendas + estoque) em 90 dias',
        `<div class="tbl-wrap"><table class="t"><thead><tr><th>Empreendimento · status</th><th>Lotes</th><th>Vend.</th><th>Disp.</th><th>% vend.</th><th>VGV vend.</th><th>Estoque</th><th>VGV total</th><th>Ticket</th><th>Desc.</th><th>Vd. 90d</th><th>Meses</th><th>VSO</th><th>Com.</th><th>Distr.</th></tr></thead><tbody>${rows}</tbody></table></div>`)}
      <div class="grid g32" style="margin-top:16px">
        ${card('Vendas mensais · últimos 24 meses', 'Lotes vendidos por mês e empreendimento', cv('c_vgv_vendas', 'tall'))}
        ${card('Top 10 imobiliárias parceiras', 'Valor vendido acumulado', cv('c_vgv_top', 'tall'))}
      </div>
      <div class="grid g2">
        ${card('Ticket médio: vendido x estoque', 'Empreendimentos com estoque disponível', cv('c_vgv_ticket'))}
        ${card('Vendas por ano', 'VGV vendido por ano de venda', cv('c_vgv_ano'))}
      </div>`;
    },
    charts() {
      const vm = D.vendas_mensais.slice(-24);
      chart('c_vgv_vendas', { data: { labels: vm.map(m => ym(m.m)), datasets: EMPS.map((e, i) => bar(title(e), vm.map(m => m.q[i]), EMP_COLOR[e], { stack: 's' })) },
        options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({ stacked: true }, plainAxis, { ticks: { maxRotation: 0, maxTicksLimit: 12 } }), y: { stacked: true, grid: { color: C.grid }, border: { display: false }, ticks: { precision: 0 } } },
          plugins: { tooltip: { filter: c => c.parsed.y > 0, callbacks: { label: c => ' ' + c.dataset.label + ': ' + c.parsed.y + ' lote(s) · ' + money(vm[c.dataIndex].v[EMPS.indexOf(c.dataset.label.toUpperCase())]), footer: it => 'Total: ' + vm[it[0].dataIndex].qt + ' lotes · ' + money(vm[it[0].dataIndex].vt) } } } } });
      const t = D.vgv_top;
      chart('c_vgv_top', { data: { labels: t.map(x => title(x[1])), datasets: [bar('Valor vendido', t.map(x => x[3]), C.s1)] },
        options: { indexAxis: 'y', scales: { x: moneyAxis, y: plainAxis }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => { const x = t[c.dataIndex]; return [' ' + full(x[3]), ' ' + int(x[2]) + ' lotes · ' + pct(x[4]) + ' do total', ' comissão ' + pct(x[5], 2)]; } } } } } });
      const e = D.vgv_emp.filter(x => x.nome !== 'Total' && x.ticket_e > 0);
      chart('c_vgv_ticket', { data: { labels: e.map(x => title(x.nome)), datasets: [bar('Ticket médio vendido', e.map(x => x.ticket_v), C.s1), bar('Ticket médio do estoque', e.map(x => x.ticket_e), C.b250)] },
        options: { scales: { x: plainAxis, y: moneyAxis }, plugins: { tooltip: moneyTip } } });
      const byY = {}; D.vendas_mensais.forEach(m => { const y = m.m.slice(0, 4); byY[y] = byY[y] || EMPS.map(() => 0); m.v.forEach((v, i) => byY[y][i] += v); });
      const ys = Object.keys(byY);
      chart('c_vgv_ano', { data: { labels: ys.map(y => y === '2026' ? '2026 (até out)' : y), datasets: EMPS.map((e, i) => bar(title(e), ys.map(y => byY[y][i]), EMP_COLOR[e], { stack: 's' })) },
        options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({ stacked: true }, plainAxis), y: Object.assign({ stacked: true }, moneyAxis) }, plugins: { tooltip: Object.assign({ filter: c => c.parsed.y > 0 }, moneyTip) } } });
    }
  };

  /* ================================================================= */
  /*                          CONTAS A RECEBER                         */
  /* ================================================================= */
  PAGES.receber = {
    title: 'Contas a receber', sub: 'Carteira de recebíveis · todos os empreendimentos · valores na participação Avos',
    html() {
      const r = D.cr_kpi;
      const max = Math.max(...D.cr_emp.filter(e => e.nome !== 'Total').flatMap(e => e.heat));
      const heat = v => { const t = v / max; const bg = v <= 0 ? 'transparent' : t > .66 ? C.b600 : t > .4 ? C.b350 : t > .2 ? C.b200 : C.b100; return `<td style="background:${bg};color:${t > .4 ? '#fff' : 'inherit'}">${mil(v)}</td>`; };
      const rows = D.cr_emp.map(e => { const T = e.nome === 'Total'; return `<tr class="${T ? 'total' : ''}"><td>${T ? 'Total' : sw(EMP_COLOR[e.nome]) + esc(title(e.nome))}</td><td>${mil(e.recebido)}</td><td>${mil(e.avencer)}</td><td>${mil(e.vencido)}</td><td>${pct(e.pv, 2)}</td>${T ? e.heat.map(v => `<td>${mil(v)}</td>`).join('') : e.heat.map(heat).join('')}</tr>`; }).join('');
      return `
      <div class="kpis">
        ${kpi('Recebido', money(r.recebido), 'acumulado desde 2019', true)}
        ${kpi('A vencer', money(r.avencer), 'parcelas futuras')}
        ${kpi('Vencido', money(r.vencido), 'em aberto')}
        ${kpi('% inadimplência', pct(r.inad, 2), 'vencido ÷ (vencido + a vencer)')}
        ${kpi('Multa e juros', money(r.multa), 'sobre parcelas pagas em atraso')}
      </div>
      <div class="grid g2">
        ${card('Carteira por empreendimento', 'Recebido, a vencer e vencido', cv('c_cr_emp'))}
        ${card('Fluxo de recebimento por ano', 'Realizado até hoje e projeção pelas parcelas a vencer', cv('c_cr_ano'))}
      </div>
      ${card('Situação da carteira e saldo a receber por ano de vencimento', 'R$ mil · mapa de calor do saldo a vencer (mais escuro = maior valor)',
        `<div class="tbl-wrap"><table class="t"><thead><tr><th>Empreendimento</th><th>Recebido</th><th>A vencer</th><th>Vencido</th><th>% vencido</th>${D.cr_anos_venc.map(y => `<th>${y}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`)}
      <div class="grid g2" style="margin-top:16px">
        ${card('Recebimentos por mês · últimos 12 meses', 'Por empreendimento', cv('c_cr_rec12'))}
        ${card('Parcelas a vencer · próximos meses', 'Total da carteira, mês a mês (após set/28: ' + money(D.cr_mensal[D.cr_mensal.length - 1].apos) + ')', cv('c_cr_prox'))}
      </div>`;
    },
    charts() {
      const e = D.cr_emp.filter(x => x.nome !== 'Total');
      chart('c_cr_emp', { data: { labels: e.map(x => title(x.nome)), datasets: [bar('Recebido', e.map(x => x.recebido), C.b550, { stack: 's' }), bar('A vencer', e.map(x => x.avencer), C.b200, { stack: 's' }), bar('Vencido', e.map(x => x.vencido), C.crit, { stack: 's' })] },
        options: { indexAxis: 'y', scales: { x: Object.assign({ stacked: true }, moneyAxis), y: Object.assign({ stacked: true }, plainAxis) }, plugins: { tooltip: { callbacks: { label: c => ' ' + c.dataset.label + ': ' + full(c.parsed.x), footer: it => '% vencido: ' + pct(e[it[0].dataIndex].pv, 2) } } } } });
      const f = D.cr_fluxo.slice(0, -1);
      chart('c_cr_ano', { data: { labels: f.map(x => x[0]), datasets: [bar('Recebido', f.map(x => x[1]), C.b550, { stack: 's' }), bar('A vencer', f.map(x => x[2]), C.b200, { stack: 's' }), bar('Vencido', f.map(x => x[3]), C.crit, { stack: 's' })] },
        options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({ stacked: true }, plainAxis), y: Object.assign({ stacked: true }, moneyAxis) }, plugins: { tooltip: Object.assign({ filter: c => c.parsed.y > 0 }, moneyTip) } } });
      const r = D.rec12;
      chart('c_cr_rec12', { data: { labels: r.map(x => ym(x.m)), datasets: EMPS.map(n => { const j = D.rec12_emps.indexOf(n); return bar(title(n), r.map(x => x.v[j]), EMP_COLOR[n], { stack: 's' }); }) },
        options: { interaction: { mode: 'index', intersect: false }, scales: { x: Object.assign({ stacked: true }, plainAxis), y: Object.assign({ stacked: true }, moneyAxis) },
          plugins: { tooltip: { filter: c => c.parsed.y > 0, callbacks: { label: c => ' ' + c.dataset.label + ': ' + full(c.parsed.y), footer: it => 'Total: ' + full(r[it[0].dataIndex].t) } } } } });
      const tot = D.cr_mensal[D.cr_mensal.length - 1];
      chart('c_cr_prox', { data: { labels: D.cr_meses.map(ym), datasets: [bar('A vencer', tot.m, C.s1)] },
        options: { scales: { x: Object.assign({}, plainAxis, { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } }), y: moneyAxis }, plugins: { legend: { display: false }, tooltip: moneyTip } } });
    }
  };

  /* ================================================================= */
  /*                              COBRANÇA                             */
  /* ================================================================= */
  PAGES.cobranca = {
    title: 'Cobrança e inadimplência', sub: 'Painel de cobrança · visão total dos empreendimentos (100%), não apenas a participação Avos',
    html() {
      const k = D.cob_kpi;
      const top = D.top_dev.map((x, i) => `<tr><td class="dim">${i + 1}</td><td class="l">${esc(x[0])}</td><td class="l">${sw(EMP_COLOR[x[1]] || '#999')}${esc(title(x[1]))}</td><td>${int(x[2])}</td><td>${full(x[3])}</td><td>${int(x[4])} d</td></tr>`).join('');
      const emps = [...new Set(D.clientes.map(c => c[0]))];
      const etapas = [...new Set(D.clientes.map(c => c[8]).filter(Boolean))];
      return `
      <div class="kpis">
        ${kpi('Valor vencido', money(k.vencido), 'total em aberto', true)}
        ${kpi('Parcelas vencidas', int(k.parcelas), D.clientes.length + ' clientes')}
        ${kpi('% inadimplência', pct(k.inad, 2), 'sobre a carteira total')}
        ${kpi('Multa e juros', money(k.multa), 'cobrados sobre atrasos')}
      </div>
      <div class="grid g12">
        ${card('Aging do vencido', 'Quanto está vencido e há quanto tempo · faixas em dias de atraso', cv('c_cob_aging'))}
        ${card('Maiores valores vencidos por cliente', 'Prioridade de cobrança',
          `<div class="tbl-wrap"><table class="t"><thead><tr><th>#</th><th class="l">Cliente</th><th class="l">Empreend.</th><th>Parc.</th><th>Vencido</th><th>Atraso</th></tr></thead><tbody>${top}</tbody></table></div>`)}
      </div>
      ${card('Inadimplência por imobiliária', 'Imobiliárias com valor inadimplente · % sobre o valor vendido no tooltip', cv('c_cob_imob', 'tall'))}
      <div style="margin-top:16px">${card('Todos os clientes com parcelas vencidas', 'Filtre por empreendimento, etapa de cobrança ou busque por nome',
        `<div class="toolbar"><select id="fEmp"><option value="">Todos os empreendimentos</option>${emps.map(e => `<option>${esc(e)}</option>`).join('')}</select>
          <select id="fEt"><option value="">Todas as etapas</option>${etapas.map(e => `<option>${esc(e)}</option>`).join('')}</select>
          <input id="fQ" type="search" placeholder="Buscar cliente, lote ou imobiliária"><span class="count" id="fCount"></span></div>
         <div class="tbl-wrap scroll"><table class="t" id="tCli"><thead><tr>
          <th class="l sortable" data-k="0">Empreend.</th><th class="l sortable" data-k="1">Lote</th><th class="l sortable" data-k="2">Cliente</th><th class="l sortable" data-k="3">Imobiliária</th>
          <th class="sortable" data-k="4">Parc.</th><th class="sortable" data-k="5">Vencido</th><th class="sortable" data-k="6">Pago</th><th class="sortable" data-k="7">A vencer</th>
          <th class="l sortable" data-k="8">Etapa</th><th class="l sortable" data-k="9">Últ. evento</th><th class="l">Descrição</th></tr></thead><tbody></tbody></table></div>`)}</div>`;
    },
    charts() {
      const a = D.aging.slice(0, -1); const AG = ['1–30', '31–60', '61–90', '91–180', '181–365', '> 365'];
      const ramp = [C.b250, C.b350, C.b450, C.b550, C.b600, C.b700];
      chart('c_cob_aging', { data: { labels: AG, datasets: [bar('Valor vencido', a.map(x => x[1]), ramp)] },
        options: { scales: { x: Object.assign({}, plainAxis, { ticks: { autoSkip: false, maxRotation: 0, font: { size: 10.5 } } }), y: moneyAxis }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => { const x = a[c.dataIndex]; return [' ' + full(x[1]), ' ' + int(x[2]) + ' parcelas · ' + pct(x[3]) + ' do vencido']; } } } } } });
      const im = D.imob_inad.filter(x => x[3] > 1 && !/^Total|Não identificada/.test(x[0])).sort((p, q) => q[3] - p[3]);
      chart('c_cob_imob', { data: { labels: im.map(x => title(x[0])), datasets: [bar('Valor inadimplente', im.map(x => x[3]), C.crit)] },
        options: { indexAxis: 'y', scales: { x: moneyAxis, y: plainAxis }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => { const x = im[c.dataIndex]; return [' Inadimplente: ' + full(x[3]), ' Vendido: ' + money(x[1]) + ' · recebido: ' + money(x[2]), ' % inadimplente s/ vendido: ' + pct(x[4], 2)]; } } } } } });
    },
    after() {
      let sortK = 5, dir = -1;
      const render = () => {
        const fe = $('#fEmp').value, ft = $('#fEt').value, q = $('#fQ').value.trim().toLowerCase();
        let rows = D.clientes.filter(c => (!fe || c[0] === fe) && (!ft || c[8] === ft) && (!q || [c[1], c[2], c[3]].join(' ').toLowerCase().includes(q)));
        rows.sort((x, y) => { const a = x[sortK], b = y[sortK]; return (typeof a === 'number' ? a - b : String(a).localeCompare(String(b), 'pt-BR')) * dir; });
        const tv = rows.reduce((s, c) => s + (c[5] || 0), 0);
        $('#fCount').textContent = rows.length + ' clientes · ' + full(tv) + ' vencidos';
        $('#tCli tbody').innerHTML = rows.map(c => `<tr><td>${sw(EMP_COLOR[c[0]] || '#bbb')}${esc(title(c[0]))}</td><td class="l">${esc(c[1])}</td><td class="l wrap2">${esc(c[2])}</td><td class="l wrap2">${esc(c[3])}</td><td>${int(c[4])}</td><td><b>${full(c[5])}</b></td><td>${full(c[6])}</td><td>${full(c[7])}</td><td class="l">${c[8] ? statusChip(c[8]) : ''}</td><td class="l">${c[9] ? c[9].split('-').reverse().join('/') : '<span class="dim">–</span>'}</td><td class="wrap">${esc(c[10])}</td></tr>`).join('');
      };
      ['#fEmp', '#fEt'].forEach(s => $(s).addEventListener('change', render));
      $('#fQ').addEventListener('input', render);
      document.querySelectorAll('#tCli th.sortable').forEach(th => th.addEventListener('click', () => { const k = +th.dataset.k; dir = sortK === k ? -dir : (k >= 4 && k <= 7 ? -1 : 1); sortK = k; render(); }));
      render();
    }
  };

  /* ================================================================= */
  /*                     SÓCIOS, GRUPO E IMPOSTOS                      */
  /* ================================================================= */
  PAGES.grupo = {
    title: 'Sócios, grupo e impostos', sub: 'Aportes, retiradas e lucros · intercompany · aplicações financeiras · tributos pagos',
    html() {
      const st = D.socios_tot;
      const soc = D.socios.map(s => `<tr><td>${esc(s[0])}</td><td>${mil(s[1])}</td><td>${mil(s[2])}</td><td>${mil(s[3])}</td><td><b>${mil(s[4])}</b></td></tr>`).join('') +
        `<tr class="total"><td>Total</td><td>${mil(st[0])}</td><td>${mil(st[1])}</td><td>${mil(st[2])}</td><td>${mil(st[3])}</td></tr>`;
      const pares = D.ic_pares.map(p => `<tr><td class="l">${esc(title(p[0]))}</td><td class="l">${esc(title(p[1]))}</td><td>${full(p[2])}</td></tr>`).join('') + `<tr class="total"><td class="l" colspan="2">Total</td><td>${full(D.ic_total)}</td></tr>`;
      const inv = D.inv.map(r => `<tr class="${r[0] === 'Total' ? 'total' : ''}"><td>${esc(r[0] === 'Total' ? 'Total' : title(r[0]))}</td><td>${full(r[1])}</td><td>${full(r[2])}</td><td>${full(r[3])}</td><td><b>${full(r[4])}</b></td><td>${pct(r[5], 2)}</td></tr>`).join('');
      const imp = D.imp.map(r => `<tr class="${r[0] === 'Total' ? 'total' : ''}"><td>${esc(r[0] === 'Total' ? 'Total' : title(r[0]))}</td>${r.slice(1, 8).map(v => `<td>${mil(v)}</td>`).join('')}<td>${pct(r[8])}</td></tr>`).join('');
      return `
      <div class="section-label">Sócios e terceiros</div>
      <div class="kpis">
        ${kpi('Total distribuído', money(-(st[1] + st[2])), 'retiradas + lucro a terceiros', true)}
        ${kpi('Lucro a terceiros', money(st[2]), '')}
        ${kpi('Retirada de sócios', money(st[1]), '')}
        ${kpi('Aporte de sócios', money(st[0]), 'entradas')}
        ${kpi('Beneficiários', '17', 'pessoas / empresas com movimento')}
      </div>
      <div class="grid g32">
        ${card('Resumo por pessoa / empresa', 'R$ mil · líquido = aporte + retirada + lucro a terceiros', `<div class="tbl-wrap scroll"><table class="t"><thead><tr><th>Pessoa / empresa</th><th>Aporte</th><th>Retirada</th><th>Lucro 3º</th><th>Líquido</th></tr></thead><tbody>${soc}</tbody></table></div>`)}
        ${card('Distribuições por ano', 'Líquido de aportes, retiradas e lucro a terceiros (saídas)', cv('c_soc_ano', 'tall'))}
      </div>
      <div class="section-label">Intercompany · quem deve para quem</div>
      <div class="grid g2">
        ${card('Posição líquida por empresa', 'Aporte de capital entre empresas · à direita = devedora líquida, à esquerda = credora líquida', cv('c_ic'))}
        ${card('Saldo por par de empresas', 'Saldo devido', `<div class="tbl-wrap"><table class="t"><thead><tr><th class="l">Quem deve</th><th class="l">Para quem</th><th>Saldo devido</th></tr></thead><tbody>${pares}</tbody></table></div>`)}
      </div>
      <div class="section-label">Aplicações financeiras</div>
      ${card('Rendimento de aplicações por empreendimento', 'Rendimento bruto, IRRF, IOF e rendimento líquido', `<div class="tbl-wrap"><table class="t"><thead><tr><th>Empreendimento</th><th>Rend. bruto</th><th>IRRF</th><th>IOF</th><th>Rend. líquido</th><th>Alíquota IRRF</th></tr></thead><tbody>${inv}</tbody></table></div>`)}
      <div class="section-label">Impostos</div>
      <div class="grid">
        ${card('Impostos pagos por empreendimento', 'Por tributo · regime de caixa · total ' + money(-D.imp[D.imp.length - 1][7]), cv('c_imp'))}
      </div>
      <div class="grid">
        ${card('Detalhe por tributo', 'R$ mil', `<div class="tbl-wrap"><table class="t"><thead><tr><th>Empreend.</th><th>PIS/COFINS</th><th>IRPJ</th><th>CSLL</th><th>IRPJ/CSLL</th><th>RET</th><th>Imp. fed.</th><th>Total</th><th>%</th></tr></thead><tbody>${imp}</tbody></table></div>`)}
      </div>`;
    },
    charts() {
      chart('c_soc_ano', { data: { labels: D.socios_anos, datasets: [bar('Distribuição líquida', D.socios_anual.map(v => -v), C.ink)] },
        options: { scales: { x: plainAxis, y: moneyAxis }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ' ' + full(c.parsed.y) } } } } });
      const ic = D.ic_pos.slice().sort((a, b) => b[1] - a[1]);
      chart('c_ic', { data: { labels: ic.map(x => title(x[0])), datasets: [bar('Saldo líquido', ic.map(x => x[1]), ic.map(x => x[1] >= 0 ? C.s8 : C.s1))] },
        options: { indexAxis: 'y', scales: { x: moneyAxis, y: plainAxis }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ' ' + ic[c.dataIndex][2] + ': ' + full(Math.abs(c.parsed.x)) } } } } });
      const rows = D.imp.filter(r => r[0] !== 'Total' && Math.abs(r[7]) > 0);
      const trib = ['PIS/COFINS', 'IRPJ', 'CSLL', 'IRPJ/CSLL', 'RET', 'Imp. federais'], col = [C.s1, C.s2, C.s3, C.s4, C.s5, C.s6];
      chart('c_imp', { data: { labels: rows.map(r => title(r[0])), datasets: trib.map((t, i) => bar(t, rows.map(r => -r[i + 1]), col[i], { stack: 's' })) },
        options: { indexAxis: 'y', scales: { x: Object.assign({ stacked: true }, moneyAxis), y: Object.assign({ stacked: true }, plainAxis) },
          plugins: { tooltip: { filter: c => c.parsed.x > 0, callbacks: { label: c => ' ' + c.dataset.label + ': ' + full(c.parsed.x), footer: it => 'Total: ' + full(-rows[it[0].dataIndex][7]) } } } } });
    }
  };
})();
