#!/usr/bin/env python3
"""
proxy_viewer.py — generate a self-contained HTML proxy-alignment editor.

Input : proxy_recipe.json (proxy_extract.py; optionally + worn_overlay.py "worn").
Output: standalone HTML. Blender-style move/rotate gizmo per proxy; two clothing
        overlays — "Worn ref" (selected slot, native coords = alignment target) and
        "Resultado final" (every slot attached to its proxy = assembled preview that
        follows your edits); exports edits JSON for proxy_apply.py.

Three.js r0.147 UMD + OrbitControls + TransformControls via jsDelivr (file:// safe).
"""
import sys, os, json

HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Proxy Align — __MODEL__</title>
<style>
  html,body{margin:0;height:100%;background:#1a1d21;color:#dfe3e8;font:13px/1.4 system-ui,sans-serif;overflow:hidden}
  #wrap{display:flex;height:100vh}
  #side{width:280px;background:#23272e;border-right:1px solid #333;display:flex;flex-direction:column}
  #side h1{font-size:14px;margin:0;padding:12px;border-bottom:1px solid #333;color:#fff}
  #side h1 small{display:block;color:#8b93a0;font-weight:400;font-size:11px;margin-top:3px}
  #list{flex:1;overflow:auto}
  .row{padding:8px 12px;border-bottom:1px solid #2b2f37;cursor:pointer;display:flex;align-items:center;gap:8px}
  .row:hover{background:#2b313a}
  .row.sel{background:#33405a}
  .dot{width:11px;height:11px;border-radius:50%;flex:none}
  .row .nm{font-weight:600}
  .row .sl{color:#8b93a0;font-size:11px}
  .row.moved .nm::after{content:" *";color:#ffb454}
  .row .wbadge{margin-left:auto;font-size:9px;color:#7fd1a6;border:1px solid #2e6b4d;border-radius:3px;padding:0 4px}
  #foot{padding:10px 12px;border-top:1px solid #333;font-size:11px;color:#8b93a0}
  #main{flex:1;position:relative}
  #cv{display:block;width:100%;height:100%}
  #bar{position:absolute;top:10px;left:10px;display:flex;gap:6px;flex-wrap:wrap;max-width:70%}
  button{background:#2f3742;color:#dfe3e8;border:1px solid #444;border-radius:5px;padding:6px 10px;cursor:pointer;font-size:12px}
  button:hover{background:#3a4350}
  button.on{background:#3f6bd6;border-color:#3f6bd6;color:#fff}
  #read{position:absolute;bottom:10px;left:10px;background:rgba(20,22,26,.9);border:1px solid #333;border-radius:6px;padding:10px;min-width:240px;font-variant-numeric:tabular-nums}
  #read b{color:#fff}
  #read .g{color:#8b93a0}
  #help{position:absolute;top:10px;right:10px;background:rgba(20,22,26,.85);border:1px solid #333;border-radius:6px;padding:8px 10px;font-size:11px;color:#aab1bd;max-width:240px}
  .lbl{position:absolute;transform:translate(-50%,-120%);background:rgba(0,0,0,.6);padding:1px 5px;border-radius:3px;font-size:10px;pointer-events:none;white-space:nowrap}
  #modal{position:absolute;inset:0;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center}
  #modal .box{background:#23272e;border:1px solid #444;border-radius:8px;padding:14px;width:70%;max-width:680px}
  #modal textarea{width:100%;height:300px;background:#15171b;color:#cfe;border:1px solid #333;border-radius:5px;font:12px monospace;padding:8px;box-sizing:border-box}
  kbd{background:#333;border-radius:3px;padding:0 4px;border:1px solid #555}
</style></head><body>
<div id="wrap">
  <div id="side">
    <h1>Proxy Align<small>__MODEL__</small></h1>
    <div id="list"></div>
    <div id="foot">Sin selección</div>
  </div>
  <div id="main">
    <canvas id="cv"></canvas>
    <div id="bar">
      <button id="bMove" class="on">Mover (W)</button>
      <button id="bRot">Rotar (E)</button>
      <button id="bResult">Resultado final</button>
      <button id="bWorn">Worn ref</button>
      <button id="bBody" class="on">Cuerpo</button>
      <button id="bWire">Wireframe</button>
      <button id="bGrid" class="on">Grid</button>
      <button id="bReset">Reset proxy</button>
      <button id="bExport">Exportar edits</button>
    </div>
    <div id="help">
      Clic en un proxy (lista o 3D) para engancharle el gizmo.<br>
      <kbd>W</kbd> mover · <kbd>E</kbd> rotar · arrastra flechas/aros.<br>
      <b>Resultado final</b>: viste el maniquí con cada prenda en su proxy (sigue tus ediciones).<br>
      <b>Worn ref</b>: prenda del proxy seleccionado en su sitio nativo, como objetivo.<br>
      <b>Exportar</b>: triángulos canónicos no-ambiguos (rotación determinista).<br>
      Orbitar: arrastrar vacío · Pan: botón derecho · Zoom: rueda.
    </div>
    <div id="read"><span class="g">Selecciona un proxy…</span></div>
  </div>
</div>
<div id="modal"><div class="box">
  <div style="margin-bottom:8px">Edits JSON — <b>Seleccionar todo</b> + <kbd>Ctrl+C</kbd>, guarda como <b>edits.json</b> y pásalo a <b>proxy_apply.py</b>.</div>
  <textarea id="ta" readonly></textarea>
  <div style="margin-top:8px;text-align:right"><button onclick="document.getElementById('ta').select()">Seleccionar todo</button> <button onclick="document.getElementById('modal').style.display='none'">Cerrar</button></div>
</div></div>

<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/TransformControls.js"></script>
<script>
const R = __RECIPE__;
const T = THREE;

const cv = document.getElementById('cv');
const ren = new T.WebGLRenderer({canvas:cv, antialias:true});
ren.setPixelRatio(devicePixelRatio);
const scene = new T.Scene(); scene.background = new T.Color(0x1a1d21);
const cam = new T.PerspectiveCamera(50, 1, 0.01, 100);

const bb = R.bbox, ctr = [(bb.min[0]+bb.max[0])/2,(bb.min[1]+bb.max[1])/2,(bb.min[2]+bb.max[2])/2];
const span = Math.max(bb.max[0]-bb.min[0], bb.max[1]-bb.min[1], bb.max[2]-bb.min[2]) || 2;
cam.position.set(ctr[0]+span*1.1, ctr[1]+span*0.4, ctr[2]+span*1.6);

const orbit = new T.OrbitControls(cam, ren.domElement);
orbit.target.set(ctr[0], ctr[1], ctr[2]); orbit.enableDamping=true; orbit.dampingFactor=0.08;

scene.add(new T.AmbientLight(0xffffff,0.55));
const k=new T.DirectionalLight(0xffffff,0.8); k.position.set(2,4,3); scene.add(k);
const f=new T.DirectionalLight(0x88aaff,0.4); f.position.set(-3,2,-2); scene.add(f);

let grid = new T.GridHelper(Math.ceil(span*2), Math.ceil(span*2), 0x445566, 0x2c333d);
grid.position.set(ctr[0],0,ctr[2]); scene.add(grid);

const bg = new T.BufferGeometry();
bg.setAttribute('position', new T.BufferAttribute(new Float32Array(R.body.positions.flat()),3));
bg.setIndex(R.body.faces.flat()); bg.computeVertexNormals();
const body = new T.Mesh(bg, new T.MeshStandardMaterial({color:0xb8c0cc, roughness:0.85, metalness:0.0, side:T.DoubleSide}));
scene.add(body);
const bwire = new T.LineSegments(new T.WireframeGeometry(bg), new T.LineBasicMaterial({color:0x556070})); bwire.visible=false; scene.add(bwire);

function hsl(i,n){const c=new T.Color();c.setHSL(i/Math.max(1,n),0.6,0.58);return c;}

const handles = [], labels = [], worn = [], result = [];
const lblLayer = document.getElementById('main');
R.proxies.forEach((px,i)=>{
  const col = hsl(i, R.proxies.length), o = px.origin;
  const h = new T.Group(); h.position.set(o[0],o[1],o[2]); scene.add(h);
  h.userData.local = px.triangle.map(v=>new T.Vector3(v[0]-o[0], v[1]-o[1], v[2]-o[2]));
  h.userData.px = px; h.userData.idx = i; h.userData.moved=false;

  const sph = new T.Mesh(new T.SphereGeometry(span*0.018, 16, 12), new T.MeshBasicMaterial({color:col}));
  sph.userData.handleIdx = i; h.add(sph); h.userData.sph = sph;
  const tg = new T.BufferGeometry();
  tg.setAttribute('position', new T.BufferAttribute(new Float32Array(h.userData.local.flatMap(v=>[v.x,v.y,v.z])),3));
  tg.setIndex([0,1,2]); tg.computeVertexNormals();
  h.add(new T.Mesh(tg, new T.MeshBasicMaterial({color:col, transparent:true, opacity:0.5, side:T.DoubleSide})));
  h.add(new T.AxesHelper(span*0.06));
  handles.push(h);

  const d=document.createElement('div'); d.className='lbl'; d.textContent=px.slot;
  d.style.color='#'+col.getHexString(); lblLayer.appendChild(d); labels.push(d);

  if(px.worn){
    // (1) native-coords reference ghost (alignment target)
    const wg=new T.BufferGeometry();
    wg.setAttribute('position', new T.BufferAttribute(new Float32Array(px.worn.positions.flat()),3));
    wg.setIndex(px.worn.faces.flat()); wg.computeVertexNormals();
    const wm=new T.Mesh(wg, new T.MeshStandardMaterial({color:col, transparent:true, opacity:0.30, side:T.DoubleSide, depthWrite:false}));
    wm.visible=false; wm.userData.pi=i; scene.add(wm); worn.push(wm);
    // (2) final-result mesh: same geometry expressed relative to v0, parented to the
    // handle so it rigidly follows the proxy as you move/rotate it (assembled preview)
    const rg=new T.BufferGeometry();
    rg.setAttribute('position', new T.BufferAttribute(new Float32Array(px.worn.positions.flatMap(p=>[p[0]-o[0],p[1]-o[1],p[2]-o[2]])),3));
    rg.setIndex(px.worn.faces.flat()); rg.computeVertexNormals();
    const rm=new T.Mesh(rg, new T.MeshStandardMaterial({color:col, roughness:0.7, metalness:0.0, side:T.DoubleSide, transparent:true, opacity:0.9}));
    rm.visible=false; h.add(rm); result.push(rm);
  }
});

const giz = new T.TransformControls(cam, ren.domElement);
giz.setSize(0.9); giz.setSpace('local'); scene.add(giz);
giz.addEventListener('dragging-changed', e=>{ orbit.enabled = !e.value; });
giz.addEventListener('objectChange', ()=>{ if(selIdx>=0){ handles[selIdx].userData.moved=true; markMoved(selIdx); updateRead(); }});

let selIdx = -1, wornOn = false, resultOn = false;
function select(i){
  selIdx = i;
  document.querySelectorAll('.row').forEach((r,k)=>r.classList.toggle('sel',k===i));
  if(i<0){ giz.detach(); document.getElementById('foot').textContent='Sin selección'; updateRead(); refreshWorn(); return; }
  giz.attach(handles[i]);
  document.getElementById('foot').textContent = handles[i].userData.px.name;
  updateRead(); refreshWorn();
}
function markMoved(i){ document.querySelectorAll('.row')[i].classList.toggle('moved', handles[i].userData.moved); }
function refreshWorn(){ worn.forEach(w=>{ w.visible = wornOn && (selIdx<0 || w.userData.pi===selIdx); }); }

const list = document.getElementById('list');
R.proxies.forEach((px,i)=>{
  const row=document.createElement('div'); row.className='row';
  const wb = px.worn ? '<span class="wbadge">worn</span>' : '';
  row.innerHTML='<span class="dot" style="background:#'+hsl(i,R.proxies.length).getHexString()+'"></span>'+
                '<div><div class="nm">'+px.slot+'</div><div class="sl">'+px.name.split('\\').pop()+'</div></div>'+wb;
  row.onclick=()=>select(i); list.appendChild(row);
});

function updateRead(){
  const el=document.getElementById('read');
  if(selIdx<0){ el.innerHTML='<span class="g">Selecciona un proxy…</span>'; return; }
  const h=handles[selIdx], p=h.position, r=h.rotation, deg=x=>(x*180/Math.PI).toFixed(1);
  const w=h.userData.px.worn?('<br><span class="g">worn</span> '+h.userData.px.worn.variant):'';
  el.innerHTML='<b>'+h.userData.px.slot+'</b> <span class="g">'+h.userData.px.name.split('\\').pop()+'</span>'+w+'<br>'+
    '<span class="g">pos</span> X '+p.x.toFixed(3)+'  Y '+p.y.toFixed(3)+'  Z '+p.z.toFixed(3)+'<br>'+
    '<span class="g">rot</span> X '+deg(r.x)+'°  Y '+deg(r.y)+'°  Z '+deg(r.z)+'°';
}

const ray=new T.Raycaster(), mse=new T.Vector2();
ren.domElement.addEventListener('pointerdown', e=>{
  if(giz.dragging) return;
  const rect=ren.domElement.getBoundingClientRect();
  mse.x=((e.clientX-rect.left)/rect.width)*2-1; mse.y=-((e.clientY-rect.top)/rect.height)*2+1;
  ray.setFromCamera(mse,cam);
  const hits=ray.intersectObjects(handles.map(h=>h.userData.sph), false);
  if(hits.length) select(hits[0].object.userData.handleIdx);
});

const $=id=>document.getElementById(id);
$('bMove').onclick=()=>{giz.setMode('translate');$('bMove').classList.add('on');$('bRot').classList.remove('on');};
$('bRot').onclick =()=>{giz.setMode('rotate');  $('bRot').classList.add('on'); $('bMove').classList.remove('on');};
$('bResult').onclick=()=>{resultOn=!resultOn; result.forEach(r=>r.visible=resultOn); $('bResult').classList.toggle('on',resultOn);};
$('bWorn').onclick=()=>{wornOn=!wornOn;$('bWorn').classList.toggle('on',wornOn);refreshWorn();};
$('bBody').onclick=()=>{body.visible=!body.visible;$('bBody').classList.toggle('on',body.visible);};
$('bWire').onclick=()=>{bwire.visible=!bwire.visible;$('bWire').classList.toggle('on',bwire.visible);};
$('bGrid').onclick=()=>{grid.visible=!grid.visible;$('bGrid').classList.toggle('on',grid.visible);};
$('bReset').onclick=()=>{ if(selIdx<0)return; const h=handles[selIdx],o=h.userData.px.origin;
  h.position.set(o[0],o[1],o[2]); h.rotation.set(0,0,0); h.userData.moved=false; markMoved(selIdx); updateRead(); };
addEventListener('keydown',e=>{ if(e.key==='w'||e.key==='W')$('bMove').click(); if(e.key==='e'||e.key==='E')$('bRot').click(); });

$('bExport').onclick=()=>{
  const edits=[];
  const S=0.001, M=new T.Matrix4();
  handles.forEach(h=>{
    const px=h.userData.px; h.updateMatrixWorld(); M.extractRotation(h.matrixWorld);
    const e=M.elements;                       // columns = world dirs of local x,y,z
    const ly=[e[4],e[5],e[6]], lz=[e[8],e[9],e[10]], p=h.position;
    // canonical unambiguous triangle (see proxy_frame.py): anchor, +Y short leg,
    // +Z long leg(2x). derive_frame() recovers exactly this handle's rotation,
    // so what you align == what the engine renders. No 90/45/45 tie re-introduced.
    const nt=[[rnd(p.x),rnd(p.y),rnd(p.z)],
              [rnd(p.x+S*ly[0]),rnd(p.y+S*ly[1]),rnd(p.z+S*ly[2])],
              [rnd(p.x+2*S*lz[0]),rnd(p.y+2*S*lz[1]),rnd(p.z+2*S*lz[2])]];
    edits.push({name:px.name, lod:px.lod, point_indices:px.point_indices, new_triangle:nt, moved:h.userData.moved});
  });
  $('ta').value=JSON.stringify({model:R.model, generated_by:"proxy_viewer_canon", edits},null,2);
  $('modal').style.display='flex'; $('ta').select();
};
function rnd(x){return Math.round(x*1e6)/1e6;}

function tick(){
  requestAnimationFrame(tick); orbit.update();
  const rect=ren.domElement.getBoundingClientRect();
  handles.forEach((h,i)=>{
    const v=h.position.clone().project(cam);
    const x=(v.x*0.5+0.5)*rect.width, y=(-v.y*0.5+0.5)*rect.height, lab=labels[i];
    if(v.z<1){ lab.style.display='block'; lab.style.left=x+'px'; lab.style.top=y+'px'; } else lab.style.display='none';
  });
  ren.render(scene,cam);
}
function resize(){ const r=cv.parentElement.getBoundingClientRect(); ren.setSize(r.width,r.height,false); cam.aspect=r.width/r.height; cam.updateProjectionMatrix(); }
addEventListener('resize',resize); resize(); tick();
</script></body></html>
"""

def generate(recipe_path, out_path):
    with open(recipe_path) as f:
        recipe = json.load(f)
    html = HTML.replace("__RECIPE__", json.dumps(recipe)).replace("__MODEL__", recipe.get("model", "model"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    nworn = sum(1 for p in recipe["proxies"] if "worn" in p)
    print("wrote %s (%d bytes, %d proxies, %d worn refs)" % (out_path, len(html), len(recipe["proxies"]), nworn))

if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "proxy_recipe.json",
             sys.argv[2] if len(sys.argv) > 2 else "proxy_align_viewer.html")
