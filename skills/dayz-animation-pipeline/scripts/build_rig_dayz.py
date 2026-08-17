import json, os, numpy as np
SCR=r'C:\Users\<you>\AppData\Local\Temp\claude\C--Users-guill-OneDrive-Documentos-DayZ-Projects\38e5dcec-fbce-4f5a-bb24-b65ca2e8ee83\scratchpad'
rig=json.load(open(os.path.join(SCR,'rig_raw.json')))
emp=json.load(open(os.path.join(SCR,'empties_armworld.json')))

def RT(m):
    A=np.array(m,dtype=float); return A[:3,:3].copy(), A[:3,3].copy()

# --- alignment: bone arm-world (cm,T-pose) -> mesh-world (m). uniform s + translate ---
bw={b['name']:RT(b['world']) for b in rig['bones']}
bpts=np.array([t for _,t in bw.values()])
verts=np.array(rig['mesh']['verts'])
# scale from X half-width (hands), robust
s = (verts[:,0].max()-verts[:,0].min()) / (bpts[:,0].max()-bpts[:,0].min())
# translate to align bbox centers per axis
t = verts.mean(0) - s*bpts.mean(0)
# refine Z/Y by aligning mins (feet on floor, front align): use min alignment on Z
t[2] = verts[:,2].min() - s*bpts[:,2].min()
print("align scale=%.6f  translate=%s"%(s,[round(x,4) for x in t]))

# Fm: Blender world Z-up -> DayZ Y-up: x'=x, y'=z, z'=-y
Rf=np.array([[1,0,0],[0,0,1],[0,-1,0]],dtype=float)
def to_dayz(R,tr):
    Rfin=Rf@R; tfin=Rf@(s*tr+t); return Rfin,tfin
def pt_dayz(p):  # point only
    p=np.array(p,float); return Rf@(s*p+t)

def quat(R):
    tr=np.trace(R)
    if tr>0:
        q=0.5/np.sqrt(tr+1.0); w=0.25/q; x=(R[2,1]-R[1,2])*q; y=(R[0,2]-R[2,0])*q; z=(R[1,0]-R[0,1])*q
    else:
        i=int(np.argmax([R[0,0],R[1,1],R[2,2]]))
        if i==0: d=2*np.sqrt(1+R[0,0]-R[1,1]-R[2,2]); w=(R[2,1]-R[1,2])/d;x=0.25*d;y=(R[0,1]+R[1,0])/d;z=(R[0,2]+R[2,0])/d
        elif i==1: d=2*np.sqrt(1+R[1,1]-R[0,0]-R[2,2]); w=(R[0,2]-R[2,0])/d;x=(R[0,1]+R[1,0])/d;y=0.25*d;z=(R[1,2]+R[2,1])/d
        else: d=2*np.sqrt(1+R[2,2]-R[0,0]-R[1,1]); w=(R[1,0]-R[0,1])/d;x=(R[0,2]+R[2,0])/d;y=(R[1,2]+R[2,1])/d;z=0.25*d
    v=np.array([x,y,z,w]); return list((v/np.linalg.norm(v)).round(6))

# bone final world (rigid, DayZ)
order=[b['name'] for b in rig['bones']]
parent={b['name']:b['parent'] for b in rig['bones']}
fw={}
for b in rig['bones']:
    R,tr=bw[b['name']]; fw[b['name']]=to_dayz(R,tr)
def inv(R,tt): Rt=R.T; return Rt, -Rt@tt
bones_out=[]
for nm in order:
    par=parent[nm]; R,tt=fw[nm]
    if par is None: Rl,tl=R,tt
    else:
        Rp,tp=fw[par]; Ri,ti=inv(Rp,tp); Rl=Ri@R; tl=Ri@tt+ti
    bones_out.append({"name":nm,"parent":par,"pos":[round(float(x),6) for x in tl],"quat":quat(Rl),
                      "world_pos":[round(float(x),5) for x in tt]})

# mesh -> DayZ (verts already mesh-world meters; only Fm)
mverts=[[round(float(x),5) for x in (Rf@np.array(v))] for v in rig['mesh']['verts']]
name2idx={nm:i for i,nm in enumerate(order)}
skin=[]
for w in rig['mesh']['weights']:
    pr=[(name2idx.get(n,0),wt) for n,wt in w if n in name2idx][:4]
    while len(pr)<4: pr.append((0,0.0))
    ssum=sum(wt for _,wt in pr) or 1.0
    skin.append([[i,round(wt/ssum,5)] for i,wt in pr])

anchors={}
for k,m in emp.items():
    R,tr=RT(m); Rd,td=to_dayz(R,tr); anchors[k]={"pos":[round(float(x),5) for x in td],"quat":quat(Rd)}

out={"space":"dayz_yup_meters","align":{"scale":s,"translate":list(t)},"bone_order":order,
     "bones":bones_out,"anchors":anchors,"mesh":{"verts":mverts,"faces":rig['mesh']['faces'],"skin":skin}}
json.dump(out,open(os.path.join(SCR,'rig_dayz.json'),'w'))

# sanity: key bone world positions (DayZ) vs mesh bbox
mv=np.array(mverts); print("mesh DayZ bbox min",mv.min(0).round(3).tolist(),"max",mv.max(0).round(3).tolist())
bd={b['name']:b['world_pos'] for b in bones_out}
for k in ["Head","Pelvis","RightHand","LeftHand","RightFoot","LeftFoot","Neck"]:
    print("  bone %-10s DayZ world=%s"%(k,[round(x,3) for x in bd[k]]))
for k in ["RightHand_Dummy","Weapon_Root","LeftHand_Dummy"]:
    if k in anchors: print("  anchor %-16s %s"%(k,[round(x,3) for x in anchors[k]['pos']]))
