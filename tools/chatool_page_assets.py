# -*- coding: utf-8 -*-
"""런처 화면의 '자산·모델' 탭. 순수 HTML/CSS/JS 라 따로 깔 것이 없다.

3D 미리보기는 WebGL 로 그린다. 라이브러리를 쓰지 않으므로 브라우저만
있으면 되고, 창 런처에서도 똑같이 돈다.

여기 있는 **감기 검사**가 핵심이다. 이 게임의 차는 스키닝 메시라
차고(쉬는 자세)에서는 뒤집힌 면이 드러나지 않는다. 기기에 넣어 보기 전에
여기서 빨갛게 보이면 그건 주행 화면에서 새까맣게 나온다.
"""

ASSETS = r"""
<style>
  .acols{display:grid;grid-template-columns:1fr 340px;gap:14px;align-items:start}
  @media (max-width:1100px){.acols{grid-template-columns:1fr}}
  #a_cv{width:100%;height:380px;display:block;border-radius:8px;
        background:var(--code);border:1px solid var(--line);cursor:grab}
  #a_cv:active{cursor:grabbing}
  .vbar{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;align-items:center}
  .vbar .seg{display:flex;border:1px solid var(--line);border-radius:7px;
             overflow:hidden}
  .vbar .seg button{border:0;border-radius:0;padding:5px 11px;font-size:13px}
  .vbar .seg button.on{background:var(--accent2);color:var(--onaccent2);
                     font-weight:700}
  /* 뽑기 전후로 오른쪽 칸의 키가 달라지면 아래 카드가 통째로 밀린다.
     그래서 자리를 **미리 잡아 두고** 그 안에서만 바뀌게 한다. */
  .aside{display:flex;flex-direction:column;gap:14px}
  #a_stats{min-height:150px}
  #a_verdict{min-height:58px}
  .shot{height:206px;border-radius:7px;border:1px solid var(--line);
        background:var(--code);display:flex;align-items:center;
        justify-content:center;overflow:hidden;cursor:zoom-in}
  .shot img{max-width:100%;max-height:100%;object-fit:contain;display:block}
  .shot .none{color:var(--dim);font-size:12.5px;cursor:default}
  .thumb{width:100%;max-height:210px;object-fit:contain;border-radius:7px;
         border:1px solid var(--line);background:var(--code);display:block}
  /* 크게 보기 */
  .zoom{position:fixed;inset:0;background:rgba(6,8,12,.92);z-index:90;
        display:flex;align-items:center;justify-content:center;padding:24px;
        cursor:zoom-out}
  /* 차 텍스처는 256×256 짜리도 있다. 원래 크기로 띄우면 너무 작아
     칠할 자리가 안 보이므로 화면에 꽉 차게 키운다(픽셀은 또렷하게). */
  .zoom img{height:min(86vh,86vw);width:auto;max-width:96vw;
            object-fit:contain;image-rendering:pixelated;
            border-radius:8px;border:1px solid var(--line)}
  .zoom .cap{position:absolute;left:0;right:0;bottom:14px;text-align:center;
             color:var(--dim);font-size:12.5px}
  .fmts{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
        gap:6px 14px;margin:8px 0 2px}
  .fmts label{display:flex;gap:8px;align-items:flex-start;font-size:12.5px;
              color:var(--dim);line-height:1.45}
  .fmts input{margin:2px 0 0}
  .picklist{max-height:190px;overflow:auto;border:1px solid var(--line);
            border-radius:8px;padding:8px 10px;background:var(--code);
            display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
            gap:2px 10px}
  .picklist label{font-size:12.5px;color:var(--dim);display:flex;gap:6px}
  .stat{display:flex;justify-content:space-between;font-size:12px;
        color:var(--dim);padding:2px 0;border-bottom:1px solid var(--sep)}
  .stat b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
  .drop{border:1px dashed var(--dash);border-radius:8px;padding:14px;
      text-align:center;
        color:var(--dim);font-size:13px;cursor:pointer}
  .drop.hot{border-color:var(--accent);color:var(--accent)}
  #a_log{background:var(--code);border:1px solid var(--line);border-radius:8px;
         padding:10px 12px;font:12px/1.5 Consolas,monospace;color:var(--codefg);
         max-height:190px;overflow:auto;white-space:pre-wrap;margin:0}
  .warnbox{border-left:3px solid var(--bad);background:var(--warnbg);
         color:var(--warnfg);padding:8px 11px;
           border-radius:0 7px 7px 0;font-size:12.5px;margin-top:8px}
  .okbox{border-left:3px solid var(--ok);background:var(--okbg);
       color:var(--okfg);padding:8px 11px;
         border-radius:0 7px 7px 0;font-size:12.5px;margin-top:8px}
</style>

<script>
/* ======================================================== 자산·모델 탭 */
let A = { mounted:0, cars:null, car:null, mesh:null, tex:null,
          mode:'normal', job:null, tick:null,
          shots:null, shotKind:'tex', picked:[], formats:null, xdir:'',
          rig:null, anim:null, frame:0, playing:0, animTick:null };

function drawAssets(){
  /* 다른 탭에 들렀다 오면 #body 가 통째로 갈리므로 캔버스로 확인합니다 */
  if(A.mounted && document.querySelector('#a_cv')) return;
  A.mounted = 1;
  document.querySelector('#body').innerHTML = assetsHtml();
  aInit();
  if(A.car) aLoadMesh(A.car);
}
function assetsHtml(){ return `
  <div class="card">
    <h2>${T('차와 자산 고르기')}</h2>
    <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap">
      <div style="flex:1;min-width:150px">
        <label class="f">${T('갈래')}</label>
        <select id="a_cat" onchange="aCatPick()"></select>
      </div>
      <div style="flex:1.3;min-width:170px">
        <label class="f">${T('대상')}</label>
        <select id="a_car" onchange="aCar()"></select>
      </div>
      <div style="flex:1;min-width:150px">
        <label class="f">${T('모델 (등급·LOD)')}</label>
        <select id="a_asset" onchange="aPick()"></select>
      </div>
      <button class="primary" onclick="aExtract()">${T('뽑기')}</button>
      <button onclick="aReindex()">${T('색인 다시')}</button>
    </div>
    <div class="hint" id="a_note">${T('색인이 없으면 처음 한 번 몇 분 걸립니다.')}</div>
  </div>

  <div class="acols">
    <div class="card">
      <h2>${T('3D 미리보기')}</h2>
      <canvas id="a_cv"></canvas>
      <div class="vbar">
        <div class="seg">
          <button id="a_m1" class="on" onclick="aMode('normal')">${T('보통')}</button>
          <button id="a_m2" onclick="aMode('check')">${T('감기 검사')}</button>
          <button id="a_m3" onclick="aMode('wire')">${T('뼈대')}</button>
        </div>
        <label class="chk"><input type="checkbox" id="a_tex" checked
          onchange="aDraw()"> ${T('텍스처')}</label>
        <label class="chk"><input type="checkbox" id="a_spin"
          onchange="aSpin()"> ${T('돌리기')}</label>
        <span class="hint" style="margin:0 0 0 auto">
          ${T('끌면 돌아가고, 휠로 확대합니다')}</span>
      </div>
      <div class="vbar" style="margin-top:6px">
        <label class="f" style="margin:0">${T('동작')}</label>
        <select id="a_clip" onchange="aClip()" style="min-width:150px">
          <option value="">${T('— 정지 —')}</option>
        </select>
        <button id="a_play" onclick="aPlay()" disabled>${T('재생')}</button>
        <input type="range" id="a_seek" min="0" max="0" value="0"
               oninput="aSeek(+this.value)" style="flex:1;min-width:120px"
               disabled>
        <span class="hint" id="a_frame" style="min-width:96px"></span>
      </div>
      <div id="a_verdict"></div>
    </div>

    <div class="aside">
      <div class="card">
        <h2>${T('이 차')}</h2>
        <div id="a_stats"><div class="hint">${T('차를 고르고 뽑기를 누르세요.')}</div></div>
      </div>
      <div class="card">
        <div class="vbar" style="margin:0 0 8px">
          <div class="seg">
            <button id="a_s1" class="on" onclick="aShot('tex')">${T('텍스처')}</button>
            <button id="a_s2" onclick="aShot('uv')">${T('UV 안내선')}</button>
          </div>
        </div>
        <div class="shot" id="a_shot" onclick="aZoom()">
          <span class="none">${T('뽑으면 여기 나옵니다')}</span>
        </div>
        <div class="hint">${T('누르면 크게 봅니다. 안내선 위에 칠하면 어디가 보닛인지 바로 보입니다.')}</div>
      </div>
    </div>
  </div>

  <div class="side">
  <div class="card">
    <h2>${T('다시 칠하기 — 고른 차의 텍스처를 바꿉니다')}</h2>
    <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      <div class="drop" id="a_pdrop" style="flex:1;min-width:240px"
           onclick="document.querySelector('#a_pf').click()">
        ${T('PNG 를 여기에 끌어다 놓거나 눌러서 고르세요')}</div>
      <button class="primary" onclick="aRepaint()" id="a_pbtn" disabled>
        ${T('이 차에 칠하기')}</button>
    </div>
    <input type="file" id="a_pf" accept="image/png,image/jpeg"
           style="display:none" onchange="aPngPicked(this.files[0])">
    <div id="a_pname" class="hint"></div>
    <div class="hint">${T('크기는 자동으로 맞추고 DXT1 로 눌러 넣습니다. 길이가 보존되므로 다른 자산은 건드리지 않습니다.')}</div>
  </div>

  <div class="card">
    <h2>${T('모델 들여오기 — 새 차로 추가합니다')}</h2>
    <div class="hint" style="margin:0 0 10px">
      ${T('기존 차를 덮어쓰지 않습니다. 차 한 대를 통째로 새로 만들어 자동차 상점에 올립니다.')}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="drop" id="a_odrop"
           onclick="document.querySelector('#a_of').click()">
        ${T('OBJ 를 여기에 끌어다 놓거나 눌러서 고르세요')}</div>
      <div class="drop" id="a_ndrop"
           onclick="document.querySelector('#a_nf').click()">
        ${T('차 텍스처 PNG 를 끌어다 놓거나 눌러서 고르세요')}</div>
    </div>
    <input type="file" id="a_of" accept=".obj" style="display:none"
           onchange="aObjPicked(this.files[0])">
    <input type="file" id="a_nf" accept="image/png,image/jpeg"
           style="display:none" onchange="aNewPngPicked(this.files[0])">
    <div id="a_oname" class="hint"></div>
    <div class="row" style="margin-top:10px">
      <div><label class="f">${T('영문 이름 (자산·DB 에 쓰입니다)')}</label>
        <input id="a_name" placeholder="Taegeukho" oninput="aNewCheck()"></div>
      <div><label class="f">${T('게임에 보일 이름')}</label>
        <input id="a_label" placeholder="${T('태극호')}"></div>
      <div><label class="f">${T('등급')}</label>
        <select id="a_class">
          <option>S</option><option>A</option>
          <option>B</option><option>C</option>
        </select></div>
      <div><label class="f">${T('트로피 값')}</label>
        <input id="a_trophy" type="number" value="150" min="0"></div>
      <div><label class="f">${T('골드 값 (0 이면 트로피로만 삽니다)')}</label>
        <input id="a_gold" type="number" value="0" min="0"></div>
      <div><label class="f">${T('앞면 방향')}</label>
        <select id="a_wd">
          <option value="keep">${T('그대로')}</option>
          <option value="flip">${T('통째로 뒤집기')}</option>
          <option value="auto">${T('바깥쪽으로 자동')}</option>
        </select></div>
      <div><label class="f">${T('크기')}</label>
        <select id="a_fit">
          <option value="1">${T('원본 차 크기에 맞춤')}</option>
          <option value="0">${T('OBJ 크기 그대로')}</option>
        </select></div>
    </div>
    <button class="primary" style="margin-top:10px" onclick="aNewCar()"
            id="a_obtn" disabled>${T('새 차로 추가')}</button>
    <div class="hint">${T('넣고 나면 아래에서 APK 를 다시 만들어야 기기에 반영됩니다. 서버판이라면 서버도 다시 띄워야 표가 맞습니다.')}</div>
  </div>
  </div>

  <div class="side">
  <div class="card">
    <h2>${T('자산 내보내기 — 파일로 꺼냅니다')}</h2>
    <div class="hint" style="margin:0 0 10px">
      ${T('고른 것을 PC 폴더에 파일로 씁니다. 다 되면 그 폴더를 열어 드립니다.')}</div>
    <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
      <div style="flex:1;min-width:230px">
        <label class="f">${T('무엇을')}</label>
        <select id="a_xscope" onchange="aScope()">
          <option value="one">${T('지금 보고 있는 것 하나')}</option>
          <option value="all">${T('차고에 있는 차 전부')}</option>
          <option value="pick">${T('목록에서 골라서')}</option>
        </select>
      </div>
      <button class="primary" onclick="aExport()" id="a_xbtn">${T('내보내기')}</button>
      <button onclick="aOpenFolder()">${T('폴더 열기')}</button>
    </div>
    <div id="a_xpick" style="display:none;margin-top:10px">
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
        <input id="a_xfind" placeholder="${T('이름으로 거르기')}" oninput="aPickList()"
               style="flex:1">
        <button onclick="aPickAll(1)">${T('전부')}</button>
        <button onclick="aPickAll(0)">${T('해제')}</button>
        <span class="hint" id="a_xcount"></span>
      </div>
      <div class="picklist" id="a_xlist"></div>
    </div>
    <div class="fmts" id="a_xfmts"></div>
    <div class="hint" id="a_xdir"></div>
  </div>

  <div class="card">
    <div class="hint" style="margin:0">${T('여기서 고친 것은 <b>저장 및 내보내기</b> 탭에서 세이브와 함께 '
      + '한 번에 APK 로 굽습니다.')}</div>
  </div>

  <div class="card">
    <h2>${T('진행')}</h2>
    <pre id="a_log">${T('준비됐습니다.')}</pre>
  </div>
  </div>`;
}

/* ------------------------------------------------------------ 자잘한 것 */
const aQ = s => document.querySelector(s);
function aLog(t, clear){
  const e = aQ('#a_log'); if(!e) return;
  e.textContent = clear ? t : (e.textContent + '\n' + t);
  e.scrollTop = e.scrollHeight;
}
async function aPost(p, b){
  const r = await fetch(p, {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(b||{})});
  return await r.json();
}
function aWatch(jid, done){
  if(A.tick) clearInterval(A.tick);
  let n = 0;
  A.tick = setInterval(async () => {
    const j = await aPost('/api/job', {id:jid});
    if(!j.ok) return;
    const txt = j.log.filter(l => !l.startsWith('@@')).join('\n');
    aLog(txt || '…', true);
    if(j.done){
      clearInterval(A.tick); A.tick = null;
      const at = j.log.filter(l => l.startsWith('@@'));
      let res = null;
      if(at.length){ try{ res = JSON.parse(at[at.length-1].slice(2)); }catch(e){} }
      aLog(j.result ? T('\n— 끝났습니다 —') : T('\n— 실패했습니다 —'));
      if(done) done(j.result, res);
    }
    if(++n > 3000){ clearInterval(A.tick); A.tick = null; }
  }, 700);
}

/* ------------------------------------------------------------ 목록·뽑기 */
/* 캔버스 바탕을 지금 밝기에 맞춘다. 밝기를 바꾸면 다시 부른다. */
function aClear(){
  if(!G || !G.gl) return;
  const lit = getComputedStyle(document.documentElement)
                .getPropertyValue('--code').trim();
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(lit);
  if(m) G.gl.clearColor(parseInt(m[1],16)/255, parseInt(m[2],16)/255,
                        parseInt(m[3],16)/255, 1);
  else  G.gl.clearColor(0.051, 0.063, 0.090, 1);
}
async function aInit(){
  aGL();
  const r = await aPost('/api/assets/list', {});
  /* 탭을 빨리 오가면 기다리는 사이에 화면이 갈립니다. 그러면 그냥 접습니다 */
  if(!aQ('#a_car')) return;
  A.cars = r.cars || [];
  A.meshes = r.meshes || [];
  A.cats = r.cats || [];
  const cs = aQ('#a_cat');
  cs.innerHTML = A.cats.map((g, i) =>
    `<option value="${i}">${esc3(g.label)} (${g.items.length})</option>`).join('');
  aQ('#a_note').textContent = r.indexed
    ? T('색인이 있습니다. 바로 뽑을 수 있습니다.')
    : T('자산 색인이 아직 없습니다. 처음 뽑을 때 자동으로 만듭니다(몇 분).');
  aCatPick();
  aFormats();
}
/* 갈래 -> 대상 -> 모델. 메시 202개를 한 줄에 늘어놓으면 못 고릅니다. */
function aCatPick(){
  const g = A.cats[+aQ('#a_cat').value] || {items:[]};
  aQ('#a_car').innerHTML = g.items.map((it, i) =>
    `<option value="${i}">${esc3(it.label)}</option>`).join('')
    || T('<option value="">— 없음 —</option>');
  aCar();
}
/* 대상을 고르면 그 대상의 모델(등급·LOD)만 채웁니다. */
function aCar(){
  if(!aQ('#a_car') || !aQ('#a_asset')) return;
  const g = A.cats[+aQ('#a_cat').value] || {items:[]};
  const it = g.items[+aQ('#a_car').value] || {models:[]};
  aQ('#a_asset').innerHTML = (it.models||[]).map(v =>
    `<option>${esc3(v)}</option>`).join('')
    || T('<option value="">— 없음 —</option>');
  aPick();
}
function aPick(){
  if(!aQ('#a_asset')) return;
  A.car = aQ('#a_asset').value;
  aQ('#a_pbtn').disabled = !A.pngData;
  aNewCheck();
  aStats(null);
  A.shots = null; aShot(A.shotKind || 'tex');
  A.mesh = null; A.tex = null; aQ('#a_verdict').innerHTML = ''; aDraw();
  aRigLoad(A.car);
}
function aReindex(){
  aPost('/api/assets/index', {}).then(r => { aLog(T('색인을 만드는 중입니다…'), true);
    aWatch(r.job, () => aInit()); });
}
function aExtract(){
  const car = A.car;
  aLog(T('뽑는 중입니다…'), true);
  aPost('/api/assets/get', {car}).then(r => aWatch(r.job, (ok, res) => {
    if(!ok) return;
    const u = p => '/file?p=' + encodeURIComponent(p) + '&t=' + Date.now();
    A.shots = {tex: res && res.tex ? u(res.tex) : null,
               uv:  res && res.uv  ? u(res.uv)  : null};
    aShot(A.shotKind || 'tex');
    aStats(res);
    aLoadMesh(car);
  }));
}
/* 텍스처와 UV 를 나란히 두면 오른쪽 칸이 길어져 아래 카드를 밀어냅니다.
   그래서 한 번에 하나만, 자리는 늘 같은 크기로 보여 줍니다. */
function aShot(kind){
  A.shotKind = kind;
  const box = aQ('#a_shot'); if(!box) return;
  const b1 = aQ('#a_s1'), b2 = aQ('#a_s2');
  if(b1) b1.className = kind === 'tex' ? 'on' : '';
  if(b2) b2.className = kind === 'uv' ? 'on' : '';
  const src = A.shots && A.shots[kind];
  box.innerHTML = src ? `<img src="${src}" alt="">`
    : `<span class="none">${A.shots ? T('이 자산엔 텍스처가 없습니다')
                                    : T('뽑으면 여기 나옵니다')}</span>`;
  box.style.cursor = src ? 'zoom-in' : 'default';
}
function aZoom(){
  const src = A.shots && A.shots[A.shotKind || 'tex'];
  if(!src) return;
  const d = document.createElement('div');
  d.className = 'zoom';
  d.innerHTML = `<img src="${src}" alt=""><div class="cap">`
    + `${A.car} ${T('— 아무 데나 누르면 닫힙니다')}</div>`;
  d.onclick = () => d.remove();
  document.body.appendChild(d);
}
function aStats(res){
  const e = aQ('#a_stats');
  if(!e) return;
  /* 뽑기 전에도 **같은 줄 수**로 그립니다. 값만 채워 넣어야 카드 키가
     안 변하고, 그래야 아래 카드들이 제자리에 있습니다. */
  const m = res && res.mesh, ts = res && res.texSize;
  const dash = '—';
  let h = '';
  const row = (k,v) => `<div class="stat"><span>${k}</span><b>${v}</b></div>`;
  h += row(T('이름|자산'), res ? res.car : dash);
  h += row(T('메시'), m ? m.name : dash);
  h += row(T('정점'), m ? m.verts.toLocaleString() : dash);
  h += row(T('삼각형'), m ? m.tris.toLocaleString() : dash);
  h += row(T('크기 (좌우×앞뒤×높이)'),
           m ? (m.size[0]+' × '+m.size[1]+' × '+m.size[2]) : dash);
  h += row(T('텍스처'), ts ? (ts[0]+' × '+ts[1]) : dash);
  h += `<div class="hint" style="margin-top:9px;display:flex;gap:6px;
        flex-wrap:wrap">
        <button onclick="aQuick('obj')" ${res ? '' : 'disabled'}>${T('OBJ 로 꺼내기')}</button>
        <button onclick="aQuick('glb')" ${res ? '' : 'disabled'}>${T('glTF 로 꺼내기')}</button>
        </div>
        <div class="hint" style="margin-top:6px">${T('아래 <b>자산 내보내기</b> 에서 형식과 범위를 더 고를 수 있습니다.')}</div>`;
  e.innerHTML = h;
}

/* ------------------------------------------------------------ 내보내기 */
/* 창 런처(webview)는 &lt;a download&gt; 가 먹지 않습니다. 그래서 내려받기
   대신 서버가 PC 폴더에 직접 쓰고, 끝나면 탐색기로 열어 줍니다. */
async function aFormats(){
  const r = await aPost('/api/assets/formats', {});
  if(!aQ('#a_xfmts')) return;
  A.formats = r.formats || [];
  A.xdir = r.dir || '';
  const on = {obj:1, png:1};
  aQ('#a_xfmts').innerHTML = A.formats.map(f =>
    `<label><input type="checkbox" class="xf" value="${f.key}"
      ${on[f.key] ? 'checked' : ''}><span>${f.desc}</span></label>`).join('');
  aQ('#a_xdir').textContent = T('나가는 곳: {dir}', {dir:A.xdir});
}
function aScope(){
  const s = aQ('#a_xscope').value;
  aQ('#a_xpick').style.display = s === 'pick' ? '' : 'none';
  if(s === 'pick' && !aQ('#a_xlist').childElementCount) aPickList();
}
function aPickList(){
  const q = (aQ('#a_xfind').value || '').toLowerCase();
  const names = (A.meshes || []);
  const keep = new Set(A.picked || []);
  const shown = names.filter(n => !q || n.toLowerCase().includes(q));
  const esc2 = x => String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;');
  aQ('#a_xlist').innerHTML = shown.slice(0, 400).map(n =>
    `<label><input type="checkbox" class="xp" value="${esc2(n)}"
      ${keep.has(n) ? 'checked' : ''} onchange="aPickKeep()">`
    + `<span>${esc2(n)}</span></label>`).join('')
    || T('<span class="hint">그런 이름이 없습니다</span>');
  aPickCount(shown.length, names.length);
}
function aPickKeep(){
  const set = new Set(A.picked || []);
  document.querySelectorAll('.xp').forEach(c => {
    if(c.checked) set.add(c.value); else set.delete(c.value); });
  A.picked = [...set];
  aPickCount();
}
function aPickCount(shown, total){
  const e = aQ('#a_xcount'); if(!e) return;
  const n = (A.picked || []).length;
  e.textContent = (shown != null
                     ? T('{shown}/{total} 보임 · {n}개 고름',
                         {shown:shown, total:total, n:n})
                     : T('{n}개 고름', {n:n}));
}
function aPickAll(on){
  document.querySelectorAll('.xp').forEach(c => { c.checked = !!on; });
  aPickKeep();
}
function aChecked(){
  return [...document.querySelectorAll('.xf')].filter(c => c.checked)
         .map(c => c.value);
}
function aQuick(fmt){
  aRunExport({scope:'one', car:A.car, formats:[fmt, 'png']});
}
function aExport(){
  const scope = aQ('#a_xscope').value;
  const fmts = aChecked();
  if(!fmts.length){ aLog(T('내보낼 형식을 하나는 고르세요.'), true); return; }
  const b = {scope, formats:fmts, car:A.car, names:(A.picked || [])};
  if(scope === 'pick' && !b.names.length){
    aLog(T('목록에서 자산을 골라 주세요.'), true); return; }
  aRunExport(b);
}
function aRunExport(body){
  aLog(T('내보내는 중입니다…'), true);
  const btn = aQ('#a_xbtn'); if(btn) btn.disabled = true;
  aPost('/api/assets/export', body).then(r => {
    if(!r.ok){ aLog(r.msg || T('실패했습니다')); if(btn) btn.disabled = false;
               return; }
    aWatch(r.job, (ok, res) => {
      if(btn) btn.disabled = false;
      if(ok && res && res.dir) aOpenFolder(res.dir);
    });
  });
}
function aOpenFolder(path){
  aPost('/api/assets/openfolder', {path: (typeof path === 'string') ? path : ''})
    .then(r => { if(!r.ok) aLog(r.msg || T('폴더를 못 열었습니다')); });
}

/* ------------------------------------------------------------ 칠하기·넣기 */
A.pngData = null; A.objText = null; A.newPng = null;
function aPngPicked(f){
  if(!f) return;
  const rd = new FileReader();
  rd.onload = () => { A.pngData = rd.result;
    aQ('#a_pname').textContent = T('{name} — 준비됐습니다', {name:f.name});
    aQ('#a_pbtn').disabled = false;
    aQ('#a_ti').src = rd.result; };
  rd.readAsDataURL(f);
}
function aObjPicked(f){
  if(!f) return;
  const rd = new FileReader();
  rd.onload = () => { A.objText = rd.result;
    A.objName = f.name;
    /* 이름을 안 적었으면 파일 이름에서 짐작해 채워 둡니다 */
    const base = f.name.replace(/\.obj$/i,'').replace(/[^A-Za-z0-9]/g,'');
    if(base && !aQ('#a_name').value) aQ('#a_name').value = base;
    aNewCheck(); };
  rd.readAsText(f);
}
function aNewPngPicked(f){
  if(!f) return;
  const rd = new FileReader();
  rd.onload = () => { A.newPng = rd.result; aNewCheck(); };
  rd.readAsDataURL(f);
}
/* 이름 · OBJ · PNG 가 다 있어야 넣을 수 있습니다 */
function aNewCheck(){
  const nm = (aQ('#a_name')||{}).value || '';
  const ok = !!(A.objText && A.newPng && /^[A-Za-z][A-Za-z0-9]*$/.test(nm));
  const b = aQ('#a_obtn'); if(b) b.disabled = !ok;
  const e = aQ('#a_oname'); if(!e) return;
  if(!A.objText && !A.newPng){ e.textContent = ''; return; }
  const faces = A.objText ? (A.objText.match(/^f /gm)||[]).length : 0;
  const bits = [A.objText ? T('{name} — 면 {n}개', {name:A.objName, n:faces})
                          : T('OBJ 를 아직 안 골랐습니다'),
                A.newPng ? T('텍스처 준비됨') : T('텍스처를 아직 안 골랐습니다')];
  if(A.objText && A.newPng && !ok) bits.push(T('이름은 영문으로 시작해야 합니다'));
  e.textContent = bits.join(' · ');
}
function aRepaint(){
  aLog(T('칠하는 중입니다…'), true);
  aPost('/api/assets/repaint', {car:A.car, png:A.pngData})
    .then(r => aWatch(r.job, ok => { if(ok) aLoadMesh(A.car); }));
}
function aNewCar(){
  const nm = aQ('#a_name').value.trim();
  aLog(T('새 차 "{name}" 를 넣는 중입니다…', {name:nm}), true);
  aPost('/api/assets/newcar', {
    name: nm, label: aQ('#a_label').value.trim() || nm,
    'class': aQ('#a_class').value,
    gold: +aQ('#a_gold').value || 0, trophy: +aQ('#a_trophy').value || 0,
    obj: A.objText, png: A.newPng,
    winding: aQ('#a_wd').value, fit: aQ('#a_fit').value === '1'
  }).then(r => {
    if(!r.ok){ aLog(r.msg || T('넣지 못했습니다')); return; }
    aWatch(r.job, ok => { if(ok) aInit(); });
  });
}
/* 끌어다 놓기 */
function aDrop(id, cb){
  const e = aQ(id); if(!e) return;
  ['dragenter','dragover'].forEach(t => e.addEventListener(t, ev => {
    ev.preventDefault(); e.classList.add('hot'); }));
  ['dragleave','drop'].forEach(t => e.addEventListener(t, ev => {
    ev.preventDefault(); e.classList.remove('hot'); }));
  e.addEventListener('drop', ev => {
    if(ev.dataTransfer.files.length) cb(ev.dataTransfer.files[0]); });
}

/* ======================================================== WebGL 미리보기 */
let G = null;
function aGL(){
  const cv = aQ('#a_cv'); if(!cv) return;
  aDrop('#a_pdrop', aPngPicked); aDrop('#a_odrop', aObjPicked);
  aDrop('#a_ndrop', aNewPngPicked);
  let gl = null;
  try { gl = cv.getContext('webgl') || cv.getContext('experimental-webgl'); }
  catch(e){}
  if(!gl){ cv.outerHTML =
    T('<div class="hint">이 브라우저는 WebGL 이 없어 3D 미리보기를 그릴 수 없습니다.</div>');
    return; }
  const vs = `attribute vec3 p; attribute vec2 t; attribute vec3 n;
    uniform mat4 mvp, mv; varying vec2 vt; varying vec3 vn;
    void main(){ vt=t; vn=(mv*vec4(n,0.0)).xyz; gl_Position=mvp*vec4(p,1.0); }`;
  const fs = `precision mediump float;
    uniform sampler2D s; uniform float useTex, check, flat_;
    varying vec2 vt; varying vec3 vn;
    void main(){
      vec3 base = useTex>0.5 ? texture2D(s, vt).rgb : vec3(0.70,0.73,0.80);
      float l = max(dot(normalize(vn), normalize(vec3(0.35,0.45,0.82))),0.0)
                *0.78 + 0.24;
      vec3 c = flat_>0.5 ? vec3(0.42,0.68,1.0) : base*l;
      if(check>0.5 && !gl_FrontFacing) c = vec3(1.0,0.18,0.28);
      gl_FragColor = vec4(c,1.0);
    }`;
  const mk = (ty, src) => { const sh = gl.createShader(ty);
    gl.shaderSource(sh, src); gl.compileShader(sh); return sh; };
  const pr = gl.createProgram();
  gl.attachShader(pr, mk(gl.VERTEX_SHADER, vs));
  gl.attachShader(pr, mk(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(pr); gl.useProgram(pr);
  G = { gl, pr, cv, yaw:0.7, pitch:0.35, dist:2.6, n:0, spin:0,
        buf:{p:gl.createBuffer(), t:gl.createBuffer(), n:gl.createBuffer()},
        wire:gl.createBuffer(), wn:0, tex:gl.createTexture(), hasTex:0 };
  gl.enable(gl.DEPTH_TEST);
  /* 3D 바탕은 화면 밝기를 따라갑니다. 어두운 판에서 흰 바탕이 나오면
     눈이 아프고, 밝은 판에서 검은 상자만 덩그러니 놓이면 겉돕니다. */
  aClear();
  let down = null;
  cv.addEventListener('mousedown', e => down = [e.clientX, e.clientY]);
  window.addEventListener('mouseup', () => down = null);
  window.addEventListener('mousemove', e => {
    if(!down) return;
    G.yaw += (e.clientX - down[0]) * 0.01;
    G.pitch = Math.max(-1.5, Math.min(1.5,
              G.pitch + (e.clientY - down[1]) * 0.01));
    down = [e.clientX, e.clientY]; aDraw(); });
  cv.addEventListener('wheel', e => { e.preventDefault();
    G.dist = Math.max(0.9, Math.min(9, G.dist * (e.deltaY > 0 ? 1.1 : 0.9)));
    aDraw(); }, {passive:false});
  aDraw();
}
function aMode(m){
  A.mode = m;
  ['a_m1','a_m2','a_m3'].forEach((id,i) => aQ('#'+id).classList.toggle(
    'on', i === {normal:0, check:1, wire:2}[m]));
  aDraw();
}
function aSpin(){
  G.spin = aQ('#a_spin').checked ? 1 : 0;
  if(G.spin) aTickSpin();
}
function aTickSpin(){
  if(!G || !G.spin) return;
  G.yaw += 0.012; aDraw(); requestAnimationFrame(aTickSpin);
}

async function aLoadMesh(car){
  const m = await aPost('/api/assets/mesh', {car});
  if(!m.ok){ aLog(m.msg || T('메시를 읽지 못했습니다')); return; }
  A.mesh = m;
  aUpload(m);
  if(m.tex) aTexture('/file?p=' + encodeURIComponent(m.tex) + '&t=' + Date.now());
  aVerdict(m);
  aDraw();
}
/* 동작을 재생하려면 프레임마다 정점이 바뀝니다. 그래서 삼각형을 펼친
   배열을 **미리 잡아 두고** 자리만 다시 채웁니다(매 프레임 새로 만들면
   쓰레기가 쌓입니다). 법선도 같이 다시 계산합니다 — 안 그러면 차가
   움직여도 빛이 따라오지 않아 종이처럼 보입니다. */
function aUpload(m){
  if(!G) return;
  const gl = G.gl, tri = m.tri, nt = tri.length;
  G.tri = tri;
  G.vsrc = new Float32Array(m.v);
  G.vpose = new Float32Array(m.v);          /* 스키닝 결과가 들어갈 자리 */
  G.P = new Float32Array(nt*3);
  G.N = new Float32Array(nt*3);
  G.T = new Float32Array(nt*2);
  G.Wv = new Float32Array(nt*6);
  const uv = m.uv;
  for(let k = 0, o = 0; k < nt; k++, o += 2){
    const i = tri[k];
    G.T[o] = uv.length ? uv[i*2] : 0;
    G.T[o+1] = uv.length ? uv[i*2+1] : 0;
  }
  aFill(G.vsrc);
  const put = (b, arr) => { gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, arr, gl.DYNAMIC_DRAW); };
  put(G.buf.p, G.P); put(G.buf.t, G.T); put(G.buf.n, G.N); put(G.wire, G.Wv);
  G.n = nt; G.wn = nt*2;
  const e = m.extent;
  G.scale = 1 / (Math.max(e[0], e[1], e[2]) || 1);
  G.ctr = m.center;
}
/* 정점 배열 하나로 펼친 삼각형·법선·뼈대선을 채웁니다. */
function aFill(v){
  const tri = G.tri, P = G.P, N = G.N, W = G.Wv;
  for(let k = 0, o = 0, wo = 0; k < tri.length; k += 3, o += 9, wo += 18){
    const a = tri[k]*3, b = tri[k+1]*3, c = tri[k+2]*3;
    const ux = v[b]-v[a], uy = v[b+1]-v[a+1], uz = v[b+2]-v[a+2];
    const wx = v[c]-v[a], wy = v[c+1]-v[a+1], wz = v[c+2]-v[a+2];
    let nx = uy*wz-uz*wy, ny = uz*wx-ux*wz, nz = ux*wy-uy*wx;
    const L = Math.hypot(nx,ny,nz) || 1; nx/=L; ny/=L; nz/=L;
    const idx = [a,b,c];
    for(let j = 0; j < 3; j++){
      const i = idx[j], q = o + j*3;
      P[q] = v[i]; P[q+1] = v[i+1]; P[q+2] = v[i+2];
      N[q] = nx; N[q+1] = ny; N[q+2] = nz;
    }
    const e = [a,b, b,c, c,a];
    for(let j = 0; j < 6; j++){
      const i = e[j], q = wo + j*3;
      W[q] = v[i]; W[q+1] = v[i+1]; W[q+2] = v[i+2];
    }
  }
}
/* ------------------------------------------------------------ 동작 보기 */
/* 이 게임의 차는 스키닝 메시라 뼈가 자세를 잡습니다. 서버가 프레임마다
   뼈별 행렬을 구워 주고, 여기서는 정점마다 그걸 가중치로 섞습니다.
   정점이 1000개 안쪽이라 CPU 로 해도 넉넉합니다. */
async function aRigLoad(car){
  aRigStop();
  A.rig = null; A.anim = null;
  const sel = aQ('#a_clip'); if(!sel) return;
  sel.innerHTML = T('<option value="">— 정지 —</option>');
  aRigEnable(false, '');
  const r = await aPost('/api/assets/anim', {car});
  if(!aQ('#a_clip') || A.car !== car) return;
  if(!r.ok){
    aRigEnable(false, r.need === 'index'
      ? T('뼈대 색인이 없습니다 — 아래 단추로 한 번 만드세요') : (r.msg || ''));
    if(r.need === 'index'){
      const b = aQ('#a_play');
      if(b){ b.disabled = false; b.textContent = T('뼈대 색인 만들기');
             b.onclick = aRigIndex; }
    }
    return;
  }
  A.rig = r;
  sel.innerHTML = T('<option value="">— 정지 —</option>') + (r.clips||[]).map(c =>
    `<option value="${esc3(c.name)}">${esc3(c.name)} · ${T('{n}초',{n:c.length})}</option>`
  ).join('');
  aRigEnable(false, (r.clips||[]).length
    ? T('뼈 {bones}개 · 동작 {clips}개', {bones:r.bones.length, clips:r.clips.length})
    : T('뼈는 있는데 붙어 있는 동작이 없습니다'));
}
const esc3 = x => String(x).replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function aRigEnable(on, note){
  const b = aQ('#a_play'), sk = aQ('#a_seek'), f = aQ('#a_frame');
  if(b){ b.disabled = !on; b.textContent = A.playing ? T('멈춤') : T('재생');
         b.onclick = aPlay; }
  if(sk) sk.disabled = !on;
  if(f && note !== undefined) f.textContent = note;
}
function aRigIndex(){
  aLog(T('뼈대 색인을 만드는 중입니다…'), true);
  aPost('/api/assets/anim/index', {}).then(r =>
    aWatch(r.job, () => aRigLoad(A.car)));
}
async function aClip(){
  aRigStop();
  const name = aQ('#a_clip').value;
  if(!name){ A.anim = null; G.animScale = 0; aRestPose();
             aRigEnable(false, ''); return; }
  aQ('#a_frame').textContent = T('굽는 중…');
  const r = await aPost('/api/assets/anim/bake', {car:A.car, clip:name});
  if(!r.ok){ aQ('#a_frame').textContent = r.msg || T('실패'); return; }
  A.anim = {fps:r.fps, count:r.count, bones:r.bones,
            m:new Float32Array(r.m)};
  A.frame = 0;
  const sk = aQ('#a_seek'); sk.max = r.count - 1; sk.value = 0;
  aFitAnim();
  aRigEnable(true, '');
  aPlay(true);
}
/* 동작에 맞춰 화면을 다시 잡습니다. `jump` 처럼 차가 위로 크게 솟는
   동작은 정지 자세 기준으로 잡으면 재생 내내 화면 밖으로 나가 버립니다.
   모든 프레임을 훑어 실제로 차지하는 자리를 구합니다(정점은 띄엄띄엄
   봐도 테두리는 거의 그대로입니다). */
function aFitAnim(){
  const R = A.rig, an = A.anim;
  if(!R || !an || !G || !G.vsrc){ return; }
  const src = G.vsrc, M = an.m, nv = Math.min(R.verts, src.length/3);
  const step = Math.max(1, Math.floor(nv/160));
  let lo = [1e9,1e9,1e9], hi = [-1e9,-1e9,-1e9];
  for(let f = 0; f < an.count; f++){
    const base = f*an.bones*16;
    for(let i = 0; i < nv; i += step){
      const x = src[i*3], y = src[i*3+1], z = src[i*3+2];
      let ox = 0, oy = 0, oz = 0;
      for(let k = 0; k < 4; k++){
        const w = R.w[i*4+k];
        if(w <= 0) continue;
        const o = base + R.b[i*4+k]*16;
        ox += w*(M[o]*x   + M[o+1]*y  + M[o+2]*z  + M[o+3]);
        oy += w*(M[o+4]*x + M[o+5]*y  + M[o+6]*z  + M[o+7]);
        oz += w*(M[o+8]*x + M[o+9]*y  + M[o+10]*z + M[o+11]);
      }
      const q = [ox,oy,oz];
      for(let j = 0; j < 3; j++){
        if(q[j] < lo[j]) lo[j] = q[j];
        if(q[j] > hi[j]) hi[j] = q[j];
      }
    }
  }
  const ext = [hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]];
  G.animCtr = [(lo[0]+hi[0])/2, (lo[1]+hi[1])/2, (lo[2]+hi[2])/2];
  /* 다 담으려고만 하면 헬리의 변신처럼 크게 솟는 동작에서 차가 콩알만
     해집니다. 정지 때 크기의 절반 밑으로는 안 줄입니다 — 잠깐 화면 밖으로
     나가더라도 무엇이 움직이는지는 보여야 합니다. */
  const fit = 1 / (Math.max(ext[0], ext[1], ext[2]) || 1);
  G.animScale = Math.max(fit, (G.scale || fit) * 0.5);
}
function aRestPose(){
  if(!G || !G.vsrc) return;
  aFill(G.vsrc); aReupload(); aDraw();
}
function aSkin(f){
  const R = A.rig, an = A.anim;
  if(!R || !an || !G) return;
  const M = an.m, base = f * an.bones * 16;
  const src = G.vsrc, dst = G.vpose, w = R.w, bi = R.b;
  const nv = Math.min(R.verts, src.length/3);
  for(let i = 0; i < nv; i++){
    const x = src[i*3], y = src[i*3+1], z = src[i*3+2];
    let ox = 0, oy = 0, oz = 0;
    for(let k = 0; k < 4; k++){
      const ww = w[i*4+k];
      if(ww <= 0) continue;
      const o = base + bi[i*4+k]*16;
      ox += ww*(M[o]*x   + M[o+1]*y  + M[o+2]*z  + M[o+3]);
      oy += ww*(M[o+4]*x + M[o+5]*y  + M[o+6]*z  + M[o+7]);
      oz += ww*(M[o+8]*x + M[o+9]*y  + M[o+10]*z + M[o+11]);
    }
    dst[i*3] = ox; dst[i*3+1] = oy; dst[i*3+2] = oz;
  }
  aFill(dst); aReupload();
}
function aSeek(f){
  if(!A.anim) return;
  A.frame = Math.max(0, Math.min(A.anim.count-1, f|0));
  aSkin(A.frame); aDraw(); aFrameNote();
}
function aFrameNote(){
  const e = aQ('#a_frame');
  if(e && A.anim) e.textContent = T('{at} / {all} 프레임',
    {at:A.frame+1, all:A.anim.count});
}
function aPlay(force){
  if(!A.anim) return;
  A.playing = (force === true) ? 1 : (A.playing ? 0 : 1);
  const b = aQ('#a_play'); if(b) b.textContent = A.playing ? T('멈춤') : T('재생');
  if(A.playing){ A.last = performance.now(); aAnimTick(); }
}
function aRigStop(){
  A.playing = 0;
  const b = aQ('#a_play'); if(b) b.textContent = T('재생');
}
function aAnimTick(){
  if(!A.playing || !A.anim || !aQ('#a_cv')){ A.playing = 0; return; }
  const now = performance.now();
  const step = 1000 / (A.anim.fps || 30);
  if(now - A.last >= step){
    A.last = now;
    A.frame = (A.frame + 1) % A.anim.count;
    aSkin(A.frame); aDraw(); aFrameNote();
    const sk = aQ('#a_seek'); if(sk) sk.value = A.frame;
  }
  requestAnimationFrame(aAnimTick);
}

function aReupload(){
  const gl = G.gl;
  const sub = (b, arr) => { gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferSubData(gl.ARRAY_BUFFER, 0, arr); };
  sub(G.buf.p, G.P); sub(G.buf.n, G.N); sub(G.wire, G.Wv);
}
function aTexture(url){
  const gl = G.gl, im = new Image();
  im.onload = () => {
    gl.bindTexture(gl.TEXTURE_2D, G.tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, im);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    G.hasTex = 1; aDraw();
  };
  im.src = url;
}
/* 감기 진단.

   무게중심으로 안팎을 세는 방법은 이 게임 차에는 못 쓴다. 원본 차들도
   전부 50% 가 나온다 — 차 메시가 **속이 빈 얇은 껍데기**라 겉면과 속면이
   반반이기 때문이다. 그래서 두 가지만 본다.
     1) 모서리가 짝을 이루는가  = 감기가 서로 어긋나지 않았는가
     2) 부호 있는 부피          = 통째로 뒤집혔는가 (두꺼운 모양일 때만) */
function aVerdict(m){
  const v = m.v, tri = m.tri;
  const ed = new Map();
  let vol = 0, avol = 0, bad = 0;
  const key = i => v[i*3].toFixed(4)+','+v[i*3+1].toFixed(4)+','+v[i*3+2].toFixed(4);
  const K = [];
  for(let i = 0; i < v.length/3; i++) K.push(key(i));
  for(let k = 0; k < tri.length; k += 3){
    const a = tri[k], b = tri[k+1], c = tri[k+2];
    for(const e of [[a,b],[b,c],[c,a]]){
      const s2 = K[e[0]] + '|' + K[e[1]];
      ed.set(s2, (ed.get(s2)||0) + 1);
    }
    const A0 = [v[a*3],v[a*3+1],v[a*3+2]];
    const B0 = [v[b*3],v[b*3+1],v[b*3+2]];
    const C0 = [v[c*3],v[c*3+1],v[c*3+2]];
    const d = (A0[0]*(B0[1]*C0[2]-B0[2]*C0[1])
             - A0[1]*(B0[0]*C0[2]-B0[2]*C0[0])
             + A0[2]*(B0[0]*C0[1]-B0[1]*C0[0]))/6;
    vol += d; avol += Math.abs(d);
  }
  let paired = 0;
  for(const [s2, n] of ed){
    if(n > 1) bad++;
    else { const p2 = s2.split('|'); if(ed.has(p2[1]+'|'+p2[0])) paired++; }
  }
  const pct = ed.size ? Math.round(paired * 100 / ed.size) : 0;
  const rel = avol ? vol / avol : 0;
  const e = aQ('#a_verdict');
  if(!e) return;
  let h = '';
  if(bad > 0)
    h += `<div class="warnbox">${T('같은 방향으로 두 번 쓰인 모서리가 '
      + '<b>{n}개</b> 있습니다. 면끼리 감기가 어긋났다는 뜻이라 어느 쪽에서 '
      + '보든 군데군데 뚫려 보입니다. 블렌더에서 법선을 정리하고 다시 '
      + '내보내세요.', {n:bad})}</div>`;
  else if(pct >= 90)
    h += `<div class="okbox">${T('모서리 <b>{pct}%</b>가 짝을 이룹니다. '
      + '감기는 서로 어긋나지 않았습니다.', {pct:pct})}</div>`;
  else
    h += `<div class="warnbox">${T('모서리 짝이 <b>{pct}%</b> 뿐입니다. '
      + '열린 면이 많다는 뜻이니 뚫린 곳이 없는지 <b>감기 검사</b> 로 '
      + '확인하세요.', {pct:pct})}</div>`;
  if(Math.abs(rel) > 0.15)
    h += rel > 0
      ? `<div class="okbox">${T('부피 부호가 <b>바깥</b>을 가리킵니다.')}</div>`
      : `<div class="warnbox">${T('부피 부호가 <b>안쪽</b>을 가리킵니다. '
        + '통째로 뒤집힌 모양입니다. 넣을 때 <b>통째로 뒤집기</b> 를 '
        + '고르세요.')}</div>`;
  else
    h += `<div class="hint">${T('얇은 껍데기라 부피로는 안팎을 가릴 수 '
      + '없습니다 (원본 차들도 그렇습니다). <b>감기 검사</b>를 눌러 눈으로 '
      + '보세요 — 빨간 면이 넓게 보이면 주행 화면에서 새까맣게 나옵니다.')}</div>`;
  e.innerHTML = h;
}

/* 행렬 */
function mPersp(f, a, n, q){
  const t = 1/Math.tan(f/2);
  return [t/a,0,0,0, 0,t,0,0, 0,0,(q+n)/(n-q),-1, 0,0,2*q*n/(n-q),0];
}
function mMul(A_, B_){
  const o = new Array(16);
  for(let i=0;i<4;i++) for(let j=0;j<4;j++){
    let s=0; for(let k=0;k<4;k++) s += A_[k*4+j]*B_[i*4+k];
    o[i*4+j]=s;
  }
  return o;
}
function mView(yaw, pitch, dist){
  const cy=Math.cos(yaw), sy=Math.sin(yaw);
  const cp=Math.cos(pitch), sp=Math.sin(pitch);
  /* z 가 위인 좌표계를 카메라로 옮깁니다 */
  const r = [ cy, -sy*sp, sy*cp, 0,
              sy,  cy*sp,-cy*cp, 0,
               0,     cp,    sp, 0,
               0,      0, -dist, 1];
  return r;
}
function aDraw(){
  if(!G) return;
  const gl = G.gl, cv = G.cv;
  const w = cv.clientWidth || 600, h = cv.clientHeight || 380;
  if(cv.width !== w || cv.height !== h){ cv.width = w; cv.height = h; }
  gl.viewport(0, 0, w, h);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  if(!G.n) return;
  const anim = !!(A.anim && G.animScale);
  const s = (anim ? G.animScale : G.scale) || 1;
  const c = (anim ? G.animCtr : G.ctr) || [0,0,0];
  const model = [s,0,0,0, 0,s,0,0, 0,0,s,0,
                 -c[0]*s, -c[1]*s, -c[2]*s, 1];
  const mv = mMul(mView(G.yaw, G.pitch, G.dist), model);
  const mvp = mMul(mPersp(0.85, w/h, 0.05, 60), mv);
  const u = n => gl.getUniformLocation(G.pr, n);
  gl.uniformMatrix4fv(u('mvp'), false, new Float32Array(mvp));
  gl.uniformMatrix4fv(u('mv'), false, new Float32Array(mv));
  const useTex = (aQ('#a_tex') && aQ('#a_tex').checked && G.hasTex
                  && A.mode !== 'wire') ? 1 : 0;
  gl.uniform1f(u('useTex'), useTex);
  gl.uniform1f(u('check'), A.mode === 'check' ? 1 : 0);
  gl.uniform1f(u('flat_'), A.mode === 'wire' ? 1 : 0);
  if(useTex){ gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, G.tex); gl.uniform1i(u('s'), 0); }
  if(A.mode === 'check') gl.disable(gl.CULL_FACE);
  else { gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK); }
  const bind = (b, name, sz) => {
    const l = gl.getAttribLocation(G.pr, name);
    if(l < 0) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(l);
    gl.vertexAttribPointer(l, sz, gl.FLOAT, false, 0, 0);
  };
  if(A.mode === 'wire'){
    /* 뼈대는 정점 수가 달라서 uv·법선 배열을 끄고 상수로 줍니다 */
    bind(G.wire, 'p', 3);
    for(const nm of ['t','n']){
      const l = gl.getAttribLocation(G.pr, nm);
      if(l >= 0){ gl.disableVertexAttribArray(l);
        if(nm === 't') gl.vertexAttrib2f(l, 0, 0);
        else gl.vertexAttrib3f(l, 0, 0, 1); }
    }
    gl.drawArrays(gl.LINES, 0, G.wn);
  } else {
    bind(G.buf.p, 'p', 3); bind(G.buf.t, 't', 2); bind(G.buf.n, 'n', 3);
    gl.drawArrays(gl.TRIANGLES, 0, G.n);
  }
}
</script>
"""
