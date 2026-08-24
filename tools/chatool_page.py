# -*- coding: utf-8 -*-
"""런처 화면. 순수 HTML/CSS/JS 한 장이라 어떤 브라우저에서도 그냥 열립니다.

chatool.py 의 웹 런처와 창 런처가 **이 같은 화면**을 씁니다.
"""

PAGE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>다함께 차차차 — 런처</title>
<style>
  /* 어두운 쪽이 기본입니다. 밝은 쪽은 아래에서 색만 바꿔 끼웁니다.
     `data-theme` 이 없으면 = 시스템을 따릅니다. */
  :root{
    --bg:#12141a; --panel:#1b1e27; --panel2:#232734; --line:#2f3444;
    --ink:#e8eaf0; --dim:#98a0b4; --accent:#ffa53d; --accent2:#4db2ff;
    --ok:#4ade80; --bad:#f87171; --sel:#2a2010; --sep:#232733;
    /* 굳은 색을 여기로 모았습니다. 밝은 쪽에서 하나라도 빠지면 글자가
       바탕에 파묻힙니다 — 실제로 그랬습니다. */
    --field:#141720;      /* 입력칸 바탕 */
    --hover:#4a5064;      /* 단추에 손 얹었을 때 테두리 */
    --onaccent:#241400;   /* 주 단추 글자 */
    --onaccent2:#03202f;  /* 켜진 탭 글자 */
    --dot:#3a4053;        /* 목록 앞의 점 */
    --code:#0d1017;       /* 로그 · 캔버스 바탕 */
    --codefg:#9fb0c8;     /* 로그 글자 */
    --dash:#3c4358;       /* 끌어다 놓는 자리 테두리 */
    --have:#4a6a3a;       /* 가지고 있는 드라이버 테두리 */
    --okbg:#16241b; --okline:#2c4a38; --okfg:#bfe6cd;
    --warnbg:#2a1a1a; --warnline:#4a2c2c; --warnfg:#f0c9c9;
  }
  :root[data-theme=light]{
      --bg:#f4f5f8; --panel:#ffffff; --panel2:#eef0f5; --line:#d8dce6;
    --ink:#1a1d26; --dim:#5d6577; --accent:#b7621a; --accent2:#1d6fa8;
    --ok:#1f7a45; --bad:#c0392b; --sel:#fdf1e0; --sep:#e6e9f0;
    --field:#ffffff; --hover:#a8b0c0;
    --onaccent:#ffffff; --onaccent2:#ffffff;
    --dot:#c3c9d6; --code:#f7f8fb; --codefg:#3c4454; --dash:#b9c0cf;
    --have:#5f8c46;
    --okbg:#e9f5ed; --okline:#a9d6b9; --okfg:#1c5c36;
    --warnbg:#fdeceb; --warnline:#efb9b6; --warnfg:#8c2b23;
  }
  @media(prefers-color-scheme:light){
    :root:not([data-theme=dark]){
      --bg:#f4f5f8; --panel:#ffffff; --panel2:#eef0f5; --line:#d8dce6;
      --ink:#1a1d26; --dim:#5d6577; --accent:#b7621a; --accent2:#1d6fa8;
      --ok:#1f7a45; --bad:#c0392b; --sel:#fdf1e0; --sep:#e6e9f0;
      --field:#ffffff; --hover:#a8b0c0;
      --onaccent:#ffffff; --onaccent2:#ffffff;
      --dot:#c3c9d6; --code:#f7f8fb; --codefg:#3c4454; --dash:#b9c0cf;
      --have:#5f8c46;
      --okbg:#e9f5ed; --okline:#a9d6b9; --okfg:#1c5c36;
      --warnbg:#fdeceb; --warnline:#efb9b6; --warnfg:#8c2b23;
    }
  }
  .setsel{width:auto;min-width:104px;padding:3px 8px;font-size:12px}
  /* 기기가 없을 때만 나오는 다시 확인 단추 */
  .iconbtn{display:none;padding:4px 7px;line-height:0;color:var(--dim)}
  .iconbtn.on{display:inline-flex;align-items:center}
  .iconbtn:hover{color:var(--ink);border-color:var(--hover)}
  .iconbtn.spin svg{animation:turn .9s linear infinite}
  @keyframes turn{ to{ transform:rotate(360deg) } }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:14px/1.55 "Malgun Gothic","맑은 고딕",system-ui,sans-serif}
  header{display:flex;align-items:center;gap:14px;padding:14px 20px;
         background:var(--panel);border-bottom:1px solid var(--line)}
  header h1{margin:0;font-size:17px;letter-spacing:-.02em}
  header .sp{flex:1}
  .pill{font-size:12px;padding:3px 10px;border-radius:999px;
        background:var(--panel2);border:1px solid var(--line);color:var(--dim)}
  .pill.on{color:var(--ok);border-color:var(--okline)}
  .pill.off{color:var(--bad);border-color:var(--warnline)}
  main{display:block;padding:16px;max-width:1560px;margin:0 auto}
  /* 짧은 카드는 나란히 놓는다. 세로로만 쌓으면 스크롤이 길어진다.
     좁아지면 알아서 한 줄로 내려온다. */
  .side{display:grid;grid-template-columns:1fr 1fr;gap:0 14px;
        align-items:start}
  @media(max-width:1080px){ .side{grid-template-columns:1fr} }
  .side>.card{margin-bottom:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
        padding:14px 16px;margin-bottom:14px}
  .card h2{margin:0 0 10px;font-size:13px;color:var(--dim);font-weight:600;
           letter-spacing:.04em;text-transform:uppercase}
  button{font:inherit;color:var(--ink);background:var(--panel2);
         border:1px solid var(--line);border-radius:7px;padding:6px 12px;
         cursor:pointer}
  button:hover{border-color:var(--hover)}
  button.primary{background:var(--accent);border-color:var(--accent);
               color:var(--onaccent);
                 font-weight:700}
  button.danger:hover{border-color:var(--bad);color:var(--bad)}
  input,select{font:inherit;color:var(--ink);background:var(--field);
       border:1px solid var(--line);border-radius:6px;padding:5px 8px;width:100%}
  input[type=checkbox]{width:auto}
  .slot{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:7px;
        cursor:pointer;border:1px solid transparent}
  .slot:hover{background:var(--panel2)}
  .slot.sel{background:var(--sel);border-color:var(--accent)}
  .slot .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .slot .dot{width:8px;height:8px;border-radius:50%;background:var(--dot)}
  .slot.sel .dot{background:var(--accent)}
  .row{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
       gap:10px}
  label.f{display:block;font-size:12px;color:var(--dim);margin-bottom:3px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
        gap:6px 10px}
  .chk{display:flex;align-items:center;gap:7px;padding:3px 0;font-size:13px}
  .chk span.no{color:var(--dim);font-size:11px;min-width:22px}
  .tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
  .tabs button.on{background:var(--accent2);border-color:var(--accent2);
                color:var(--onaccent2);
                  font-weight:700}
  .bar{position:fixed;left:0;right:0;bottom:0;background:var(--panel);
       border-top:1px solid var(--line);padding:10px 20px;display:flex;
       align-items:center;gap:12px}
  .bar .msg{flex:1;color:var(--dim);font-size:13px}
  .pad{padding-bottom:64px}
  .hint{color:var(--dim);font-size:12px;margin-top:6px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  td{padding:3px 6px;border-bottom:1px solid var(--sep)}
  td:first-child{color:var(--dim)}
  td input{width:90px}
  /* 드라이버 프로필 카드 */
  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));
         gap:10px;margin-top:10px}
  .dcard{display:flex;gap:10px;background:var(--panel2);border-radius:9px;
         border:1px solid var(--line);padding:10px}
  .dcard.have{border-color:var(--have)}
  .dcard img{width:72px;height:73px;image-rendering:pixelated;border-radius:7px;
             border:1px solid var(--line);background:var(--code);flex:none}
  .dcard .b{flex:1;min-width:0}
  .dcard .nm{font-weight:700;display:flex;gap:6px;align-items:center}
  .dcard .nm .no{color:var(--dim);font-size:11px;font-weight:400}
  .dcard .ex{color:var(--dim);font-size:12px;line-height:1.45;margin:3px 0 6px}
  .dcard .ft{display:flex;gap:6px;align-items:center;flex-wrap:wrap;
             font-size:12px;color:var(--dim)}
  .dcard button{padding:3px 8px;font-size:12px}
  /* 저장 및 내보내기 탭 */
  .two{display:grid;grid-template-columns:minmax(280px,1fr) minmax(300px,1.2fr);
       gap:16px;align-items:start}
  @media(max-width:820px){ .two{grid-template-columns:1fr} }
  .btns{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
  .tag{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--panel2);
       border:1px solid var(--line);color:var(--dim);white-space:nowrap}
  .dh{font-size:15px;margin-bottom:2px}
  .sec{margin-top:10px;border-top:1px solid var(--line)}
  .sec>summary{cursor:pointer;list-style:none;padding:7px 0 5px;
       font-size:12px;color:var(--dim);font-weight:600;letter-spacing:.04em;
       text-transform:uppercase;display:flex;align-items:center;gap:6px}
  .sec>summary::-webkit-details-marker{display:none}
  .sec>summary::before{content:'▸';font-size:11px;color:var(--dim);
       transition:transform .12s;display:inline-block;width:10px}
  .sec[open]>summary::before{transform:rotate(90deg)}
  .sec>summary:hover{color:var(--ink)}
  /* 값이 모두 같은 세로선에 서게 첫 칸을 못박습니다. 섹션마다 표가 달라도
     너비가 같으니 눈이 한 줄로 읽습니다. */
  table.kv{table-layout:fixed;width:100%}
  table.kv td:first-child{width:150px;color:var(--dim);
       overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  table.kv td:last-child{word-break:break-word}
  .pcard{background:var(--panel2);border:1px solid var(--line);border-radius:9px;
         padding:10px 12px;margin-top:8px;cursor:pointer}
  .pcard:hover{border-color:var(--accent)}
  .pcard .nm{font-weight:700}
  .pcard .ex{color:var(--dim);font-size:12px;margin:3px 0}
  .pcard .ft{display:flex;gap:5px;flex-wrap:wrap;margin:6px 0}
  .note{border-radius:9px;padding:10px 14px;margin-bottom:14px;font-size:13px}
  .note ul{margin:6px 0;padding-left:18px}
  .note.ok{background:var(--okbg);border:1px solid var(--okline);
         color:var(--okfg)}
  .note.warn{background:var(--warnbg);border:1px solid var(--warnline);
           color:var(--warnfg)}
  .note button{margin-top:6px}
  .wgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));
         gap:8px;margin:8px 0}
  .wcard{background:var(--panel2);border:1px solid var(--line);border-radius:9px;
         padding:10px 12px;cursor:pointer}
  .wcard:hover{border-color:var(--hover)}
  .wcard.on{border-color:var(--accent);background:var(--sel)}
  .wcard .nm{font-weight:700;display:flex;gap:7px;align-items:center}
  .wcard .ex{color:var(--dim);font-size:12px;margin-top:4px;line-height:1.45}
  .steps{margin:2px 0 10px;padding-left:18px;color:var(--dim);font-size:12px}
