"""Build public/capex.html from tools/capex/page.html. Data: public/capex/data/*.csv (see prepare_data.py).
Run from anywhere: python3 tools/capex/build_capex.py
The page script was written for the Claude dashboard runtime; a small shim below provides the same
`dash` API (data, calc, draw, colors) over static CSV files, so the drawing code stays unchanged."""
import os, re, shutil, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, '..', '..', 'public')   # repo layout: tools/capex -> public/
BASE = 'https://aicapex.sjoonkwon.com'
DATASETS = ['quarterly', 'era', 'periods', 'leases', 'commit', 'nonlease', 'snapshot', 'amzn_seg', 'kr_mem', 'kr_customs']

page = open(os.path.join(HERE, 'page.html'), encoding='utf-8').read()
page = page.replace('<meta name="dash-one-writer">\n', '')

# ---- new panel n: 2026 customs breakdown (fixed snapshot) ----
card_n = '''
    <section class="card wide" id="fig-n">
      <p class="cap"><span class="lab">n</span><span class="note">한국 메모리 수출을 관세청 10자리 품목으로 나눈 값, <span data-n="period">—</span>(십억 달러). 늘어난 금액 가운데 범용 D램이 <span data-n="dram_share">—</span>, 복합구조칩이 <span data-n="hbm_share">—</span>입니다. 복합구조칩은 대만행 몫이 커서 HBM으로 보이지만, 품목명에 HBM이 따로 있지는 않습니다. <span data-n="src">—</span></span></p>
      <div class="chart" style="min-height:0" data-draw="chartN" data-source="kr_customs"></div>
    </section>
'''
anchor = '    <section class="card" id="fig-d">'
assert page.count(anchor) == 1
page = page.replace(anchor, card_n + '\n' + anchor)
li_old = '    </ul>\n  </section>'
assert page.count(li_old) == 1
page = page.replace(li_old, '      <li>그림 n은 관세청 품목별 수출입실적(공공데이터포털 API, 10자리 HSK 854232xxxx)을 1~9월끼리 더한 값입니다. 2021~2025년 대만행 분기 값은 UN Comtrade와 금액·중량 모두 일치했습니다. 이 그림은 연구실의 매일 수집 자료(메모리 국면 모니터의 공개 데이터)를 읽어 매일 갱신되며, 그 자료를 불러오지 못하면 2026년 11월 5일에 고정한 값으로 그립니다. 범용 D램 가격 국면은 <a href="https://memsim.sjoonkwon.com">메모리 국면 모니터</a>에서 매일 갱신됩니다.</li>\n' + li_old)

