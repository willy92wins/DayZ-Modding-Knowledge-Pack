# DayZ — Patrón "stub server-only" en jerarquías modded class

> Bug-pattern transversal. Aplica a cualquier mod DayZ que use la
> separación `#ifdef SERVER modded class X` para meter lógica pesada
> server-only. Documentado a raíz del compile error 2026-05-11 en
> LF_VStorage (`LFV_Module.ShouldBlockContainerInteractionWithReason`
> undefined en cliente con `mmg_storage` activo).

## El patrón arquitectónico (legítimo)

```
// Scripts/4_World/<MyMod>_Module.c  (client + server)
class <MyMod>_Module : CF_ModuleWorld
{
    // Stubs vacíos que el cliente puede llamar sin error.
    bool ShouldBlock(ItemBase x) { return false; }
    void Notify(PlayerBase p) {}
    void DoServerThing(EntityAI e) {}
}

// Scripts/4_World/<MyMod>_Module_Server.c  (solo server)
#ifdef SERVER
modded class <MyMod>_Module
{
    // Override real con lógica pesada.
    override bool ShouldBlock(ItemBase x) { /* validación, IO, RPC, … */ }
    override void Notify(PlayerBase p) { /* mensajes admin … */ }
    override void DoServerThing(EntityAI e) { /* persistencia, … */ }

    // Métodos NUEVOS añadidos solo aquí (NO en la base).
    bool NewServerMethod(...) { ... }   // <-- riesgo de bug
}
#endif
```

Esto está OK siempre que la disciplina se mantenga.

## El bug — añadir método server sin stub en la base

Cuando un dev añade un método nuevo en `<MyMod>_Module_Server.c` y se le
olvida añadir el stub correspondiente en `<MyMod>_Module.c`:

1. El método existe SOLO bajo `#ifdef SERVER`.
2. En cliente la clase base no tiene el método.
3. Cualquier código compilado en cliente que llame al método falla con
   `Undefined function '<MyMod>_Module.NewServerMethod'`.

### Cuándo se manifiesta

El bug es **silencioso hasta que algún action / hook / UI cargado en
cliente llama al método**. Path típico:

```
// Scripts/4_World/Actions/<MyMod>_ModdedAction_X.c
#ifdef <some_external_mod>
modded class ActionX
{
    override void OnStartServer(ActionData ad)   // <-- compila en client+server
    {
        <MyMod>_Module m = <MyMod>_Module.GetModule();
        if (m.NewServerMethod(...)) { ... }       // <-- compile fail si client carga el #ifdef
    }
}
#endif
```

`OnStartServer` ejecuta server-side, pero el fichero se **compila en
ambos**. El `#ifdef <some_external_mod>` se activa cuando el mod externo
está cargado (en cliente si el usuario lo tiene instalado).

Por tanto el bug aparece solo en clientes que tienen ese mod externo —
los demás no lo ven, lo cual hace que el bug pueda quedar latente
durante meses.

## Detección

Una pasada `grep` cruzada cierra el patrón:

```bash
# 1. Lista métodos server-only:
grep -nP '^\s*(bool|void|int|float|string)\s+\w+\s*\(' <MyMod>_Module_Server.c

# 2. Para cada uno, verificar si existe stub en la base:
grep -n 'NewServerMethod\b' <MyMod>_Module.c
```

Si (2) sale vacío para un método de (1) → falta stub.

Otra vía: grep todos los callsites `<MyMod>_Module\.\w+\(` y cruzar
contra lo definido en la base.

## Fix

Añadir stub no-op en la clase base. Firma EXACTA (incluyendo nombres de
parámetro — override rule Enforce):

```c
// En <MyMod>_Module.c, junto a los demás stubs:
bool NewServerMethod(/* mismos params + names que server */) { return false; }
void NewServerVoidMethod(/* mismos params */) {}
```

## Prevención durable

**Convención de equipo**: cualquier PR que toque `<MyMod>_Module_Server.c`
añadiendo un método público debe añadir el stub correspondiente en
`<MyMod>_Module.c` en el mismo commit.

Linter ligero (script offline antes de cada commit):

```python
# Pseudo-código: extraer firmas públicas de Server.c, verificar
# presencia de cada nombre en base .c. Falla CI si missing.
import re
server_methods = re.findall(r'^\s*(?:bool|void|int|float|string)\s+(\w+)\s*\(', server_src, re.M)
base_methods = re.findall(r'^\s*(?:bool|void|int|float|string)\s+(\w+)\s*\(', base_src, re.M)
missing = set(server_methods) - set(base_methods)
if missing:
    fail(f"Missing client stubs: {missing}")
```

(No automatizado a fecha de hoy; backlog si el pattern reaparece.)

## Casos verificados

| Proyecto | Métodos afectados | Solución | Fecha |
|---|---|---|---|
| LF_VStorage | `ShouldBlockContainerInteractionWithReason`, `SendBlockReasonMessageToPlayer` | Stubs añadidos en `LFV_Module.c:167-169` | 2026-05-11 |

## Relacionado

- `enforce-script-reference` Rule 24: override parameter names MUST match
  exactly. Aplica al añadir stubs base — usar mismos names que el server.
- DayZ engine compile lifecycle: client + server cargan el mismo
  `Scripts/4_World/` tree, divergencia solo via `#ifdef SERVER`.
- Skill `enforce-script-reference` cubre la layer architecture (3_Game /
  4_World / 5_Mission) pero NO este patron específico — candidato a
  añadir si el bug reaparece en otro mod.
- [[dayz-enforce-script-reference]] — Rule 24 + reglas de `modded class` (no añadir member vars, coexistencia de declaraciones).
- [[dayz-mod-implementation-checklists]] — el client/server data map (§1) que previene este tipo de divergencia.
- [[dayz-capacidades-verificadas]] — esta nota está enlazada desde ahí como bug-pattern relacionado con `#ifdef SERVER`.

## Aplica a

- LF_VStorage (verificado).
- LF_PowerGrid (probable — usa misma arquitectura módulo + #ifdef SERVER).
- Cualquier mod DayZ que separe lógica heavy en `_Server.c` con
  `#ifdef SERVER modded class`.