</style>
</head>
<body>
<header>
  <h1><span id="h_app">다함께 차차차</span>
      <span id="h_sub" style="color:var(--dim);font-weight:400">런처</span></h1>
  <span class="sp"></span>
  <button id="adbre" class="iconbtn" onclick="reScan()" title="">
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none"
         stroke="currentColor" stroke-width="2.1" stroke-linecap="round"
         stroke-linejoin="round" aria-hidden="true">
      <polyline points="23 4 23 10 17 10"></polyline>
      <polyline points="1 20 1 14 7 14"></polyline>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
    </svg>
  </button>
  <span class="pill" id="adb">기기를 확인하는 중입니다…</span>
  <select id="adbpick" class="setsel" onchange="pickDev2(this.value)"
          style="display:none"></select>
  <span class="pill" id="cur">—</span>
  <select id="uitheme" class="setsel" onchange="setTheme(this.value)"></select>
  <select id="uilang" class="setsel" onchange="setLang(this.value)"></select>
</header>

<main class="pad">
  <div>
    <div class="tabs" id="tabs"></div>
    <div id="body"></div>
  </div>
</main>

<div class="bar">
  <span class="msg" id="msg">준비됐습니다.</span>
  <button id="b_revert" onclick="load()">되돌리기</button>
  <button id="b_save" class="primary" onclick="save()">저장</button>
</div>

<script>
let S=null, cur=null, tab='플레이어';   /* 탭 이름은 열쇠로 든다 */
const $=s=>document.querySelector(s);
const say=(t,bad)=>{const m=$('#msg');m.textContent=t;m.style.color=bad?'var(--bad)':'var(--dim)';};

/* ===================================================== 말 (i18n)
   열쇠는 **한국어 원문 그대로**입니다. `lang/en.json` 처럼 값만 바꾼 파일을
   넣으면 언어가 하나 늘어납니다. 번역이 빠진 자리는 한국어로 나오므로 어디가
   덜 됐는지 눈에 바로 띕니다.

     T('세이브')                  ->  Saves
     T('{n}개를 찾았습니다',{n:3}) ->  Found 3
*/
let L={}, UI={lang:'kr', theme:'system', langs:[]};
function T(s, v){
  /* 열쇠 뒤의 `|뜻가름`(예: '기록|주행')은 한국어로 볼 때 떼어 냅니다.
     한국어에서 같은 말이 다른 언어에서 갈리는 자리에만 씁니다. */
  let o = L[s];
  if(o===undefined || o===''){ const i=s.lastIndexOf('|'); o = i>0 ? s.slice(0,i) : s; }
  if(v) for(const k in v) o = o.split('{'+k+'}').join(v[k]);
  return o;
}
async function loadUI(){
  try{
    const j = await post('/api/ui',{});
    if(j && j.ok){ L=j.strings||{}; UI=Object.assign(UI,j); }
  }catch(x){}
  applyTheme(); drawChrome();
}
function applyTheme(){
  const r=document.documentElement;
  if(UI.theme==='system') r.removeAttribute('data-theme');
  else r.setAttribute('data-theme', UI.theme);
}
/* 화면 바깥틀(제목 · 고르개)은 탭을 다시 그려도 그대로라 따로 칠합니다. */
function drawChrome(){
  document.title=T('다함께 차차차 — 런처');
  const h=$('#h_app'); if(h) h.textContent=T('다함께 차차차');
  const h2=$('#h_sub'); if(h2) h2.textContent=T('런처');
  const th=$('#uitheme');
  if(th){
    const opts=[['system',T('시스템 따라')],['light',T('밝게')],['dark',T('어둡게')]];
    th.innerHTML=opts.map(o=>`<option value="${o[0]}">${esc(o[1])}</option>`).join('');
    th.value=UI.theme;
  }
  const lg=$('#uilang');
  if(lg){
    lg.innerHTML=(UI.langs||[]).map(o=>
      `<option value="${esc(o.code)}">${esc(o.name)}</option>`).join('');
    lg.value=UI.lang;
  }
  const b=$('#b_revert'); if(b) b.textContent=T('되돌리기');
  const b2=$('#b_save'); if(b2) b2.textContent=T('저장');
  const ad=$('#adb'); if(ad && !S) ad.textContent=T('기기를 확인하는 중입니다…');
  const ms=$('#msg'); if(ms && !S) ms.textContent=T('준비됐습니다.');
  if(S) drawDevBar();      /* 기기 칸도 그 말로 다시 */
}
/* 머리말의 기기 칸.

   · 붙어 있으면  = 어느 기기인지 보여 준다
   · 없으면      = 다시 확인 단추를 왼쪽에 내놓는다 (꽂고 나서 누르면 된다)
   · 둘 이상이면 = 어느 쪽에 넣을지 고르게 한다.
     adb 는 기기가 둘이면 그냥 실패하므로 고르는 것이 곧 쓸 수 있는 조건이다. */