chart_n = r'''
<script>
(function () {
  const N = (x) => (x === '' || x == null ? NaN : Number(x));
  dash.draw('chartN', (el) => {
    const g = dash.data('kr_customs');
    if (g.status !== 'ok') { el.textContent = '—'; return; }
    const r0 = g.data[0] || {}; const LA = `${r0.y_prev}년 1~${r0.m_last}월`, LB = `${r0.y_cur}년 1~${r0.m_last}월`;
    const rows = g.data.map((r) => ({ code: r.code, item: r.item, a: N(r.v_prev), b: N(r.v_cur), ta: N(r.t_prev), tb: N(r.t_cur) }));
    const inc = d3.sum(rows, (r) => r.b - r.a), share = (c) => { const x = rows.find((r) => r.code === c); return x && inc > 0 ? d3.format('.0%')((x.b - x.a) / inc) : '—'; };
    const setN = (k, v) => document.querySelectorAll(`[data-n="${k}"]`).forEach((e) => { e.textContent = v; });
    setN('period', `${LA}과 ${LB}`); setN('dram_share', share('8542321010')); setN('hbm_share', share('8542323000'));
    setN('src', g.from === 'live' ? '매일 갱신됩니다.' : '2026년 11월 5일 기준 고정 값입니다.');
    el.replaceChildren();
    const W = el.clientWidth, rowH = 46, M = { t: 28, r: 64, b: 24, l: Math.min(170, W * 0.36) };
    const H = M.t + rows.length * rowH + M.b;
    const svg = d3.select(el).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
    const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => Math.max(r.a, r.b)) * 1.08]).range([M.l, W - M.r]).nice();
    const y = d3.scaleBand().domain(rows.map((r) => r.item)).range([M.t, H - M.b]).padding(0.18);
    const c = dash.colors;
    svg.append('g').attr('transform', `translate(0,${M.t - 6})`).call(d3.axisTop(x).ticks(Math.max(3, Math.floor(W / 120))).tickSize(-(H - M.t - M.b + 6)))
      .call((s) => { s.select('.domain').remove(); s.selectAll('line').attr('stroke', 'var(--cds-chart-grid)'); });
    const half = y.bandwidth() / 2;
    const tip = (() => { let t = el.querySelector(':scope > .tt'); if (!t) { t = document.createElement('div'); t.className = 'tt'; t.hidden = true; el.appendChild(t); } return t; })();
    const show = (ev, r) => {
      tip.replaceChildren();
      const h = document.createElement('div'); h.className = 'h'; h.textContent = r.item; tip.appendChild(h);
      [[c[7], LA, r.a, r.ta], [c[0], LB, r.b, r.tb]].forEach(([col, lab, v, t]) => {
        const d = document.createElement('div'); const i = document.createElement('i'); i.style.background = col; d.appendChild(i);
        d.appendChild(document.createTextNode(`${lab}  ${d3.format(',.1f')(v)}십억 달러 · ${d3.format(',.0f')(t)}톤`)); tip.appendChild(d);
      });
      const [px, py] = d3.pointer(ev, el); tip.hidden = false;
      let left = px + 14; if (left + tip.offsetWidth > el.clientWidth) left = px - tip.offsetWidth - 14; if (left < 0) left = 0;
      tip.style.left = left + 'px'; tip.style.top = Math.max(0, py - tip.offsetHeight - 8) + 'px';
    };
    const gr = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (r) => `translate(0,${y(r.item)})`)
      .on('mousemove', show).on('mouseleave', () => { tip.hidden = true; });
    gr.append('rect').attr('x', M.l).attr('y', 0).attr('width', W - M.l - M.r).attr('height', y.bandwidth()).attr('fill', 'transparent');
    gr.append('rect').attr('x', x(0)).attr('y', 1).attr('height', half - 2).attr('width', (r) => x(r.a) - x(0)).attr('fill', c[7]).attr('rx', 2);
    gr.append('rect').attr('x', x(0)).attr('y', half + 1).attr('height', half - 2).attr('width', (r) => x(r.b) - x(0)).attr('fill', c[0]).attr('rx', 2);
    gr.append('text').attr('x', M.l - 10).attr('y', y.bandwidth() / 2).attr('dy', '0.35em').attr('text-anchor', 'end').attr('class', 'strong').text((r) => r.item);
    gr.append('text').attr('x', (r) => x(r.b) + 6).attr('y', half * 1.5).attr('dy', '0.35em')
      .text((r) => (r.a > 0 ? '×' + d3.format('.1f')(r.b / r.a) : ''));
    const lg = svg.append('g').attr('transform', `translate(${M.l},${H - 6})`);
    [[c[7], LA], [c[0], LB]].forEach(([col, lab], i) => {
      const gg = lg.append('g').attr('transform', `translate(${i * 130},0)`);
      gg.append('rect').attr('y', -10).attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', col);
      gg.append('text').attr('x', 15).attr('y', -1).text(lab);
    });
  });
})();
</script>
'''

