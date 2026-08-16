# Audit escalation — severity discipline + multi-agent isolation

> Extracted from dayz-mod-workflow/SKILL.md 2026-07-07 (F3).
>
> Sectioned §8 (severity inflation in audit reports) and §9 (multi-agent audit context isolation) from the core SKILL.md. These OVERLAP the `rigorous-data-audit` skill (the operational 7-step, multi-auditor workflow) — use that skill to RUN a data-critical audit; this file is the workflow-protocol note on labelling severity and keeping parallel auditors independent.

---

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration] -->
## 8. SEVERITY INFLATION IN AUDIT REPORTS (added 2026-05-15)

Patrón observado en audits de LFPowerGrid: etiquetar como `P1 — crash`
hallazgos que en realidad son `P2 — VM exception recuperable, server sigue
corriendo`. Causa: extrapolación de mensaje de log (`String CORRUPTED`) a
comportamiento real (proceso muere) sin verificar.

### Antídoto operativo antes de redactar audit findings

1. Reproducir el bug en server local (`dayz-launch-test` si disponible).
2. Loggear el ciclo completo del bug (carga -> execute -> autosave -> reload).
3. Distinguir:
   - `crash` <-> proceso muere, server cae, requiere restart.
   - `VM exception` <-> excepción de Enforce VM, log spam, ejecución continúa.
   - `corruption` <-> datos malos persisten, código corre con ellos.
   - `degradation` <-> feature funciona peor pero corre.
   - `cosmetic` <-> solo visual / sin efecto funcional.
4. La etiqueta del finding usa el término concreto del paso 3, no "crash"
   como genérico.

### Caso real

Sesión `Review audit findings and create remediation plan` 2026-05-14
(`local_daee0706`): "Server arranca: NO" en tabla `antes vs después` se
desinfló a "el server sí arranca, solo que da error" tras corrección del
usuario.

### Referencia cruzada

R4 + R30 del `CLAUDE.md` global.

---

<!-- [merged 2026-06-05 from <claude-home>\skills user copy during plugin-canonical migration] -->
## 9. AUDITORÍAS MULTI-AGENTE: AISLAMIENTO DE CONTEXTO OBLIGATORIO (added 2026-05-16)

Post-mortem documentado en `LF_VStorage_dev/skills/rigorous-data-audit/postmortem.md`
(sesión `Evaluate GitHub project` 2026-05-14): 4 agentes auditores
"convergieron" en hallazgos confabulados porque leyeron el mismo conventions
doc y heredaron el mismo sesgo. La convergencia se interpretó como rigor;
era acoplamiento.

### Regla operativa para futuras auditorías multi-agente sobre código DayZ

- Cada agente verifica desde fuente vanilla / `path:line` independiente.
- Prohibido que dos agentes citen "lo mismo dice X" como evidencia cruzada
  cuando ambos leyeron el mismo doc.
- Al menos un agente debe correr **adversarial** — sin acceso al conventions
  doc, solo al código real, contrastando los hallazgos del resto.
- **Muestreo aleatorio (≥20%) de los hallazgos antes de aplicarlos**: si no
  pasan recheck adversarial, descartar la auditoría completa, no solo los
  ítems sospechosos. La confabulación es sistémica, no por-ítem.

### Síntomas de auditoría confabulada que disparan re-check

- Métricas absolutas grandes ("47 issues encontrados") sin `path:line` por
  ítem.
- Ramas OR defensivas etiquetadas como bug cuando son tolerancia diseñada.
  Caso: `classify_lod()` con bandas Arma 3 + DayZ — la rama OR ES el diseño,
  no un fallo.
- Severidad inflada (P1 sobre cosas que son P2-P3). Cruzar con sección 8.
- Convergencia anómala entre agentes que deberían ser independientes — si 4
  agentes "encuentran" lo mismo y leyeron el mismo conventions doc, es
  sesgo compartido, no triangulación.

### Definición operacional de VERIFIED

Para que un hallazgo pase a aplicar:

1. Tiene `path:line` concreto en código real (no en doc).
2. Pegado el snippet del código que viola la regla.
3. Pegado el snippet del fix con diff aplicable.
4. Al menos un agente sin contexto compartido lo verificó por separado.

Sin estos cuatro, el hallazgo se marca `❓ confabulación posible` y NO se
aplica.

### Referencia cruzada

R8 (verificación durante, no solo al final) + R22 (verificación honesta en
output) + R31 (lenguaje de pitch prohibido sin evidencia) del CLAUDE.md
global.