function drawDevBar(){
  const a=$('#adb'), b=$('#adbre'), sel=$('#adbpick');
  const list=(S && S.adb && S.adb.devices) || [];
  const ok = !!(S && S.adb && S.adb.ok);
  if(a){
    a.className = 'pill ' + (ok ? 'on' : 'off');
    a.textContent = ok ? T('기기 연결됨 ({list})', {list:list.join(', ')})
                       : T('연결된 기기가 없습니다');
  }
  if(b){
    b.className = 'iconbtn' + (ok ? '' : ' on');
    b.title = T('기기를 다시 확인합니다');
  }
  if(sel){
    if(list.length > 1){
      sel.style.display='';
      sel.innerHTML = list.map(d=>
        `<option value="${esc(d)}">${esc(d)}</option>`).join('');
      sel.value = (S.adb.chosen || list[0]);
      sel.title = T('어느 기기에 넣을지 고릅니다');
    } else {
      sel.style.display='none';
    }
  }
}
async function pickDev2(serial){
  await post('/api/adb/pick', {serial});
  await load();
}
async function reScan(){
  const b=$('#adbre'); if(b) b.classList.add('spin');
  const a=$('#adb'); if(a) a.textContent=T('기기를 확인하는 중입니다…');
  try{ await load(); } finally { if(b) b.classList.remove('spin'); }
  if(S && S.adb && !S.adb.ok) say(T('아직 안 보입니다. USB 를 꽂고 폰에서 '
    + 'USB 디버깅을 허용했는지 보세요.'), true);
}
async function setTheme(v){
  UI.theme=v; applyTheme();
  if(typeof aClear==='function'){ aClear(); if(typeof aDraw==='function') aDraw(); }
  await post('/api/ui/set',{theme:v});
}
async function setLang(v){
  const j=await post('/api/ui/set',{lang:v});
  if(j&&j.ok){ L=j.strings||{}; UI.lang=j.lang; }
  drawChrome(); await load();
}

async function api(path,body){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},
                            body:JSON.stringify(body||{})});
  const j=await r.json();
  say(j.msg||'', j.ok===false);
  await load();
  return j;
}
async function load(){
  const r=await fetch('/api/state'); S=await r.json(); cur=S.active;
  drawDevBar();
  $('#cur').textContent=T('사용 중: {name}',{name:cur||'—'});
  drawTabs(); draw(); drawSlots();
  if(S.adb.ok) loadApps();
}
function drawSlots(){
  /* 세이브 목록은 '저장 및 내보내기' 탭 안에만 있습니다. 다른 탭에서는
     자리가 없으니 조용히 지나갑니다. */
  if(!$('#slots')) return;
  $('#slots').innerHTML=S.slots.map(n=>{
    const b=(typeof O!=='undefined' && O.brief) ? O.brief[n] : '';
    return `<div class="slot ${n===cur?'sel':''}" onclick="pick('${esc(n)}')">
       <span class="dot"></span><span class="nm">${esc(n)}`
       + (b?`<div class="hint" style="margin:0">${esc(b)}</div>`:'')
       + `</span></div>`;}).join('');
}
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function pick(n){ api('/api/slot/select',{name:n}); }
function newSlot(){ const n=prompt(T('새 세이브 이름을 적으세요'),T('새 세이브')); if(n) api('/api/slot/new',{name:n}); }
function copySlot(){ const n=prompt(T('복제본 이름을 적으세요'), T('{name} 복사',{name:cur})); if(n) api('/api/slot/new',{name:n,copyFrom:cur}); }
function renameSlot(){ const n=prompt(T('새 이름을 적으세요'), cur); if(n&&n!==cur) api('/api/slot/rename',{name:cur,to:n}); }
function delSlot(){ if(confirm(cur+T(' 을(를) 지울까요?'))) api('/api/slot/delete',{name:cur,active:cur}); }
function pull(){ const n=prompt(T('가져온 세이브를 어떤 이름으로 저장할까요?'),T('기기에서'));
  if(n) api('/api/adb/pull',{name:n,pkg:tgtPkg()}); }
function tgtPkg(){ const e=$('#dpkg'); return e ? e.value : ''; }
/* 프리셋마다 앱이 따로라 어느 쪽 세이브를 만질지 골라야 합니다.
   깔려 있는 것을 먼저 올리고, 없으면 아는 것 전부를 보여 줍니다. */
async function loadApps(){
  const e=$('#dpkg'); if(!e) return;
  let j={apps:[],known:[]};
  try{ j=await (await fetch('/api/adb/apps',{method:'POST',
        headers:{'Content-Type':'application/json'},body:'{}'})).json(); }catch(x){}
  const have=new Set((j.apps||[]).map(a=>a.pkg));
  const rows=(j.known||[]).map(a=>({...a, on:have.has(a.pkg)}));
  rows.sort((a,b)=>(b.on?1:0)-(a.on?1:0));
  const keep=e.value;
  const tail = p => { const i=p.lastIndexOf('.'); return i<0?p:p.slice(i+1); };
  e.innerHTML=rows.map(a=>
    `<option value="${esc(a.pkg)}">${esc(a.label)} · ${esc(tail(a.pkg))}`
    + `${a.on?'':' '+T('(안 깔림)')}</option>`).join('');
  if(keep && rows.some(a=>a.pkg===keep)) e.value=keep;
}

const TABS=['플레이어','자동차','드라이버','아이템·스킬','초대·공지','자산·모델',
            '저장 및 내보내기','기록'];
/* 세이브를 만지는 탭들. 여기엔 아래에 저장 단추를 붙입니다. */
const EDIT_TABS=['플레이어','자동차','드라이버','아이템·스킬','초대·공지'];
function drawTabs(){
  $('#tabs').innerHTML=TABS.map(t=>
    `<button class="${t===tab?'on':''}" onclick="tab='${t}';draw()">`
    + esc(T(t)) + `</button>`).join('');
}
function num(path,label,max){
  const v=get(path);
  return `<div><label class="f">${label}</label>
    <input type="number" value="${v}" ${max?'max='+max:''} min="0"
      oninput="set('${path}',Math.max(0,Math.min(${max||1e15},+this.value)))"></div>`;
}
function get(p){ return p.split('.').reduce((o,k)=>o&&o[k],S.data); }
function set(p,v){ const ks=p.split('.'); let o=S.data;
  for(let i=0;i<ks.length-1;i++)o=o[ks[i]]; o[ks[ks.length-1]]=v; }