shim = r'''<script>
/* Static stand-in for the dashboard runtime: loads CSVs and offers data/calc/draw/colors. */
(function () {
  const DATASETS = __DATASETS__;
  const store = {}, calcs = {}, draws = [];
  const palette = () => ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6', '--s7', '--s8'].map((v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim());
  const memo = {};
  function data(id) {
    if (store[id]) return store[id];
    const c = calcs[id];
    if (!c) return { status: 'missing', data: [], columns: [] };
    if (memo[id]) return memo[id];
    const ins = c.inputs.map(data);
    if (ins.some((g) => g.status === 'error')) return { status: 'error', data: [], columns: [] };
    if (ins.some((g) => g.status !== 'ok')) return { status: 'loading', data: [], columns: [] };
    try {
      const out = c.fn(...ins.map((g) => g.data));
      const rows = Array.isArray(out) ? out : [out];
      return (memo[id] = { status: 'ok', data: rows, columns: rows.length ? Object.keys(rows[0]) : [] });
    } catch (e) { console.error('calc', id, e); return (memo[id] = { status: 'error', data: [], columns: [] }); }
  }
  function renderAll() {
    for (const [name, fn] of draws) document.querySelectorAll(`#dash-root [data-draw="${name}"]`).forEach((el) => { try { fn(el); } catch (e) { console.error('draw', name, e); } });
  }
  window.dash = {
    data, calc: (id, spec) => { calcs[id] = spec; },
    draw: (name, fn) => { draws.push([name, fn]); },
    get colors() { return palette(); },
    onData: (fn) => { draws.push(['__all__', fn]); },
  };
  DATASETS.forEach((id) => { store[id] = { status: 'loading', data: [], columns: [] }; });
  const REMOTE = { kr_customs: 'https://memsim.sjoonkwon.com/data/kr_customs_ytd.csv' };
  const load = (id) => {
    const local = () => d3.csv(`/capex/data/${id}.csv`).then((rows) => ({ rows, from: 'local' }));
    return REMOTE[id] ? d3.csv(REMOTE[id], { cache: 'no-store' }).then((rows) => (rows.length ? { rows, from: 'live' } : local()), local) : local();
  };
  Promise.all(DATASETS.map((id) => load(id).then(({ rows, from }) => { store[id] = { status: 'ok', data: rows, columns: rows.columns, from }; },
    () => { store[id] = { status: 'error', data: [], columns: [] }; })))
    .then(() => {
      renderAll();
      let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(renderAll, 150); });
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', renderAll);
    });
})();
</script>'''.replace('__DATASETS__', str(DATASETS))

head = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>빅테크 AI 설비투자 추적</title>
<meta name="description" content="마이크로소프트·알파벳·아마존·메타의 분기 설비투자, 현금흐름, 리스·구매 약정과 한국 메모리 수출. SEC EDGAR·UN Comtrade·관세청 자료. 권석준(성균관대학교).">
<meta name="author" content="권석준"><meta property="og:type" content="website"><meta property="og:title" content="빅테크 AI 설비투자 추적"><meta property="og:url" content="''' + BASE + '''/capex"><link rel="canonical" href="''' + BASE + '''/capex">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600&family=Noto+Serif+KR:wght@400;600&family=Roboto+Condensed:wght@400;700&display=swap">
<style>
/* Layout: one column of figure cards under a short lead; tokens stand in for the dashboard theme. */
:root {
  color-scheme: light;
  --bg: #f5f6f4; --color-fg: #15191c; --color-fg-muted: #5a6268; --color-panel: #ffffff; --color-border-line: #dde1dd;
  --color-bad: #c2372f; --color-ok: #1a7f37; --color-warn: #9a6200;
  --font-anthropic-sans: "IBM Plex Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  --font-anthropic-serif: "Noto Serif KR", "AppleMyungjo", "Batang", Georgia, serif;
  --cds-gap-xs: 6px; --cds-gap-sm: 10px; --cds-gap-md: 18px; --cds-gap-lg: 28px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-lg: 20px; --cds-radius: 8px;
  --cds-font-size-caption: 13.5px; --cds-font-size-heading: 17px; --cds-font-size-title: clamp(26px, 4vw, 34px); --cds-font-weight-medium: 600;
  --cds-border: #d3d8d4; --cds-surface-popover: #ffffff; --cds-shadow-popover: 0 4px 16px rgba(20,25,28,.12); --cds-text-secondary: #5a6268;
  --cds-chart-axis: #b9beba; --cds-chart-grid: #e8ebe8; --cds-chart-muted: #a7adaa; --cds-chart-reference: #7c8480; --cds-chart-status-critical: #c2372f; --cds-dur-slow: .3s;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100; --s5: #e87ba4; --s6: #008300; --s7: #6250d6; --s8: #9aa19d;
  --hb-bg: #eef2f1; --hb-ink: #1f5d73; --hb-rule: #d5dcda;
  padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px);
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  color-scheme: dark; --bg: #121618; --color-fg: #e8ecec; --color-fg-muted: #a3acaf; --color-panel: #1a1f22; --color-border-line: #2c3337;
  --cds-border: #384045; --cds-surface-popover: #22292c; --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.4); --cds-text-secondary: #a3acaf;
  --cds-chart-axis: #4a5357; --cds-chart-grid: #262d30; --cds-chart-muted: #5f686c; --cds-chart-reference: #8b9498;
  --s1: #5b9cf0; --s2: #f08a5d; --s3: #3cc995; --s4: #f2b93b; --s5: #f09bbb; --s6: #3fae3f; --s7: #8a7cf0; --s8: #6f777b;
  --hb-bg: #172024; --hb-ink: #7cc0d6; --hb-rule: #2c3337; } }
