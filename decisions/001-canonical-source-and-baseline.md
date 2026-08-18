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

# ADR 001 — Fuente Git canónica y baseline inmutable

- **Fecha:** 2026-07-24
- **Estado:** aceptada

## Contexto

El pack existía únicamente como tres copias byte-idénticas de un ZIP publicado.
Editar skills instaladas, notas del vault y el ZIP por separado reproduciría el
drift que ya se observa: las catorce skills del archivo divergen de sus fuentes
locales actuales.

## Decisión

Este repositorio pasa a ser la única fuente editable del pack. El contenido del
ZIP anterior se importó sin cambios en el commit raíz
`d48e2c1a02dacc97645a9e70d8bc1058e6dae9a5`.

El ZIP de origen queda como fixture inmutable:

- SHA-256:
  `E63C26C5C385E3037B4AFE9C918B3A9DE9E12CC0AF876316214518BF852735E5`.
- Archivos extraídos: 138.
- Comparación ZIP ↔ árbol: 138 presentes, 0 hashes distintos, 0 extras.

Las copias instaladas y el vault son entradas que se reconcilian mediante un
inventario explícito; nunca se sobreescribe una fuente con otra por fecha o
nombre solamente.

## Consecuencias

- Toda release se construirá desde un commit limpio de este repositorio.
- Todo conflicto pack↔fuente tendrá una adjudicación durable.
- Los artefactos de planificación pueden vivir en Git, pero el builder público
  usará una allowlist explícita.
- No se publicará ni empujará ningún remoto durante esta iniciativa sin una
  petición separada del usuario.