function draw(){
  drawTabs();
  const bar=document.querySelector('.bar');
  /* 자산 탭은 3D 캔버스를 들고 있어 다시 그리면 안 됩니다. 제가 알아서 붙습니다 */
  if(tab==='자산·모델'){ bar.style.display='none'; return drawAssets(); }
  if(tab==='저장 및 내보내기'){ bar.style.display='none'; return drawOut(); }
  if(tab==='기록'){ bar.style.display='none'; return drawLog(); }
  bar.style.display='';
  A.mounted=0;
  const d=S.data, m=S.meta; let h='';
  if(tab==='플레이어'){
    h+=`<div class="card"><h2>${T('기본')}</h2><div class="row">
      <div><label class="f">${T('별명')}</label>
        <input value="${esc(d.player.nickName)}" oninput="set('player.nickName',this.value)"></div>
      ${num('player.gold',T('골드'),m.max.gold)}
      ${num('player.trophy',T('트로피'),m.max.trophy)}
      ${num('player.tire',T('타이어 (최대 {max})',{max:m.max.tire}),m.max.tire)}
      <div><label class="f">${T('타고 있는 차')}</label><select onchange="set('player.car',this.value)">
        ${m.cars.map(c=>`<option ${c.name===d.player.car?'selected':''}>${c.name}</option>`).join('')}
      </select></div>
      <div><label class="f">${T('드라이버')}</label><select onchange="set('player.driver',+this.value)">
        ${m.drivers.map(x=>`<option value="${x.no}" ${x.no===d.player.driver?'selected':''}>${esc(x.name)}</option>`).join('')}
      </select></div>
    </div></div>`;
    h+=`<div class="card"><h2>${T('기록|주행')}</h2><div class="row">
      ${Object.keys(d.records||{}).map(k=>num('records.'+k,k)).join('')}
    </div></div>`;
  }
  if(tab==='자동차'){
    h+=`<div class="card"><h2>${T('보유 차량 ({have}/{all})',{have:d.carsOwned.length,all:m.cars.length})}</h2>
      <div style="display:flex;gap:6px;margin-bottom:8px">
        <button onclick="allCars(1)">${T('전부 선택')}</button>
        <button onclick="allCars(0)">${T('전부 해제')}</button></div>
      <div class="grid">${m.cars.map(c=>`
        <label class="chk"><input type="checkbox" ${d.carsOwned.includes(c.name)?'checked':''}
          onchange="toggle('carsOwned','${c.name}',this.checked)">
          <span class="no">${c.no}</span>${c.name} <span class="no">${c.cls}</span></label>`).join('')}
      </div></div>`;
    h+=`<div class="card"><h2>${T('등급 올린 차')}</h2><table>${m.cars.map(c=>`
      <tr><td>${c.name}</td><td>
        <select onchange="setClass('${c.name}',this.value)">
          ${['','C','B','A','S','R'].map(x=>`<option ${x===(d.carClass[c.name]||'')?'selected':''}>${x||T('(기본 {cls})',{cls:c.cls})}</option>`).join('')}
        </select></td></tr>`).join('')}</table></div>`;
  }
  if(tab==='드라이버'){
    h+=`<div class="card">
      <h2>${T('드라이버 (열둘 고정)')}</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <button onclick="drvExport()">${T('고른 사람 내보내기')}</button>
        <button onclick="drvAll(1)">${T('전부 보유')}</button>
        <button onclick="drvAll(0)">${T('전부 해제')}</button>
        <span class="hint" style="margin:0">${T('초상화 · 능력 · 보이스를 함께 봅니다. 전부 가지고 있으면 드라이버 상점이 비어 버립니다.')}</span>
      </div>
      <pre id="drvlog" style="display:none"></pre>
      <div id="drvcards" class="cards"><div class="hint">${T('읽는 중입니다…')}</div></div>
    </div>`;
  }
  if(tab==='아이템·스킬'){
    h+=`<div class="card"><h2>${T('아이템')}</h2><div class="row">
      ${m.items.map(k=>num('items.'+k,k)).join('')}</div>
      <div class="hint">${T('강화공구상자만 0/1 입니다 — 클라이언트가 '
        + 'Mathf.Clamp(값,0,1) 로 자릅니다.')}</div></div>`;
    h+=`<div class="card"><h2>${T('스킬 (차마다 따로 붙습니다)')}</h2>
      <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap">
        <div style="flex:1;min-width:200px">
          <label class="f">${T('어느 차의 스킬')}</label>
          <select id="sk_car" onchange="skDraw()">
            ${m.cars.map(c=>`<option value="${c.no}">${c.no}. ${esc(c.name)}
              — ${T('{cls}급',{cls:c.cls})}</option>`).join('')}
          </select>
        </div>
        <button onclick="skAll(3)">${T('이 차 전부 3레벨')}</button>
        <button onclick="skAll(0)">${T('이 차 전부 없애기')}</button>
      </div>
      <div id="sk_body"></div>
      <div class="hint">${T('원본(Origin) 셋은 값이 0 이고 R 등급에 딸려 옵니다. 추가(Addtion) 열은 골드 10,000 또는 트로피 50 입니다. 올리는 값은 15,000 → 20,000 골드입니다.')}</div>
      </div>`;
  }
  if(tab==='초대·공지'){
    h+=`<div class="card"><h2>${T('초대')}</h2><div class="row">
      ${num('invite.count',T('초대 횟수'))}</div>
      <div class="hint">${T('30회에 미아우, 50회에 허미가 열립니다.')}</div></div>`;
    h+=`<div class="card"><h2>${T('휴면 복귀')}</h2><div class="row">
      ${num('dormancy.days',T('휴면 일수'))}</div></div>`;
    h+=`<div class="card"><h2>${T('공지사항')}</h2>
      <label class="f">${T('제목')}</label>
      <input value="${esc((d.notice||{}).title||'')}" oninput="set('notice.title',this.value)">
      <label class="f" style="margin-top:8px">${T('내용')}</label>
      <input value="${esc((d.notice||{}).body||'')}" oninput="set('notice.body',this.value)">
      </div>`;
  }
  if(EDIT_TABS.includes(tab)){
    h+=`<div class="card" style="display:flex;gap:10px;align-items:center;
          flex-wrap:wrap">
      <button class="primary" onclick="save()">${T('이 내용으로 저장')}</button>
      <button onclick="load()">${T('되돌리기')}</button>
      <span class="hint" style="margin:0">${T('저장해 둔 것으로')}
        ${T('<b>저장 및 내보내기</b> 탭에서 APK 를 굽습니다.')}</span>
      <span class="hint" id="savenote" style="margin:0 0 0 auto"></span>
    </div>`;
  }
  $('#body').innerHTML=h;
  if(tab==='드라이버') drvLoad();
  if(tab==='아이템·스킬') skDraw();
}
/* ------------------------------------------------------------ 스킬 */
/* 스킬은 **차마다** 붙습니다(R 클래스 스킬). 세이브에는
   [{car, no, lv, eq}] 로 담고, 게임에는 /skill/get/list 로 나갑니다. */