:root[data-theme="dark"] {
  color-scheme: dark; --bg: #121618; --color-fg: #e8ecec; --color-fg-muted: #a3acaf; --color-panel: #1a1f22; --color-border-line: #2c3337;
  --cds-border: #384045; --cds-surface-popover: #22292c; --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.4); --cds-text-secondary: #a3acaf;
  --cds-chart-axis: #4a5357; --cds-chart-grid: #262d30; --cds-chart-muted: #5f686c; --cds-chart-reference: #8b9498;
  --s1: #5b9cf0; --s2: #f08a5d; --s3: #3cc995; --s4: #f2b93b; --s5: #f09bbb; --s6: #3fae3f; --s7: #8a7cf0; --s8: #6f777b;
  --hb-bg: #172024; --hb-ink: #7cc0d6; --hb-rule: #2c3337; }
body { margin: 0; background: var(--bg); color: var(--color-fg); font: 15px/1.6 var(--font-anthropic-sans); }
#dash-root { max-width: 1240px; margin: 0 auto; padding-block: 28px 56px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
#dash-root a { color: var(--hb-ink); }
.hub-back { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; background: var(--hb-bg); border-bottom: 1px solid var(--hb-rule); padding-block: 9px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); font: 500 13px var(--font-anthropic-sans); }
.hub-back a { color: var(--hb-ink); text-decoration: none; } .hub-back a:hover { text-decoration: underline; }
.asof { margin: 0; color: var(--color-fg-muted); font-size: 13px; }
.bt .chart .domain { stroke: var(--cds-chart-axis); }
.bt .chart .tick line { stroke: var(--cds-chart-grid); }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
</head><body>
<nav class="hub-back" aria-label="시뮬레이터 목록"><a href="/">← 빅테크 AI 투자 시뮬레이터 · 권석준</a><span><a href="/hyperscaler">주가·조달</a> · <a href="/google">구글 전략</a> · <a href="/commerce">에이전트 커머스</a> · <a href="https://memsim.sjoonkwon.com">메모리 국면</a></span></nav>
<div id="dash-root">
'''
asof = '<p class="asof">자료 기준: SEC 공시 2026년 3분기까지, UN Comtrade 2025년 12월까지, 관세청 2026년 9월까지. 매달 22일 새 공시와 무역 통계로 갱신합니다. 투자 권유가 아닙니다.</p>\n'
page = page.replace('  </header>', '  </header>\n' + asof, 1)
# the dashboard page carries its own <script> block; the shim must run before it
i = page.index('<script>')
html = head + page[:i] + '\n</div>\n' + shim + '\n' + page[i:] + chart_n + '\n</body></html>\n'
os.makedirs(os.path.join(SITE, 'capex', 'data'), exist_ok=True)
open(os.path.join(SITE, 'capex.html'), 'w', encoding='utf-8').write(html)
# data already lives in public/capex/data (written by prepare_data.py; kr_customs.csv is a fixed snapshot)
for d in DATASETS:
    assert os.path.exists(os.path.join(SITE, 'capex', 'data', d + '.csv')), d
print('capex.html', len(html))
