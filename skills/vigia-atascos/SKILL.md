---
name: vigia-atascos
description: Detecta trabajo parado, en bucle o esperando entre agentes de Guillermo (INDEX/POST/HANDOFF/PRs). Usar cuando haya hops abiertos, POST atrasados, o el Secretario/RP revise el tablero. Complementa task-observer; no sustituye la espera activa del dueño del hop.
---

# Vigía de atascos (Foreman-lite)

Adaptado de ideas de Archive228/foreman (MIT); no es una copia del stack. No adivinar: solo señales observables.

## Quién
- **Detecta:** Secretario (tablero, INDEX, POST, Pack PRs).
- **Checker (≠ worker):** Auditor por defecto; RP si es agenda; Experto IA si es lane/hardware.
- El worker del hop **no** se auto-da PASS.

## Indicadores
1. **STALL** — sin POST/avance con recurso dedicado >2 h, o sin cierre a fin de día.
2. **LOOP** — mismo fallo/sha/pregunta ≥2 veces.
3. **WAITING** — bloqueado en humano/otro bot sin chase (rompe espera activa).
4. **HANDOFF-DROP** — cierre sin POST o INDEX sin bloque POST.
5. **UNVERIFIED** — claim sin evidencia GitHub/CI/prueba en juego.

## Salida
Lista corta: `código | hop/PR | worker | checker propuesto | evidencia`. Partial ≠ PASS. Tras detectar, `SendToAgent` al checker con el literal del síntoma.

Ver también: skill `task-observer` (observación genérica de tarea).