function skRows(){ if(!S.data.skills) S.data.skills=[]; return S.data.skills; }
function skCar(){ const e=$('#sk_car'); return e ? +e.value : 1; }
function skFind(no){ return skRows().find(r=>r.car===skCar() && r.no===no); }
function skSet(no, lv, eq){
  const a=skRows(), i=a.findIndex(r=>r.car===skCar() && r.no===no);
  if(lv<=0){ if(i>=0) a.splice(i,1); }
  else if(i>=0){ a[i].lv=lv; if(eq!==undefined) a[i].eq=eq; }
  else a.push({car:skCar(), no, lv, eq:!!eq});
  skDraw();
}
function skAll(lv){
  const t=(S.meta.skills||[]);
  t.forEach(s=>skSetQuiet(s.no, lv));
  skDraw();
  say(lv? T('이 차의 스킬을 전부 {lv}레벨로 두었습니다. 저장을 눌러야 남습니다.',{lv:lv})
        : T('이 차의 스킬을 비웠습니다. 저장을 눌러야 남습니다.'));
}
function skSetQuiet(no, lv){
  const a=skRows(), i=a.findIndex(r=>r.car===skCar() && r.no===no);
  if(lv<=0){ if(i>=0) a.splice(i,1); return; }
  if(i>=0) a[i].lv=lv; else a.push({car:skCar(), no, lv, eq:false});
}
function skDraw(){
  const e=$('#sk_body'); if(!e||!S) return;
  const t=S.meta.skills||[];
  if(!t.length){ e.innerHTML=T('<div class="hint">스킬 표를 못 읽었습니다.</div>');
                 return; }
  e.innerHTML='<table style="margin-top:8px"><tr>'
    +T('<td>스킬</td><td>슬롯</td><td>값</td><td>레벨</td><td>장착</td></tr>')
    + t.map(s=>{
      const r=skFind(s.no), lv=r?r.lv:0;
      const opts=[0,1,2,3].filter(v=>v<=s.max).map(v=>
        `<option value="${v}" ${v===lv?'selected':''}>${v?T('{lv}레벨',{lv:v}):T('없음')}`
        +`</option>`).join('');
      return `<tr>
        <td style="color:var(--ink)">${esc(s.name)}
          <span class="no" style="color:var(--dim)">${esc(s.code)}</span></td>
        <td>${s.slot==='Origin'?T('원본'):T('추가')}</td>
        <td>${s.cost? (s.costType==='Trophy'?'🏆':'🪙')+s.cost : T('무료')}</td>
        <td><select onchange="skSet(${s.no}, +this.value)"
              style="width:92px">${opts}</select></td>
        <td><input type="checkbox" ${r&&r.eq?'checked':''} ${r?'':'disabled'}
              onchange="skSet(${s.no}, ${lv}, this.checked)"></td>
      </tr>`;
    }).join('')+'</table>';
}

/* ---------------------------------------------------- 드라이버 프로필 */
/* 슬롯은 열둘로 고정입니다. 카드 배열이 프리팹에 박혀 있어 열셋째를 만들려면
   UI 프리팹을 수술해야 합니다. 그래서 있는 열둘을 제대로 보여 줍니다. */
async function drvLoad(){
  const e=$('#drvcards'); if(!e) return;
  const j=await post('/api/driver/list',{});
  if(!j.ok){ e.innerHTML='<div class="hint">'+esc(j.msg||T('못 읽었습니다'))+'</div>';
             return; }
  D_ROWS=j.rows||[];
  drvDraw();
}
let D_ROWS=[];
function drvDraw(){
  const e=$('#drvcards'); if(!e||!S) return;
  const own=S.data.driversOwned||[];
  e.innerHTML=D_ROWS.map(r=>`
    <div class="dcard ${own.includes(r.no)?'have':''}">
      ${r.png?`<img src="/file?p=${encodeURIComponent(r.png)}" alt="">`
             :'<img alt="">'}
      <div class="b">
        <div class="nm">${esc(r.name)}<span class="no">${T('{no}번',{no:r.no})}${
          r.base?' · '+T('기본|드라이버'):''}</span></div>
        <div class="ex">${esc(r.exp)||'—'}</div>
        <div class="ft">
          <label class="chk" style="margin:0"><input type="checkbox"
            ${own.includes(r.no)?'checked':''}
            onchange="toggle('driversOwned',${r.no},this.checked);drvDraw()">
            ${T('보유')}</label>
          <span>${T('보이스')} ${r.voices?T('{n}개 ({folder})',{n:r.voices,folder:esc(r.voice)}):T('없음')}</span>
          <span style="margin-left:auto"></span>
          <button onclick="drvEdit(${r.no})">${T('고치기')}</button>
          <button onclick="drvExport(${r.no})">${T('내보내기')}</button>
        </div>
      </div>
    </div>`).join('');
}
function drvAll(on){
  S.data.driversOwned = on ? D_ROWS.map(r=>r.no) : [1];
  drvDraw();
  say(on?T('전부 보유로 두었습니다. 저장을 눌러야 남습니다.')
        :T('기본 드라이버만 남겼습니다. 저장을 눌러야 남습니다.'));
}
async function drvEdit(no){
  const r=D_ROWS.find(x=>x.no===no); if(!r) return;
  const nm=prompt(T('{no}번 이름',{no:no}), r.name); if(nm===null) return;
  const ex=prompt(T('{no}번 능력 설명',{no:no}), r.exp); if(ex===null) return;
  const j=await post('/api/driver/text',{no,name:nm,exp:ex});
  say(j.msg||'', j.ok===false);
  if(j.ok) drvLoad();
}
function drvExport(one){
  const nos = one ? [one] : D_ROWS.map(r=>r.no);
  const lg=$('#drvlog'); lg.style.display=''; lg.textContent=T('내보내는 중…');
  post('/api/driver/export',{nos}).then(r=>{
    if(!r.ok){ lg.textContent=r.msg||T('실패'); return; }
    watchJob(r.job, t=>{ lg.textContent=t; }, ()=>{});
  });
}

