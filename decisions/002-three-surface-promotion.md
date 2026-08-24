> **SUPERSEDED 2026-08-18.** This ADR declared the Git repository as the only
> editable source. That is no longer the policy.
>
> - `~\.claude\skills\` is the **working copy**. It is where skills are
>   edited. The copy the agent loads is the one that is written.
> - The public MIT repository `DayZ-Modding-Knowledge-Pack` is the
>   **publication snapshot**. It receives harvest by UNION, never a wipe of
>   the destination.
> - The Cowork skills-plugin tree is an ephemeral projection. Neither source
>   nor destination.
> - Layer split: the pack is the OFFLINE layer; DayZ-MCP is the ONLINE/in-game
>   layer.
>
> The body below is kept for traceability.

# ADR 002 — Promoción obligatoria a repo, Obsidian y skills

- **Fecha:** 2026-07-24
- **Estado:** aceptada

## Contexto

El usuario exige que todo conocimiento reunido permanezca también en Obsidian y
en las skills, además de incorporarse al repositorio. Tratar esas tres
superficies como fuentes editables equivalentes repetiría BUG-001: hoy las
catorce skills del baseline ya divergen de sus copias locales.

## Decisión

Cada superficie tiene un rol distinto:

1. **Git** es la única fuente del pack distribuible y de cualquier ZIP/release.
2. **Obsidian** conserva la memoria durable completa: evidencia, rutas locales,
   research, decisiones, unknowns y la versión privada de cada invariante.
3. **Skills instaladas** son despliegues operativos generados desde un commit
   validado; no se editan como fuentes independientes.

Todo conocimiento aceptado debe tener un routing durable:

- repo y Obsidian son obligatorios;
- una invariante de dominio debe llegar además a su skill activa;
- `not_applicable` solo se permite para gobierno o tooling sin consumidor de
  skill, con motivo explícito;
- la variante pública se sanitiza; la evidencia privada permanece en Obsidian.

La promoción usa targets lógicos versionados y roots físicos en configuración
local no versionada. Se ejecuta únicamente después de los gates mediante
staging, validación del árbol completo, replace en targets allowlisted y
readback por hash. Cada promoción produce un recibo con commit fuente, hashes,
IDs de destino y fecha, sin rutas privadas.

## Consecuencias

- Ninguna fase se cierra con `PROMOTION-UNROUTED` o `PROMOTION-DRIFT`.
- La fase 01 reconcilia las copias existentes antes de la primera promoción.
- Un hallazgo privado puede conservar más detalle en Obsidian, pero su
  invariante depersonalizada debe llegar al repo y a la skill aplicable.
- Los documentos de gobierno no se fuerzan dentro de una skill; quedan
  explícitamente `not_applicable`.
- Una promoción parcial o un target no verificado no se presenta como éxito.
