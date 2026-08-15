# Cookbook B — wheelPresent=0

> Familia B. Este cuerpo se movió sin reescritura en CAMBIO-1; las notas de estado y las rutas permanecen tal como estaban en el origen.

<!-- MOVED-EXACT source="dayz-vehicles/SKILL.md:446" sha256="F95C63380857A0FD89039274C0070BE2874F5D3DED6A63B87AFC125E21CAD788" -->
3. **Geometry LOD carries named property `class=vehicle` — REQUIRED PARITY (6/6 vanilla wheeled
   vehicles have it; cheap to replicate) but REFUTED as the wheel-sim gate:** deploying it alone left
   `wheelPresent=0` (LFQuad in-game 2026-05-27). The actual wheel-sim gate is the `CfgSlots.selection`
   ↔ FireGeometry selection wiring (SP-017 — see the FireGeo wheel-slot rule in
   `vehicle-structural-parity.md` / `dayz-p3d-audit`). Symptom either way: `WheelCountPresent()==0`
   while `WheelCount()==4`, no traction/spin, body sinks/bounces, **no RPT error**. → SP-027 /
   `vehicle-structural-parity.md`.
<!-- END MOVED-EXACT -->
