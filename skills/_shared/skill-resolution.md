# Skill resolution policy (added 2026-05-12)

Política operativa cuando ya hay duplicación entre skills custom del usuario y skills instaladas vía plugin (no es el caso "pre-install" — para eso ver "PLUGIN INSTALL CONFLICT CHECK" en `skill-conventions/SKILL.md`).

Caso típico: el plugin `agentic-z@dayz-n-chill` introduce `dayz-p3d-audit`, `dayz-p3d-debin`, `dayz-particles` cuando ya existen versiones locales en `C:\Users\<you>\.claude\skills\`. Ambos quedan resolvibles vía namespace (`agentic-z:dayz-p3d-audit` vs `dayz-p3d-audit`).

## Default operativo

Sin política explícita en proyecto: las skills custom locales (`C:\Users\<you>\.claude\skills\<name>`) ganan al plugin (`agentic-z:<name>`) porque suelen tener parches específicos del usuario.

## Política por skill (a decidir al detectar el conflicto)

1. **Custom local deriva de la del plugin y el parche ya está integrado upstream** → borrar la custom local, usar la del plugin. Verificar viendo el diff antes de borrar (`diff plugin/skill.md user-local/skill.md`).
2. **Custom local diverge sustancialmente** (paths a `P:\` propios, magic numbers tuneados a tu setup, secciones específicas LFPG/LFV/SimpleGroup) → mantener custom, desactivar la del plugin con `/plugin manage <plugin>` desmarcando esa skill concreta.
3. **No estás seguro** → mantener ambas, declarar conflicto en el `CLAUDE.md` del proyecto activo:

```markdown
## Skill resolution overrides
- Para dominio `dayz-p3d-audit`: usar `<namespace>:dayz-p3d-audit` porque <razón>. Última verificación YYYY-MM-DD.
```

## Documentar la decisión donde se vea

Una vez decidido, escribir el override en:

- `00_System/codex-briefing.md` del vault (regla global del pipeline).
- `workflow.md` del vault si afecta a varios proyectos.
- `CLAUDE.md` del repo si es específico de proyecto.

Así Codex y Claude saben cuál llamar y por qué, sin tener que re-evaluar el conflicto en cada sesión.

## Antes de instalar un plugin nuevo

Listar las skills locales (`ls ~/.claude/skills/`) y comparar con el manifest del plugin. Decidir política PR-skill ANTES de instalar, no después de notar el conflicto. Esto está ya cubierto en `skill-conventions/SKILL.md` sección "PLUGIN INSTALL CONFLICT CHECK".

## Anti-patrón

Instalar plugin sin auditar conflictos, descubrir la duplicación tres sesiones después, y dejar la decisión en limbo. Resultado: las dos versiones conviven indefinidamente, los agentes invocan la "incorrecta" según orden de búsqueda interno y el usuario no entiende por qué la skill se comporta diferente.

## Medido el 2026-08-24: el «Default operativo» se confirma, y le faltan dos cosas (added 2026-08-24)

El default de arriba —«las skills custom locales ganan al plugin»— **se midió y es cierto**,
pero hasta esa fecha era política escrita sin medición, y su ejemplo era `agentic-z:`, no el
plugin que hoy sirve la mayoría del catálogo. Medición: se invocó la MISMA skill duplicada por
sus dos nombres y se leyó el base directory devuelto.

| Invocación | Carga de |
|---|---|
| `mixamo-retarget` (desnudo) | `C:\Users\<you>\.claude\skills\mixamo-retarget` |
| `anthropic-skills:mixamo-retarget` (prefijado) | `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\<uuid>\<uuid>\skills\mixamo-retarget` |

**Los dos matices que faltaban, y son los que hacen daño:**

1. **«Gana» sólo se aplica al nombre desnudo.** Las dos copias siguen siendo **servibles**: el
   nombre prefijado carga la del plugin, y los dos nombres están en el catálogo de cada
   sesión. Así que arreglar la copia local NO retira la otra — un agente que escriba
   `anthropic-skills:<x>` se lleva la versión vieja sin ninguna señal de que lo es. En la
   medida, la copia servida iba **19 días por detrás** y le faltaba un arreglo de doctrina que
   sí estaba en la local.
2. **Hay un tercer árbol, y no es ninguna de las dos editables.** Lo que sirve el namespace no
   es la carpeta desde la que se empaquetó: es una copia **materializada por la app** bajo
   `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\`, con manifiesto y un
   reconciliador que borra lo no registrado a los minutos (ver la memoria
   `claude-skills-plugin-tree-managed`). Puede haber **más de una instalación** ahí a la vez,
   con contenidos distintos. Editarla a mano no sobrevive; el alta oficial es `.skill` +
   botón «Save skill».

**Consecuencia para el punto 1 de §Política por skill** («borrar la custom local, usar la del
plugin»): antes de borrar nada, comprobar **cuál de los árboles del plugin se sirve de verdad**
y con qué contenido. El `diff` contra la carpeta de origen del paquete puede salir limpio
mientras lo servido es otra cosa.

**Comprobación barata, un minuto**: invoca la skill por sus dos nombres, compara el base
directory y una línea testigo del cuerpo. Si difieren, tienes duplicación servible, no
duplicación resuelta.

Detalle, mapa de las cinco raíces y las cuatro versiones simultáneas medidas: [[LL-356]].
