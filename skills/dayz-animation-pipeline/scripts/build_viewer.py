#!/usr/bin/env python3
"""Generate the DayZ weapon-animation authoring viewer (self-contained HTML).
Embeds the OFP2_ManSkeleton rig (mesh+skin+bones, DayZ space) + a weapon mesh.
Three.js r128 UMD (no ESM, per skill R1). SkinnedMesh + analytic 2-bone IK +
direct FK controls + keyframe timeline + JSON export."""
import json, os, sys

SCR = r'C:\Users\<you>\AppData\Local\Temp\claude\C--Users-guill-OneDrive-Documentos-DayZ-Projects\38e5dcec-fbce-4f5a-bb24-b65ca2e8ee83\scratchpad'
rig = json.load(open(os.path.join(SCR, 'rig_dayz.json')))
weap = json.load(open(os.path.join(SCR, 'weapon.json')))

tg = weap['mp'].get('trigger_axis')
grip = [sum(p[i] for p in tg) / len(tg) for i in range(3)] if tg else [0, 0, 0]
anchor = rig['anchors'].get('RightHand_Dummy', {}).get('pos', [0, 1.3, 0.2])
weap_xf = {"grip": grip, "anchor": anchor}

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCR, 'viewer.html')

HTML = r'''<!DOCTYPE html><html><head><meta charset="utf-8">
<title>DayZ Weapon Anim Authoring</title>
<style>
 html,body{margin:0;height:100%;background:#15171b;color:#dfe3e8;font:13px/1.45 system-ui,sans-serif;overflow:hidden}
 #wrap{display:flex;height:100vh}
 #side{width:300px;background:#21252b;border-right:1px solid #333;display:flex;flex-direction:column;overflow:auto}
 #side h1{font-size:13px;margin:0;padding:10px 12px;border-bottom:1px solid #333;color:#fff}
 .sec{padding:6px 12px 3px;color:#8b93a0;font-size:10px;text-transform:uppercase;letter-spacing:.06em;border-top:1px solid #2b2f37;margin-top:4px}
 .ctl{padding:4px 12px}
 .ctl label{display:block;font-size:11px;color:#aeb6c2;margin-bottom:2px}
 .ctl input[type=range]{width:100%}
 .btn{display:inline-block;background:#2f3742;color:#dfe3e8;border:1px solid #444;border-radius:5px;padding:5px 9px;margin:2px;cursor:pointer;font-size:12px}
 .btn:hover{background:#3a4350}.btn.on{background:#3f6bd6;border-color:#3f6bd6;color:#fff}
 #main{flex:1;position:relative}
 #cv{display:block;width:100%;height:100%}
 #top{position:absolute;top:8px;left:8px;display:flex;gap:5px;flex-wrap:wrap;max-width:70%}
 #tl{position:absolute;bottom:0;left:0;right:0;background:rgba(20,22,26,.94);border-top:1px solid #333;padding:8px 10px}
 #tl .kfs{display:flex;gap:3px;flex-wrap:wrap;margin:5px 0;align-items:center}
 .kf{background:#34507f;border:1px solid #4a6aa0;border-radius:3px;padding:2px 7px;cursor:pointer;font-size:11px}
 .kf.cur{background:#5fd38a;color:#0a0a0a;border-color:#5fd38a}
 #scrub{width:100%}
 #err{position:absolute;top:8px;right:8px;max-width:40%;color:#ff8080;font-size:11px;white-space:pre-wrap}
 #info{position:absolute;bottom:78px;left:8px;font-size:11px;color:#9aa3b0;background:rgba(20,22,26,.8);padding:5px 8px;border-radius:5px}
 textarea{width:100%;height:60px;background:#15171b;color:#9fe6bf;border:1px solid #333;font:11px monospace;box-sizing:border-box}
</style></head><body>
<div id="wrap">
 <div id="side">
  <h1>Weapon Anim Authoring<br><span style="color:#8b93a0;font-weight:400;font-size:10px">OFP2_ManSkeleton &middot; __WEAPNAME__</span></h1>
  <div class="sec">Gizmo target</div>
  <div class="ctl" id="targets"></div>
  <div class="ctl"><span class="btn on" id="mMove">Mover</span><span class="btn" id="mRot">Rotar</span><span class="btn" id="mWeapon">Arma sigue R.Hand</span></div>
  <div class="sec">Controles directos</div>
  <div class="ctl"><label>Inclinacion torso <span id="vLean">0</span></label><input type="range" id="sLean" min="-30" max="60" value="0"></div>
  <div class="ctl"><label>Muneca Izq (roll) <span id="vWL">0</span></label><input type="range" id="sWL" min="-90" max="90" value="0"></div>
  <div class="ctl"><label>Muneca Dcha (roll) <span id="vWR">0</span></label><input type="range" id="sWR" min="-90" max="90" value="0"></div>
  <div class="ctl"><label>Dedos Izq (curl) <span id="vFL">0</span></label><input type="range" id="sFL" min="0" max="100" value="0"></div>
  <div class="ctl"><label>Dedos Dcha (curl) <span id="vFR">0</span></label><input type="range" id="sFR" min="0" max="100" value="0"></div>
  <div class="ctl"><label>Codo Izq (giro) <span id="vEL">0</span></label><input type="range" id="sEL" min="-100" max="100" value="0"></div>
  <div class="ctl"><label>Codo Dcho (giro) <span id="vER">0</span></label><input type="range" id="sER" min="-100" max="100" value="0"></div>
  <div class="ctl"><label>Cabeza pitch <span id="vHP">0</span></label><input type="range" id="sHP" min="-40" max="40" value="0"></div>
  <div class="ctl"><label>Cabeza yaw <span id="vHY">0</span></label><input type="range" id="sHY" min="-60" max="60" value="0"></div>
  <div class="sec">Vista</div>
  <div class="ctl"><span class="btn on" id="bMesh">Cuerpo</span><span class="btn on" id="bBones">Huesos</span><span class="btn on" id="bWeap">Arma</span><span class="btn" id="bWire">Wire</span></div>
  <div class="sec">Export</div>
  <div class="ctl"><span class="btn" id="bExport">Generar JSON</span><span class="btn" id="bDl">Descargar</span></div>
  <div class="ctl"><textarea id="exp" readonly placeholder="JSON de la animacion (keyframes -> bone local quats)"></textarea></div>
 </div>
 <div id="main">
  <canvas id="cv"></canvas>
  <div id="top">
   <span class="btn" id="bReady">Pose lista</span>
   <span class="btn" id="bReset">Rest (T-pose)</span>
  </div>
  <div id="err"></div>
  <div id="info"></div>
  <div id="tl">
   <div style="display:flex;gap:6px;align-items:center">
    <span class="btn" id="bPlay">&#9654; Play</span>
    <span class="btn" id="bAdd">+ Keyframe</span>
    <span class="btn" id="bDel">&times; Borrar</span>
    <span style="font-size:11px;color:#9aa3b0">FPS</span><input type="number" id="fps" value="30" min="1" max="60" style="width:46px;background:#15171b;color:#dfe;border:1px solid #333">
    <span style="font-size:11px;color:#9aa3b0">frame <b id="curf">0</b>/<b id="maxf">0</b></span>
   </div>
   <div class="kfs" id="kfs"></div>
   <input type="range" id="scrub" min="0" max="0" value="0" step="1">
  </div>
 </div>
</div>
__LIBS__
<script>
const RIG = __RIG__;
const WEAP = __WEAP__;
const WXF = __WXF__;
const T = THREE;
function fail(m){var e=document.getElementById('err');if(e)e.textContent='ERROR: '+m;console.error(m);}
window.addEventListener('error',e=>fail(e.message+' @'+e.lineno));
let scene,cam,ren,orbit,tc;
let bones={}, boneArr=[], rest={}, skinned, weaponGrp, boneLines, jointGrp;
let targets={}, activeTarget='rhand', weaponFollow=false;
let keyframes=[], curFrame=0, playing=false;
const D2R=Math.PI/180;
const restLocalQ={}; RIG.bones.forEach(b=>restLocalQ[b.name]=new T.Quaternion(b.quat[0],b.quat[1],b.quat[2],b.quat[3]));

const cv=document.getElementById('cv');
ren=new T.WebGLRenderer({canvas:cv,antialias:true,preserveDrawingBuffer:true});
ren.setPixelRatio(devicePixelRatio);
scene=new T.Scene(); scene.background=new T.Color(0x15171b);
cam=new T.PerspectiveCamera(45,1,0.01,100);
cam.position.set(1.3,1.5,1.9);
orbit=new T.OrbitControls(cam,ren.domElement); orbit.target.set(0,1.1,0); orbit.enableDamping=true;
scene.add(new T.AmbientLight(0xffffff,0.7));
const dl=new T.DirectionalLight(0xffffff,0.9); dl.position.set(2,4,3); scene.add(dl);
const dl2=new T.DirectionalLight(0x90b0ff,0.35); dl2.position.set(-3,2,-2); scene.add(dl2);
const grid=new T.GridHelper(3,30,0x445566,0x262c34); scene.add(grid);

function buildSkeleton(){
  RIG.bones.forEach(b=>{
    const bn=new T.Bone(); bn.name=b.name;
    bn.position.set(b.pos[0],b.pos[1],b.pos[2]);
    bn.quaternion.set(b.quat[0],b.quat[1],b.quat[2],b.quat[3]);
    bones[b.name]=bn; boneArr.push(bn);
  });
  RIG.bones.forEach(b=>{ if(b.parent && bones[b.parent]) bones[b.parent].add(bones[b.name]); });
  return RIG.bones.filter(b=>!b.parent).map(b=>bones[b.name]);
}
const roots=buildSkeleton();

function buildSkinned(){
  const g=new T.BufferGeometry();
  const pos=new Float32Array(RIG.mesh.verts.length*3);
  RIG.mesh.verts.forEach((v,i)=>{pos[i*3]=v[0];pos[i*3+1]=v[1];pos[i*3+2]=v[2];});
  g.setAttribute('position',new T.BufferAttribute(pos,3));
  g.setIndex(RIG.mesh.faces.flat());
  const si=new Uint16Array(RIG.mesh.verts.length*4), sw=new Float32Array(RIG.mesh.verts.length*4);
  RIG.mesh.skin.forEach((s,i)=>{ for(let k=0;k<4;k++){ si[i*4+k]=s[k]?s[k][0]:0; sw[i*4+k]=s[k]?s[k][1]:0; } });
  g.setAttribute('skinIndex',new T.Uint16BufferAttribute(si,4));
  g.setAttribute('skinWeight',new T.Float32BufferAttribute(sw,4));
  g.computeVertexNormals();
  const mat=new T.MeshStandardMaterial({color:0x9aa6b4,roughness:0.85,metalness:0.0,skinning:true,side:T.DoubleSide});
  const m=new T.SkinnedMesh(g,mat);
  m.frustumCulled=false;
  roots.forEach(r=>m.add(r));
  const skel=new T.Skeleton(boneArr);
  m.bind(skel);
  scene.add(m);
  return m;
}
skinned=buildSkinned();

scene.updateMatrixWorld(true);
boneArr.forEach(b=>{
  const p=new T.Vector3(), q=new T.Quaternion(), s=new T.Vector3();
  b.matrixWorld.decompose(p,q,s);
  rest[b.name]={pos:p.clone(),quat:q.clone()};
});

function buildWeapon(){
  const grp=new T.Group();
  const g=new T.BufferGeometry();
  const pos=new Float32Array(WEAP.verts.length*3);
  WEAP.verts.forEach((v,i)=>{pos[i*3]=v[0];pos[i*3+1]=v[1];pos[i*3+2]=v[2];});
  g.setAttribute('position',new T.BufferAttribute(pos,3));
  g.setIndex(WEAP.faces.flat()); g.computeVertexNormals();
  const mat=new T.MeshStandardMaterial({color:0x3a3f46,roughness:0.6,metalness:0.3,side:T.DoubleSide});
  const mesh=new T.Mesh(g,mat);
  mesh.position.set(-WXF.grip[0],-WXF.grip[1],-WXF.grip[2]);
  grp.add(mesh);
  grp.position.set(WXF.anchor[0],WXF.anchor[1],WXF.anchor[2]);
  scene.add(grp);
  return grp;
}
weaponGrp=buildWeapon();

jointGrp=new T.Group(); scene.add(jointGrp);
const jmat=new T.MeshBasicMaterial({color:0xffe000});
boneArr.forEach(b=>{ const s=new T.Mesh(new T.SphereGeometry(0.008,8,6),jmat); jointGrp.add(s); b.userData.dot=s; });
boneLines=new T.LineSegments(new T.BufferGeometry(),new T.LineBasicMaterial({color:0x33bbff})); scene.add(boneLines);
function updateBoneViz(){
  const pts=[]; const wp=new T.Vector3(), pp=new T.Vector3();
  boneArr.forEach(b=>{
    b.getWorldPosition(wp); b.userData.dot.position.copy(wp);
    if(b.parent && b.parent.isBone){ b.parent.getWorldPosition(pp); pts.push(pp.x,pp.y,pp.z,wp.x,wp.y,wp.z); }
  });
  boneLines.geometry.setAttribute('position',new T.Float32BufferAttribute(pts,3));
  boneLines.geometry.attributes.position.needsUpdate=true;
}

function mkTarget(name,colour,pos){
  const o=new T.Mesh(new T.SphereGeometry(0.03,12,10),new T.MeshBasicMaterial({color:colour,transparent:true,opacity:0.55}));
  o.position.copy(pos); o.name=name; scene.add(o); targets[name]=o; return o;
}
mkTarget('rhand',0xff5d5d,rest['RightHand'].pos);
mkTarget('lhand',0x5d8cff,rest['LeftHand'].pos);
mkTarget('rfoot',0xffa040,rest['RightFoot'].pos);
mkTarget('lfoot',0x40c0ff,rest['LeftFoot'].pos);
mkTarget('head',0x90ff90,new T.Vector3(rest['Head'].pos.x,rest['Head'].pos.y,rest['Head'].pos.z+0.6));

const _v=new T.Vector3(),_a=new T.Vector3(),_b=new T.Vector3();
function worldQuat(b){const q=new T.Quaternion();b.getWorldQuaternion(q);return q;}
function worldPos(b){const p=new T.Vector3();b.getWorldPosition(p);return p;}
function aimBone(bone,childRestName,desiredChildWorld){
  const bp=worldPos(bone);
  const restChildW=rest[childRestName].pos, restBoneW=rest[bone.name].pos;
  const restDir=_a.copy(restChildW).sub(restBoneW).normalize();
  const newDir=_b.copy(desiredChildWorld).sub(bp).normalize();
  const dq=new T.Quaternion().setFromUnitVectors(restDir,newDir);
  const desiredWorld=dq.multiply(rest[bone.name].quat);
  const pq=bone.parent?worldQuat(bone.parent):new T.Quaternion();
  bone.quaternion.copy(pq.invert().multiply(desiredWorld));
  bone.updateMatrixWorld(true);
}
function solveLimb(upName,loName,endName,targetW,basePole,swivelDeg){
  const up=bones[upName];
  const upW=worldPos(up);
  const l1=rest[loName].pos.distanceTo(rest[upName].pos);
  const l2=rest[endName].pos.distanceTo(rest[loName].pos);
  const toT=_v.copy(targetW).sub(upW); let d=toT.length();
  d=Math.max(Math.abs(l1-l2)+1e-4,Math.min(d,l1+l2-1e-4));
  const cosA=(l1*l1+d*d-l2*l2)/(2*l1*d);
  const a=Math.acos(Math.max(-1,Math.min(1,cosA)));
  const fwd=toT.clone().normalize();
  let p=basePole.clone().sub(fwd.clone().multiplyScalar(basePole.dot(fwd)));
  if(p.length()<1e-4) p=new T.Vector3(0,1,0); else p.normalize();
  if(swivelDeg) p.applyAxisAngle(fwd, swivelDeg*Math.PI/180);
  const elbow=upW.clone().add(fwd.clone().multiplyScalar(l1*Math.cos(a))).add(p.multiplyScalar(l1*Math.sin(a)));
  aimBone(bones[upName],loName,elbow);
  aimBone(bones[loName],endName,targetW);
}
function solveArms(){
  solveLimb('RightArm','RightForeArm','RightHand',targets['rhand'].position,new T.Vector3(-0.35,-1,-0.35),st.er||0);
  solveLimb('LeftArm','LeftForeArm','LeftHand',targets['lhand'].position,new T.Vector3(0.35,-1,-0.35),st.el||0);
}
function solveLegs(){
  solveLimb('RightUpLeg','RightLeg','RightFoot',targets['rfoot'].position,new T.Vector3(0,0.2,1),0);
  solveLimb('LeftUpLeg','LeftLeg','LeftFoot',targets['lfoot'].position,new T.Vector3(0,0.2,1),0);
}
// barrel(konec->usti) -> world +Z, weapon up -> world +Y
function boreForwardQuat(){
  const u=WEAP.mp['usti hlavne'], k=WEAP.mp['konec hlavne'];
  if(!u||!k) return new T.Quaternion();
  const ez=new T.Vector3(u[0][0],u[0][1],u[0][2]).sub(new T.Vector3(k[0][0],k[0][1],k[0][2])).normalize();
  let ey=new T.Vector3(0,1,0).sub(ez.clone().multiplyScalar(ez.y)); if(ey.length()<1e-3) ey=new T.Vector3(0,0,1); ey.normalize();
  const ex=new T.Vector3().crossVectors(ey,ez).normalize();
  const m=new T.Matrix4().makeBasis(ex,ey,ez); m.transpose();
  return new T.Quaternion().setFromRotationMatrix(m);
}
function poseIdle(){
  const q=boreForwardQuat();
  q.premultiply(new T.Quaternion().setFromAxisAngle(new T.Vector3(1,0,0),-8*Math.PI/180)); // slight muzzle-down
  weaponGrp.quaternion.copy(q);
  const Pp=new T.Vector3(-0.06,1.02,0.32); weaponGrp.position.copy(Pp); weaponGrp.updateMatrixWorld(true);
  targets['rhand'].position.copy(Pp);
  const u=WEAP.mp['usti hlavne'], k=WEAP.mp['konec hlavne']; let hg;
  if(u&&k){
    const g=new T.Vector3(WXF.grip[0],WXF.grip[1],WXF.grip[2]);
    const hgLocal=new T.Vector3(k[0][0],k[0][1],k[0][2]).lerp(new T.Vector3(u[0][0],u[0][1],u[0][2]),0.30);
    hg=weaponGrp.localToWorld(hgLocal.sub(g));
  } else hg=Pp.clone().add(new T.Vector3(0,0,0.28));
  // clamp support-hand target into left-arm reach so the elbow always bends
  const lsh=rest['LeftArm'].pos;
  const ll1=rest['LeftForeArm'].pos.distanceTo(rest['LeftArm'].pos);
  const ll2=rest['LeftHand'].pos.distanceTo(rest['LeftForeArm'].pos);
  const maxR=(ll1+ll2)*0.90, dd=hg.distanceTo(lsh);
  if(dd>maxR) hg=lsh.clone().add(hg.clone().sub(lsh).multiplyScalar(maxR/dd));
  targets['lhand'].position.copy(hg);
  targets['rfoot'].position.copy(rest['RightFoot'].pos);
  targets['lfoot'].position.copy(rest['LeftFoot'].pos);
  targets['head'].position.set(rest['Head'].pos.x,rest['Head'].pos.y,rest['Head'].pos.z+0.6);
  st={lean:0,wl:0,wr:0,fl:0,fr:0,hp:0,hy:0,el:0,er:0}; syncSliders(); applyPose();
}

let st={lean:0,wl:0,wr:0,fl:0,fr:0,hp:0,hy:0,el:0,er:0};
function addLocal(name,axis,deg){const b=bones[name];if(!b||!deg)return;b.quaternion.multiply(new T.Quaternion().setFromAxisAngle(axis,deg*D2R));}
const fingersL=['LeftHandIndex1','LeftHandIndex2','LeftHandIndex3','LeftHandMiddle1','LeftHandMiddle2','LeftHandMiddle3','LeftHandRing1','LeftHandRing2','LeftHandRing3','LeftHandPinky1','LeftHandPinky2','LeftHandPinky3'];
const fingersR=fingersL.map(n=>n.replace('Left','Right'));
function applyFK(){
  ['Spine','Spine1','Spine2','Spine3'].forEach(n=>addLocal(n,new T.Vector3(1,0,0),st.lean/4));
  addLocal('LeftHand',new T.Vector3(0,1,0),st.wl);
  addLocal('RightHand',new T.Vector3(0,1,0),st.wr);
  fingersL.forEach(n=>addLocal(n,new T.Vector3(0,0,1),-st.fl*0.6));
  fingersR.forEach(n=>addLocal(n,new T.Vector3(0,0,1),-st.fr*0.6));
  addLocal('Neck',new T.Vector3(1,0,0),st.hp*0.4); addLocal('Head',new T.Vector3(1,0,0),st.hp*0.6);
  addLocal('Neck',new T.Vector3(0,1,0),st.hy*0.4); addLocal('Head',new T.Vector3(0,1,0),st.hy*0.6);
}

function applyPose(){
  boneArr.forEach(b=>b.quaternion.copy(restLocalQ[b.name]));
  scene.updateMatrixWorld(true);
  solveLegs(); solveArms();
  applyFK();
  scene.updateMatrixWorld(true);
  if(weaponFollow){
    const h=bones['RightHand'];
    weaponGrp.position.copy(worldPos(h)); weaponGrp.quaternion.copy(worldQuat(h));
  }
  updateBoneViz();
}

tc=new T.TransformControls(cam,ren.domElement);
tc.addEventListener('dragging-changed',e=>orbit.enabled=!e.value);
tc.addEventListener('objectChange',()=>{applyPose();});
scene.add(tc);
function setActive(name){activeTarget=name;tc.attach(name==='weapon'?weaponGrp:targets[name]);
  document.querySelectorAll('#targets .btn').forEach(x=>x.classList.toggle('on',x.dataset.t===name));}
const tnames=[['rhand','R.Hand'],['lhand','L.Hand'],['rfoot','R.Foot'],['lfoot','L.Foot'],['head','Cabeza'],['weapon','Arma']];
const td=document.getElementById('targets');
tnames.forEach(p=>{const s=document.createElement('span');s.className='btn';s.dataset.t=p[0];s.textContent=p[1];s.onclick=()=>setActive(p[0]);td.appendChild(s);});
setActive('rhand');

function poseReady(){
  const a=WXF.anchor;
  weaponGrp.position.set(a[0],a[1],a[2]); weaponGrp.quaternion.identity();
  targets['rhand'].position.set(a[0],a[1],a[2]);
  targets['lhand'].position.set(a[0]+0.18, a[1]-0.02, a[2]-0.18);
  targets['rfoot'].position.copy(rest['RightFoot'].pos);
  targets['lfoot'].position.copy(rest['LeftFoot'].pos);
  targets['head'].position.set(rest['Head'].pos.x,rest['Head'].pos.y,rest['Head'].pos.z+0.6);
  applyPose();
}
function poseRest(){
  boneArr.forEach(b=>b.quaternion.copy(restLocalQ[b.name]));
  const map={rhand:'RightHand',lhand:'LeftHand',rfoot:'RightFoot',lfoot:'LeftFoot'};
  Object.keys(map).forEach(k=>targets[k].position.copy(rest[map[k]].pos));
  targets['head'].position.set(rest['Head'].pos.x,rest['Head'].pos.y,rest['Head'].pos.z+0.6);
  st={lean:0,wl:0,wr:0,fl:0,fr:0,hp:0,hy:0,el:0,er:0}; syncSliders();
  scene.updateMatrixWorld(true); updateBoneViz();
}

function captureState(){return {
  rhand:targets['rhand'].position.toArray(), lhand:targets['lhand'].position.toArray(),
  rfoot:targets['rfoot'].position.toArray(), lfoot:targets['lfoot'].position.toArray(),
  head:targets['head'].position.toArray(),
  weapon:{p:weaponGrp.position.toArray(),q:weaponGrp.quaternion.toArray()},
  st:Object.assign({},st)};}
function applyState(s){
  targets['rhand'].position.fromArray(s.rhand);targets['lhand'].position.fromArray(s.lhand);
  targets['rfoot'].position.fromArray(s.rfoot);targets['lfoot'].position.fromArray(s.lfoot);
  targets['head'].position.fromArray(s.head);
  weaponGrp.position.fromArray(s.weapon.p);weaponGrp.quaternion.fromArray(s.weapon.q);
  st=Object.assign({},s.st); syncSliders(); applyPose();
}
function lerpState(a,b,t){
  const L=(x,y)=>x.map((v,i)=>v+(y[i]-v)*t);
  const qa=new T.Quaternion().fromArray(a.weapon.q), qb=new T.Quaternion().fromArray(b.weapon.q);
  const qm=qa.clone().slerp(qb,t);
  const ls={}; for(const k in a.st) ls[k]=a.st[k]+(b.st[k]-a.st[k])*t;
  return {rhand:L(a.rhand,b.rhand),lhand:L(a.lhand,b.lhand),rfoot:L(a.rfoot,b.rfoot),lfoot:L(a.lfoot,b.lfoot),
    head:L(a.head,b.head),weapon:{p:L(a.weapon.p,b.weapon.p),q:qm.toArray()},st:ls};}
function stateAtFrame(f){
  if(!keyframes.length) return null;
  if(f<=keyframes[0].frame) return keyframes[0].state;
  if(f>=keyframes[keyframes.length-1].frame) return keyframes[keyframes.length-1].state;
  for(let i=0;i<keyframes.length-1;i++){
    const A=keyframes[i],B=keyframes[i+1];
    if(f>=A.frame&&f<=B.frame){const t=(f-A.frame)/(B.frame-A.frame||1);return lerpState(A.state,B.state,t);}
  }
  return keyframes[0].state;
}
function addKeyframe(){
  const f=curFrame;
  keyframes=keyframes.filter(k=>k.frame!==f);
  keyframes.push({frame:f,state:captureState()});
  keyframes.sort((a,b)=>a.frame-b.frame); renderKfs(); updateMax();
}
function delKeyframe(){keyframes=keyframes.filter(k=>k.frame!==curFrame);renderKfs();}
function renderKfs(){
  const c=document.getElementById('kfs'); c.innerHTML='';
  keyframes.forEach(k=>{const e=document.createElement('span');e.className='kf'+(k.frame===curFrame?' cur':'');e.textContent='f'+k.frame;e.onclick=()=>{gotoFrame(k.frame);};c.appendChild(e);});
}
function updateMax(){const mx=Math.max(0,...keyframes.map(k=>k.frame));document.getElementById('scrub').max=mx;document.getElementById('maxf').textContent=mx;}
function gotoFrame(f){curFrame=f;document.getElementById('scrub').value=f;document.getElementById('curf').textContent=f;
  const s=stateAtFrame(f); if(s) applyState(s); renderKfs();}

function syncSliders(){sLean.value=st.lean;sWL.value=st.wl;sWR.value=st.wr;sFL.value=st.fl;sFR.value=st.fr;sHP.value=st.hp;sHY.value=st.hy;
  vLean.textContent=st.lean;vWL.textContent=st.wl;vWR.textContent=st.wr;vFL.textContent=st.fl;vFR.textContent=st.fr;vHP.textContent=st.hp;vHY.textContent=st.hy;sEL.value=st.el;sER.value=st.er;vEL.textContent=st.el;vER.textContent=st.er;}
function sl(id,key,disp){const e=document.getElementById(id);e.oninput=()=>{st[key]=+e.value;document.getElementById(disp).textContent=e.value;applyPose();};}
sl('sLean','lean','vLean');sl('sWL','wl','vWL');sl('sWR','wr','vWR');sl('sFL','fl','vFL');sl('sFR','fr','vFR');sl('sHP','hp','vHP');sl('sHY','hy','vHY');sl('sEL','el','vEL');sl('sER','er','vER');

function onbtn(id,fn){document.getElementById(id).onclick=fn;}
onbtn('mMove',()=>{tc.setMode('translate');mMove.classList.add('on');mRot.classList.remove('on');});
onbtn('mRot',()=>{tc.setMode('rotate');mRot.classList.add('on');mMove.classList.remove('on');});
onbtn('mWeapon',()=>{weaponFollow=!weaponFollow;document.getElementById('mWeapon').classList.toggle('on',weaponFollow);applyPose();});
onbtn('bReady',poseIdle); onbtn('bReset',poseRest);
onbtn('bAdd',addKeyframe); onbtn('bDel',delKeyframe);
onbtn('bPlay',()=>{playing=!playing;document.getElementById('bPlay').classList.toggle('on',playing);});
document.getElementById('scrub').oninput=e=>gotoFrame(+e.target.value);
function tog(id,fn){const b=document.getElementById(id);let on=b.classList.contains('on');b.onclick=()=>{on=!on;b.classList.toggle('on',on);fn(on);};}
tog('bMesh',v=>skinned.visible=v);tog('bBones',v=>{boneLines.visible=v;jointGrp.visible=v;});
tog('bWeap',v=>weaponGrp.visible=v);tog('bWire',v=>skinned.material.wireframe=v);

function buildExport(){
  const fps=+document.getElementById('fps').value||30;
  const maxf=Math.max(0,...keyframes.map(k=>k.frame));
  const frames=[];
  for(let f=0;f<=maxf;f++){
    const s=stateAtFrame(f); if(s)applyState(s);
    const q={}; boneArr.forEach(b=>{q[b.name]=[+b.quaternion.x.toFixed(6),+b.quaternion.y.toFixed(6),+b.quaternion.z.toFixed(6),+b.quaternion.w.toFixed(6)];});
    frames.push({frame:f,bones:q});
  }
  return {format:'dayz-anim-authoring/v1',space:'rig-local-quat',fps:fps,bone_order:RIG.bone_order,
    weapon:WEAP.name,keyframes:keyframes.map(k=>k.frame),frames:frames};
}
let lastExport=null;
onbtn('bExport',()=>{lastExport=buildExport();const j=JSON.stringify(lastExport);
  document.getElementById('exp').value=j.length>4000?j.slice(0,4000)+' ...['+j.length+' chars]':j;
  document.getElementById('info').textContent='Export: '+lastExport.frames.length+' frames, '+keyframes.length+' keyframes';});
onbtn('bDl',()=>{if(!lastExport)lastExport=buildExport();const blob=new Blob([JSON.stringify(lastExport)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='weapon_anim.json';a.click();});

function setCam(px,py,pz,tx,ty,tz){cam.position.set(px,py,pz);orbit.target.set(tx,ty,tz);orbit.update();}
function previewMode(on){Object.values(targets).forEach(t=>t.visible=!on);if(on)tc.detach();else setActive(activeTarget);}
window.__VIEWER__={buildExport,addKeyframe,gotoFrame,poseReady,poseIdle,poseRest,keyframes:()=>keyframes,scene,cam,orbit,bones,targets,rest,applyPose,weaponGrp,skinned,jointGrp,boneLines,setCam,previewMode,
  setSlider:(k,v)=>{st[k]=v;syncSliders();applyPose();}};

let last=0;
function tick(ts){
  requestAnimationFrame(tick);
  if(playing&&keyframes.length>1){
    const fps=+document.getElementById('fps').value||30; const mx=keyframes[keyframes.length-1].frame;
    if(ts-last>1000/fps){last=ts;curFrame=(curFrame+1)%(mx+1);gotoFrame(curFrame);}
  }
  orbit.update(); ren.render(scene,cam);
}
function resize(){const r=cv.parentElement.getBoundingClientRect();ren.setSize(r.width,r.height,false);cam.aspect=r.width/r.height;cam.updateProjectionMatrix();}
addEventListener('resize',resize); resize();
poseIdle(); updateBoneViz(); tick(0);
document.getElementById('info').textContent='Rig OFP2_ManSkeleton + '+WEAP.name+' cargados. Arrastra los gizmos, ajusta sliders, marca keyframes.';
</script></body></html>'''

LIBDIR = os.path.join(SCR, 'libs')
libs_html = ''
for lib in ('three.min.js', 'OrbitControls.js', 'TransformControls.js'):
    code = open(os.path.join(LIBDIR, lib), encoding='utf-8').read()
    libs_html += '<script>\n' + code + '\n</script>\n'
html = (HTML.replace('__LIBS__', libs_html)
            .replace('__RIG__', json.dumps(rig))
            .replace('__WEAP__', json.dumps(weap))
            .replace('__WXF__', json.dumps(weap_xf))
            .replace('__WEAPNAME__', weap['name']))
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
with open(OUT, encoding='utf-8') as f:
    back = f.read()
assert back == html, 'read-after-write mismatch'
assert back.rstrip().endswith('</html>'), 'truncated'
print('VIEWER WROTE', OUT, len(html), 'bytes')