function toggle(key,val,on){
  const a=S.data[key];
  const i=a.indexOf(val);
  if(on&&i<0)a.push(val); if(!on&&i>=0)a.splice(i,1);
  draw();
}
function allCars(on){
  S.data.carsOwned = on ? S.meta.cars.map(c=>c.name) : ['AVEO'];
  draw();
}
function setClass(name,v){
  if(!v||v.startsWith('(')) delete S.data.carClass[name];
  else S.data.carClass[name]=v;
}
async function save(){
  const j=await api('/api/save',{name:cur,data:S.data});
  const e=$('#savenote');
  if(e) e.textContent = (j.changed && j.changed.length)
    ? T('바뀐 칸: {list}',{list:j.changed.join(' · ')}) : T('바뀐 것이 없습니다');
}
async function post(path,body){
  const r=await fetch(path,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
  return await r.json();
}

/* ==================================================== 저장 및 내보내기 탭 */
/* 세이브 · 기기 연결 · 프로젝트 · APK 굽기 · 바뀐 내역을 한자리에 모읍니다.
   왼쪽 기둥에 흩어져 있을 때는 무엇을 굽는 것인지 잘 안 보였습니다. *//* 이 탭이 쥐고 있는 것들. 창 런처와 같은 일감(chabuild · chasaves)을
   부르므로 두 얼굴의 기능이 어긋나지 않습니다. */
var O={presets:[],ways:[],limit:22,now:"",conf:{},
         dev:[],devSel:null,devLoaded:false,devMsg:'',
         brief:{},detail:null,showPresets:false,fold:{},foldKeys:{}};

function drawOut(){
  $('#body').innerHTML=`
  <div id="o_stale"></div>

  <div class="card">
    <h2>${T('1. 세이브 — 어떤 상태로 시작할지 정합니다')}</h2>
    <div class="two">
      <div>
        <div id="slots"></div>
        <div class="btns">
          <button class="primary" onclick="togglePresets()">${T('＋ 새로 만들기')}</button>
          <button onclick="copySlot()">${T('복제')}</button>
          <button onclick="renameSlot()">${T('이름')}</button>
          <button class="danger" onclick="delSlot()">${T('삭제')}</button>
        </div>
        <div class="btns">
          <button onclick="slotExport()">${T('파일로 내보내기…')}</button>
          <button onclick="slotImport()">${T('파일에서 불러오기…')}</button>
        </div>
        <div id="o_presets"></div>
      </div>
      <div id="o_detail"><div class="hint">${T('읽는 중입니다…')}</div></div>
    </div>
  </div>

  <div class="card">
    <h2>${T('2. 폰 — 세이브를 주고받습니다')}</h2>
    <div class="two">
      <div>
        <div class="btns" style="margin-top:0">
          <button class="primary" onclick="scanDev()">${T('폰에서 세이브 찾기')}</button>
          <span class="hint" id="o_devmsg" style="margin:0;align-self:center"></span>
        </div>
        <div id="o_dev"><div class="hint">${T('아직 찾아보지 않았습니다.')}</div></div>
      </div>
      <div>
        <label class="f">${T('고른 세이브를 폰의 어느 자리에')}</label>
        <select id="o_spot"></select>
        <div class="btns">
          <button class="primary" onclick="devPush()">${T('폰에 넣기 →')}</button>
          <button onclick="devPull()">${T('← PC 로 가져오기')}</button>
          <button class="danger" onclick="devRm()">${T('폰에서 지우기')}</button>
        </div>
        <div class="hint">${T('앱이 켜져 있으면 상태를 메모리에 들고 있어 파일만 갈아 끼워서는 화면이 안 바뀝니다. 넣은 뒤 앱을 껐다 켜세요.')}</div>

        <div id="o_devdetail"></div>
      </div>
    </div>
  </div>

  <div class="side">
  <div class="card">
    <h2>${T('3. APK 굽기')}</h2>
    <div class="row">
      <div>
        <label class="f">${T('어떤 APK')}</label>
        <select id="b_mode" onchange="modeChanged()">
          <option value="local">${T('로컬 전용 — 서버 없이 폰 안에서 돕니다')}</option>
          <option value="server">${T('서버 전용 — PC 의 chacnserver.py 에 붙습니다')}</option>
        </select>
      </div>
      <div>
        <label class="f">${T('구워 넣을 세이브')}</label>
        <div class="hint" id="b_slot" style="margin:0"></div>
      </div>
    </div>
    <div id="b_server"></div>
    <div class="btns">
      <label class="chk"><input type="checkbox" id="b_inst"> ${T('기기에 설치까지')}</label>
      <button class="primary" onclick="doBuild()">${T('APK 굽기')}</button>
      <span class="hint" id="b_block" style="margin:0;align-self:center"></span>
    </div>
    <div class="hint" id="b_pkg"></div>
    <pre id="b_log">${T('준비됐습니다.')}</pre>
  </div>

  <div class="card">
    <h2>${T('프로젝트')}</h2>
    <div id="projs"><div class="hint">${T('아직 없습니다.')}</div></div>
    <div class="btns">
      <button class="primary" onclick="projSave()">${T('지금 상태로 저장')}</button>
    </div>
    <div class="hint">${T('세이브 한 벌과 <b>여기까지 고친 내역</b>을 묶어 '
      + '둡니다. 작업 트리 자체는 담지 않습니다 — 되돌릴 수 없는 것이라 무엇을 '
      + '했는지만 남깁니다.')}</div>
  </div>
  </div>
  `;
  loadBrief(); loadDetail(); loadPresets(); loadWays(); loadStale();
  drawDev(); drawSpots(); loadProjs();
}

/* ---- 세이브 요약 · 상세 ---------------------------------------------- */
async function loadBrief(){
  const j=await post('/api/slot/brief',{});
  if(j.ok){ O.brief=j.brief||{}; drawSlots(); }
}
async function loadDetail(){
  if(!cur){ O.detail=null; return drawDetail(); }
  O.detail=await post('/api/slot/detail',{name:cur});
  drawDetail();
}
/* 접었다 폈다 하는 자리. 섹션마다 <table> 이 따로라 열 너비가 제각각이면
   값이 들쭉날쭉해 보입니다. CSS 의 table-layout:fixed 로 첫 칸을 못박아
   **모든 섹션의 값이 같은 세로선에 섭니다.** */
/* 접었다 폈다 하는 자리.

   자리는 **좁게** 잡습니다 — 처음엔 첫 칸만 펴 두고 나머지는 접습니다.
   접힘 상태의 열쇠는 **한국어 원문**입니다. 옮긴 제목을 열쇠로 쓰면
   언어를 바꿀 때 접어 둔 자리가 흐트러집니다. */
function fold(key, title, inner, dflt){
  const on = (O.fold[key] === undefined) ? !!dflt : O.fold[key];
  return `<details class="sec" ${on?'open':''}
     ontoggle="O.fold['${esc(key)}']=this.open">
     <summary>${esc(title)}</summary>${inner}</details>`;
}
function foldAll(pre, on){
  (O.foldKeys[pre]||[]).forEach(k=>{ O.fold[k]=on; });
  if(pre==='dev:') { if(O.devSel!==null) pickDev(O.devSel); }
  else drawDetail();
}
function foldBar(pre){
  return `<div class="btns" style="margin:6px 0 0">
    <button onclick="foldAll('${pre}',true)">${T('모두 펴기')}</button>
    <button onclick="foldAll('${pre}',false)">${T('모두 접기')}</button></div>`;
}
function secTable(sections, pre){
  pre = pre || '';
  O.foldKeys[pre] = (sections||[]).map(s=>pre+(s.key||s.title))
                                  .concat([pre+'보유 차량']);
  return (sections||[]).map((s,i)=>fold(pre+(s.key||s.title), s.title,
    `<table class="kv">`
    + s.rows.map(r=>`<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td></tr>`).join('')
    + `</table>`, i===0)).join('');
}
function carTable(cars, pre){
  if(!cars||!cars.length) return '';
  return fold((pre||'')+'보유 차량', T('보유 차량'), `<table class="kv">` + cars.map(c=>
    `<tr><td>${T('{cls}급',{cls:esc(c.cls)})}</td><td>${esc(c.names.join(' · '))}</td></tr>`
    ).join('') + `</table>`, false);
}
function drawDetail(){
  const e=$('#o_detail'); if(!e) return;
  const d=O.detail;
  if(!d||!d.ok){ e.innerHTML=T('<div class="hint">왼쪽에서 세이브를 고르세요.</div>'); return; }
  e.innerHTML=`<div class="dh"><b>${esc(d.name)}</b>`
    + (d.active?` <span class="tag">${T('빌드에 씀')}</span>`:'') + `</div>`
    + `<div class="hint">${esc(d.path)} · ${esc(d.when)} · `
    + (d.size/1024).toFixed(1) + ` KB</div>`
    + foldBar('') + secTable(d.sections) + carTable(d.cars);
}

/* ---- 프리셋 ---------------------------------------------------------- */
async function loadPresets(){
  const j=await post('/api/slot/presets',{});
  if(j.ok) O.presets=j.presets||[];
  drawPresets();
  const b=$('#b_pkg');
  if(b) b.textContent=T('앱 이름 {app} · 패키지 {pkg} — 판을 가르는 것은 '
    + '세이브지 APK 가 아닙니다.', {app:S.meta.app||'', pkg:S.meta.pkg||''});
}
function togglePresets(){ O.showPresets=!O.showPresets; drawPresets(); }
function drawPresets(){
  const e=$('#o_presets'); if(!e) return;
  if(!O.showPresets){ e.innerHTML=''; return; }
  e.innerHTML=`<div class="hint">${T('밑그림을 고르세요. 만든 뒤에 얼마든지 고칠 수 있습니다.')}</div>` + O.presets.map(p=>
    `<div class="pcard" onclick="newFromPreset('${esc(p.key)}')">
       <div class="nm">${esc(p.label)} · ${esc(p.tag)}</div>
       <div class="ex">${esc(p.desc)}</div>
       <div class="ft">${p.facts.map(f=>`<span class="tag">${esc(f)}</span>`).join('')}</div>
       <div class="ex">${esc(p.note)}</div>
     </div>`).join('');
}
function newFromPreset(k){
  const p=O.presets.find(x=>x.key===k);
  const n=prompt(T('새 세이브 이름'), p?p.label:k);
  if(n===null) return;
  O.showPresets=false;
  api('/api/slot/preset',{preset:k,name:n});
}
function slotExport(){ api('/api/slot/export',{name:cur}); }
function slotImport(){ api('/api/slot/import',{}); }

/* ---- 폰 -------------------------------------------------------------- */
async function scanDev(){
  const m=$('#o_devmsg'); if(m) m.textContent=T('찾아보는 중입니다…');
  const j=await post('/api/dev/list',{});
  O.dev=j.saves||[]; O.devLoaded=true; O.devMsg=j.msg||''; O.devSel=null;
  drawDev(); drawSpots();
}
function drawDev(){
  const e=$('#o_dev'); if(!e) return;
  const m=$('#o_devmsg'); if(m) m.textContent=O.devLoaded?(O.devMsg||''):'';
  if(!O.devLoaded){ e.innerHTML=T('<div class="hint">아직 찾아보지 않았습니다.</div>'); return; }
  if(!O.dev.length){ e.innerHTML=T('<div class="hint">폰에 세이브가 없습니다.</div>'); return; }
  e.innerHTML=O.dev.map((d,i)=>
    `<div class="slot ${O.devSel===i?'sel':''}" onclick="pickDev(${i})">
       <span class="dot"></span>
       <span class="nm">${esc(d.file)}
         <div class="hint" style="margin:0">${esc(d.kind)} · ${esc(d.app)}</div>
       </span></div>`).join('');
}
function drawSpots(){
  const e=$('#o_spot'); if(!e) return;
  const mine=O.dev.filter(d=>d.current && d.file!=='chasave.json');
  const rows=[{v:'',t:T('chasave.json — 앱이 실제로 읽는 자리')}]
    .concat(mine.map(d=>({v:d.remote,t:d.file+T(' — 게임 안 겹판의 칸')})));
  e.innerHTML=rows.map(r=>`<option value="${esc(r.v)}">${esc(r.t)}</option>`).join('');
}
async function pickDev(i){
  O.devSel=i; drawDev();
  const e=$('#o_devdetail');
  if(e) e.innerHTML=T('<div class="hint">받아 오는 중입니다…</div>');
  const j=await post('/api/dev/peek',{remote:O.dev[i].remote});
  if(!e) return;
  if(!j.ok){ e.innerHTML='<div class="hint">'+esc(j.msg||T('읽지 못했습니다'))+'</div>'; return; }
  e.innerHTML=`<div class="dh"><b>${esc(O.dev[i].file)}</b></div>`
    + `<div class="hint">${esc(O.dev[i].remote)}</div>`
    + foldBar('dev:') + secTable(j.sections,'dev:') + carTable(j.cars,'dev:');
}
async function devPush(){
  const spot=$('#o_spot');
  const j=await api('/api/dev/push',{name:cur,remote:(spot&&spot.value)||''});
  if(j.ok) scanDev();
}
async function devPull(){
  if(O.devSel===null) return say(T('폰 쪽에서 하나 고르세요'), true);
  const d=O.dev[O.devSel];
  const n=prompt(T('가져온 세이브를 어떤 이름으로 저장할까요?'),
                 d.file.replace(/[.]json$/,''));
  if(n===null) return;
  await api('/api/dev/pull',{remote:d.remote,name:n});
}
async function devRm(){
  if(O.devSel===null) return say(T('폰 쪽에서 하나 고르세요'), true);
  const d=O.dev[O.devSel];
  if(!confirm(T('폰의 {path} 를 지울까요? PC 쪽은 그대로입니다.',{path:d.remote}))) return;
  const j=await api('/api/dev/rm',{remote:d.remote});
  if(j.ok) scanDev();
}

/* ---- 다시 구워야 하나 ------------------------------------------------ */
async function loadStale(){
  const e=$('#o_stale'); if(!e) return;
  const j=await post('/api/build/stale',{});
  if(!j.ok) return;
  if(!j.rows.length){
    e.innerHTML=`<div class="note ok">${T('APK 가 최신입니다 ({when}). 세이브만 바꿀 거라면 다시 구울 것 없이 '
      + '폰에 넣으면 됩니다.',{when:esc(j.when)})}</div>`;
    return;
  }
  e.innerHTML=`<div class="note warn">
    <b>${T('APK 를 다시 구워야 합니다.')}</b> ${T('자산이나 코드가 바뀌었습니다 — 이런 것은 세이브로 옮길 수 없어 APK 안에 들어가야 합니다.')}
    <ul>${j.rows.map(r=>`<li>${esc(r.what)} <span class="hint">${esc(r.rel)}</span></li>`).join('')}</ul>
    <button onclick="freshSave()">${T('새 요소를 반영한 세이브 만들기')}</button>
    </div>`;
}
async function freshSave(){ await api('/api/build/fresh',{}); }

/* ---- 서버에 붙는 방법 ------------------------------------------------ */
async function loadWays(){
  const j=await post('/api/build/ways',{});
  if(j.ok){ O.ways=j.ways||[]; O.limit=j.limit; O.now=j.now; O.conf=j.conf||{}; }
  const m=$('#b_mode'); if(m) m.value=O.conf.mode||'local';
  drawServer();
}
function confSet(k,v){ O.conf[k]=v; post('/api/build/conf',O.conf); }
function modeChanged(){ confSet('mode',$('#b_mode').value); drawServer(); }
function pickWay(k){
  O.conf.way=k;
  const w=O.ways.find(x=>x.key===k);
  if(w && w.fixed) O.conf.host=w.host;
  post('/api/build/conf',O.conf); drawServer();
}
function hostPort(){
  const w=O.ways.find(x=>x.key===(O.conf.way||'usb'))||O.ways[0]||{};
  const h=(w.fixed?w.host:(O.conf.host||''))||'';
  return (h.trim()||'127.0.0.1') + ':' + ((O.conf.port||'8888')+'').trim();
}
function drawServer(){
  const e=$('#b_server'); if(!e) return;
  const slot=$('#b_slot');
  if(slot) slot.textContent=(cur||'—') + ' — ' + (O.brief[cur]||'');
  const md=($('#b_mode')||{}).value;
  if(md!=='server'){ e.innerHTML=''; return blockNote(); }
  const w=O.ways.find(x=>x.key===(O.conf.way||'usb'))||O.ways[0]||{steps:[]};
  const hp=hostPort(), over=hp.length-O.limit;
  e.innerHTML=`<div class="wgrid">` + O.ways.map(x=>
    `<div class="wcard ${x.key===w.key?'on':''}" onclick="pickWay('${esc(x.key)}')">
       <div class="nm"><span class="tag">${x.no}</span> ${esc(x.label)}</div>
       <div class="ex">${esc(x.desc)}</div></div>`).join('') + `</div>
    <div class="hint">${T('이 방법으로 하려면')}</div>
    <ul class="steps">${(w.steps||[]).map(s=>`<li>${esc(s)}</li>`).join('')}</ul>
    <div class="row">
      <div>
        <label class="f">${T('주소 (IP 나 도메인)')}</label>
        <input id="b_host" value="${esc(O.conf.host||'')}" ${w.fixed?'disabled':''}
               oninput="confSet('host',this.value);drawServer()">
      </div>
      <div>
        <label class="f">${T('포트')}</label>
        <input id="b_port" value="${esc(O.conf.port||'8888')}"
               oninput="confSet('port',this.value);drawServer()">
      </div>
    </div>
    <div class="${over>0?'note warn':'hint'}">${over>0
      ? T('주소가 {len}자인데 자리는 {cap}자까지입니다. 더 짧은 IP 나 '
          + '이름을 쓰세요.', {len:hp.length, cap:O.limit})
      : T('폰에 박힐 주소: http://{host}/ — 자리 {cap}자 중 {len}자를 씁니다 '
          + '(지금은 {now}).',
          {host:esc(hp), cap:O.limit, len:hp.length, now:esc(O.now||'?')})}</div>
    <label class="f" style="margin-top:8px">${T('서버의 세이브')}</label>
    <div class="chk"><input type="radio" name="ss" value="use"
      ${(O.conf.server_save||'use')==='use'?'checked':''}
      onchange="confSet('server_save','use')">
      <span>${T('고른 세이브를 서버의 시작 상태로 쓴다')}</span></div>
    <div class="chk"><input type="radio" name="ss" value="keep"
      ${O.conf.server_save==='keep'?'checked':''}
      onchange="confSet('server_save','keep')">
      <span>${T('서버가 지금 가진 상태를 그대로 둔다')}</span></div>
    <label class="chk"><input type="checkbox" ${O.conf.bundle?'checked':''}
      onchange="confSet('bundle',this.checked)">
      <span>${T('번들 주소도 함께 맞추기 (DLL 사슬을 다시 굽습니다 · 몇 분)')}</span></label>
    <div class="hint">${T('맵 자산은 서버가 /bundle/ 로 내줍니다. 주소를 127.0.0.1 밖으로 옮겼다면 번들 주소도 같이 옮겨야 맵이 나옵니다.')}</div>`;
  blockNote();
}
function blockNote(){
  const e=$('#b_block'); if(!e) return;
  const mode=($('#b_mode')||{}).value||'local';
  let msg='';
  if(mode==='server'){
    const w=O.ways.find(x=>x.key===(O.conf.way||'usb'))||{};
    if(!w.fixed && !((O.conf.host||'').trim())) msg=T('서버 주소를 적으세요.');
    else if(hostPort().length>O.limit) msg=T('주소가 자리보다 깁니다.');
  }
  e.textContent=msg;
  e.style.color=msg?'var(--bad)':'var(--dim)';
}
function doBuild(){
  const mode=$('#b_mode').value, inst=$('#b_inst').checked;
  $('#b_log').textContent=T('굽는 중입니다…');
  post('/api/build',Object.assign({mode,install:inst,slot:cur},{
    way:O.conf.way||'usb', host:O.conf.host||'', port:O.conf.port||'8888',
    server_save:O.conf.server_save||'use', bundle:!!O.conf.bundle})).then(r=>{
    if(!r.ok){ $('#b_log').textContent=r.msg||T('실패했습니다'); return; }
    watchJob(r.job, t=>{ $('#b_log').textContent=t; },
             ()=>{ loadStale(); });
  });
}
function watchJob(jid, onText, onDone){
  let n=0;
  const t=setInterval(async()=>{
    const j=await post('/api/job',{id:jid});
    if(!j.ok) return;
    onText(j.log.filter(l=>!l.startsWith('@@')).join(String.fromCharCode(10)));
    if(j.done){ clearInterval(t); if(onDone) onDone(j.result); }
    if(++n>3000) clearInterval(t);
  },700);
}
async function loadProjs(){
  const e=$('#projs'); if(!e) return;
  const j=await post('/api/proj/list',{});
  const rows=j.items||[];
  e.innerHTML = rows.length ? rows.map(p=>`
    <div class="slot"><span class="dot"></span>
      <span class="nm">${esc(p.name)}
        <span class="no" style="color:var(--dim)">${esc(p.saved)} ${T('· 내역 {a} · 새 차 {b}',{a:p.changes,b:p.cars})}</span></span>
      <button onclick="projLoad('${esc(p.name)}')">${T('불러오기')}</button>
      <button onclick="projRename('${esc(p.name)}')">${T('이름')}</button>
      <button class="danger" onclick="projDel('${esc(p.name)}')">${T('삭제')}</button>
    </div>`).join('') : T('<div class="hint">아직 없습니다.</div>');
}
function projSave(){
  const n=prompt(T('프로젝트 이름을 적으세요'), cur||T('내 판'));
  if(!n) return;
  post('/api/proj/save',{name:n})
    .then(r=>{ say(r.msg||'', r.ok===false); loadProjs(); });
}
function projLoad(n){
  if(!confirm(n+T(' 을(를) 불러올까요? 세이브로 들어갑니다.'))) return;
  post('/api/proj/load',{name:n}).then(async r=>{
    say(r.msg||'', r.ok===false); await load(); });
}
function projDel(n){
  if(!confirm(n+T(' 을(를) 지울까요?'))) return;
  post('/api/proj/delete',{name:n}).then(r=>{ say(r.msg||''); loadProjs(); });
}
function projRename(n){
  const t=prompt(T('새 이름'), n); if(!t||t===n) return;
  post('/api/proj/rename',{name:n,to:t}).then(r=>{
    say(r.msg||'', r.ok===false); loadProjs(); });
}
/* ============================================================== 기록 탭 */
function drawLog(){
  $('#body').innerHTML=`
  <div class="card">
    <h2>${T('기록')}</h2>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <select id="l_kind" onchange="loadLog()" style="width:150px">
        <option value="">${T('전부')}</option>
        <option value="save">${T('세이브')}</option>
        <option value="asset">${T('자산')}</option>
        <option value="build">APK</option>
        <option value="device">${T('기기')}</option>
        <option value="project">${T('프로젝트')}</option>
        <option value="system">${T('그 밖')}</option>
      </select>
      <input id="l_find" placeholder="${T('글자로 거르기')}" oninput="loadLog()"
             style="flex:1;min-width:160px">
      <button onclick="loadLog()">${T('새로 읽기')}</button>
      <button onclick="logExport()">${T('파일로 내보내기')}</button>
      <button class="danger" onclick="logClear()">${T('비우기')}</button>
    </div>
    <div id="logbody" style="margin-top:10px"><div class="hint">${T('읽는 중…')}</div></div>
  </div>`;
  loadLog();
}
async function loadLog(){
  const e=$('#logbody'); if(!e) return;
  const j=await post('/api/log',{limit:800, kind:$('#l_kind').value,
                                 find:$('#l_find').value});
  const rows=(j.rows||[]).slice().reverse();
  e.innerHTML = rows.length ? '<table>'+rows.map(r=>
    `<tr><td style="white-space:nowrap">${esc(r.t)}</td>
      <td style="white-space:nowrap">${esc(r.kind)}</td>
      <td>${esc(r.text)}${r.detail?' <span class="no" style="color:var(--dim)">'
        +esc(JSON.stringify(r.detail))+'</span>':''}</td></tr>`).join('')+'</table>'
    : T('<div class="hint">아무것도 없습니다.</div>');
}
function logExport(){ post('/api/log/export',{}).then(r=>say(r.msg||'')); }
function logClear(){
  if(!confirm(T('기록을 통째로 비울까요?'))) return;
  post('/api/log/clear',{}).then(r=>{ say(r.msg||''); loadLog(); });
}
(async()=>{ await loadUI(); await load(); })();
</script>
</body>
</html>
"""

from chatool_page_assets import ASSETS

# 자산 탭은 따로 쓰고 여기서 한 장으로 합칩니다.
PAGE = PAGE.replace('</body>', ASSETS + '</body>')
