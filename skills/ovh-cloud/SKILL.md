---
name: ovh-cloud
description: Operar OVHcloud por API (endpoint EU) — sobre todo la máquina de desarrollo y pruebas en Public Cloud que se enciende y se aparca bajo demanda para gastar solo crédito. Cubre tokens (createToken, POST /auth/credential, rutas mal puestas que dan NOT_GRANTED_CALL), crédito y vouchers del proyecto, consumo del mes, flavors e imágenes, crear/encender/aparcar (shelve/unshelve) instancias, el guardián de presupuesto en el PC, el agente de inactividad dentro de la VM Windows, consola VNC, precios del catálogo público y la comparación VPS mensual vs Public Cloud por horas. Dispara con «ovh», «ovhcloud», «public cloud», «enciende/apaga/aparca el servidor», «sube la devbox», «el VPS», «cuánto crédito queda», «shelve», «unshelve», «flavor», «b3-16», «token de OVH», «NOT_GRANTED_CALL», «createToken», o cualquier llamada a eu.api.ovh.com. Invócala antes de crear, arrancar o pagar nada en OVH.
---

# OVHcloud — máquina bajo demanda pagada con crédito

Herramienta: `scripts/ovhpc.py` (Python, sin dependencias). Referencias: `references/api.md`
(chuleta de endpoints con lo probado marcado) y `references/pricing-2026-11.md` (precios fechados).

## Prioridad de máquinas (Guillermo 2026-11-05; corrección 14:00)

**Ventana temporal (hasta 28-11-2026 incluido):**
- La instancia OVH `devbox` tiene **prioridad para pruebas**: créditos de regalo, online 24/7.
- **No** aparcar (`down`) tras cada uso mientras dure esta ventana.
- Estado actual: **PENDIENTE puesta a punto** (Guillermo monta Steam + DayZ). **Nadie lanza pruebas** hasta aviso del Asistente («steam ready con dayz»).

**Desde 29-11-2026:**
- Vuelve la norma general: **Willy → portátil DESKTOP-L49Q27C → OVH último recurso**.
- Tras usar OVH: `python -I scripts/ovhpc.py down` (shelve). Solo shelve corta el gasto.

Claves (`OVH_*`) en Willy (`HKCU\Environment`); config en `~/.ovh-cloud/`. Nunca en el Pack ni en el vault.

## Estado de esta cuenta (2026-11-04)

- Proyecto Public Cloud `<REDACTED-PROJECT-ID>`. Configuración en `~/.ovh-cloud/config.json`
  y log en `~/.ovh-cloud/guard.log`.
- Instancia `devbox`: **b3-16 + Windows Server 2022, región GRA11**, facturación por horas.
  Encendida, el consumo real de la primera hora (2026-11-04) fue:
  - 0,1023 €/h de instancia;
  - **0,0146 €/h de disco local NVMe**, que se cobra aparte (`b3-16.local-disk-gb`, 0,0001458 €/GB/h
    × 100 GB);
  - 0,0027 €/h de IPv4.
  En total **≈0,12 €/h**, sin IVA. Si además se cobra la licencia Windows (4 × 0,0347 €/h, que aún no
  aparece en el consumo), serían ≈0,26 €/h.
- El agente de la VM aparcó la instancia él solo a los 49 minutos de estar inactiva (verificado el
  2026-11-04).
- Crédito: **100 € «Credit provisionning»** hasta el 1-11-2027 (es el tope de gasto del usuario) y
  **200 € de prueba gratuita** hasta el 29-11-2026, que se puede gastar entero.
- **No hay medio de pago registrado** y el saldo prepago (`/me/ovhAccount/ES`) está a 0 €.
  No añadir un medio de pago ni pagar nada sin que el usuario lo pida.
- Credenciales: variables de usuario `OVH_APPKEY`, `OVH_AppSecret` y `OVH_ConsumerKey`. El script las
  lee de `HKCU\Environment` porque no están en el entorno del proceso. El token principal puede
  leer todo y escribir solo en este proyecto, y **caduca el 4-12-2026**: renovarlo con `new-token`.

## Uso

```
python -I scripts/ovhpc.py status      # estado, IP, crédito estimado, días de token
python -I scripts/ovhpc.py up          # unshelve → ACTIVE (se niega si el crédito < floor)
python -I scripts/ovhpc.py down        # shelve → SHELVED_OFFLOADED (deja de cobrar CPU)
python -I scripts/ovhpc.py budget      # detalle de créditos y consumo del mes
python -I scripts/ovhpc.py vnc         # URL de consola (primer arranque de Windows, rescate)
python -I scripts/ovhpc.py api GET /cloud/project/<id>/instance
```

Ejecútalo desde PowerShell. En Git Bash hay que exportar `MSYS_NO_PATHCONV=1` o `/me` se
convierte en `C:/Program Files/Git/me`.
Para conectarse: `mstsc /v:<ip>`, usuario `Administrator` y la contraseña que puso el usuario en VNC.

## Reglas de dinero

1. **Solo shelve corta el gasto.** Apagar Windows desde dentro, `stop` o `pause` dejan la instancia
   en `SHUTOFF`, que se cobra a precio completo. El guardián del PC la aparca si la ve así.
2. **Nunca `monthlyBilling` ni `activeMonthlyBilling`.** Es irreversible, cobra meses enteros, y basta
   un unshelve breve para que se facture el mes completo.
3. **El checkout de un pedido o un medio de pago nuevo cuestan dinero real:** siempre con el OK
   explícito del usuario para esa compra concreta.
4. OVH no tiene tope de gasto duro, solo alertas por email (`/alerting`). El tope lo pone `ovhpc.py`:
   `up` se niega a arrancar y `guard` aparca la instancia si el crédito restante estimado baja de
   `floor_eur` (5 €).

### Cómo estima el crédito restante

`restante = Σ crédito disponible − consumo del mes sin facturar × vat_factor (1,21)`.

- La versión **conservadora** solo cuenta los créditos que siguen vigentes el día 1 del mes que
  viene, que es cuando OVH factura el consumo y aplica el crédito. La **optimista** cuenta todo lo
  vigente hoy.
- La doc dice que el voucher se usa «when your consumption is billed», así que **no está claro si
  la prueba que caduca el 29-11 cubrirá el consumo de noviembre**, facturado el 1-12.
- Hasta comprobarlo con la factura de diciembre (mirar `budget`: cuánto bajó cada crédito), el
  guardián usa la conservadora.
- El `vat_factor` también es una suposición conservadora **sin verificar**.

## Encendido y apagado

| Capa | Dónde | Qué hace |
|---|---|---|
| Manual | tu PC | `up` y `down` |
| Agente de inactividad | dentro de la VM, tarea `OVH-IdleShelve` (SYSTEM, cada 5 min) | aparca tras `idle_minutes` (45) sin sesión RDP activa ni tráfico de DayZServer (`dayz_rx_kb_per_min` 300) |
| Guardián | tu PC, tarea `OVH-Guard` (cada 15 min, `pythonw`) | aparca si está en `SHUTOFF`/`STOPPED`, si el crédito baja del floor, o si hay `monthlyBilling`; avisa de la caducidad del token |

Las dos capas automáticas cubren huecos distintos. El agente funciona aunque tu PC esté apagado. El
guardián cubre el caso de que alguien apague Windows desde dentro, porque entonces el agente ya no
corre y la instancia sigue cobrando.

### Instalar el agente en la VM

1. En tu PC, ejecuta `ovhpc.py vm-token`. Pide un token que solo puede leer y aparcar esa instancia y
   prepara la carpeta `~/.ovh-cloud/vm-agent/`. El usuario valida la URL con su login.
2. Copia esa carpeta a la VM por RDP (copiar y pegar archivos funciona en mstsc). En PowerShell como
   administrador: `powershell -ExecutionPolicy Bypass -File .\install.ps1 -DayZFirewall`.
3. Comprueba la última línea del dry-run (`sessions=1 ... -> idle=0m/45`) y
   `C:\ovh-agent\agent.log`.

Detalles del agente:

- Una sesión RDP **desconectada** (cerrar la ventana sin cerrar sesión) cuenta como inactiva. Al
  aparcar se pierde la RAM, como en un apagado: hay que guardar el trabajo antes de irse.
- El temporizador se reinicia en cada arranque, así que tras un unshelve hay 45 minutos de margen
  antes de que pueda volver a aparcar.
- `config.json` dentro de la VM contiene el app secret y un consumer key limitado. La carpeta queda
  con permisos solo para SYSTEM y Administradores.

### Guardián en tu PC

`ovhpc.py install-guard [--minutes 15]` lo instala y `uninstall-guard` lo quita. Escribe en
`~/.ovh-cloud/guard.log`.

## Tokens: errores conocidos

- `403 NOT_GRANTED_CALL` en todo, con el token en estado `validated`: mira las reglas con
  `api GET /auth/currentCredential`. Una ruta vacía `""` o con espacio (`" /*"`) **no casa con
  nada**: pasó dos veces el 2026-11-04.
- 403 solo al escribir: el token no cubre esa ruta. Por ejemplo, uno hecho para `/vps/*` no puede
  crear instancias. Usa `new-token`, que pide `GET /*` y escritura en `/cloud/project/<id>/*`.
- **Los 5 tokens validados el 2026-11-04 salieron con exactamente un mes de validez**, también el de
  la VM: caducan el **2026-12-04**. Al caducar, el guardián y el agente fallan, con un error en su log
  y en `agent.log`. Para renovar:
  1. `new-token` y validar el enlace.
  2. `vm-token`, validar, y copiar el `config.json` nuevo a `C:\ovh-agent\` en la VM.
  Alternativa a explorar: las cuentas de servicio OAuth2 de OVH (sin verificar que no caduquen).
- Listar los tokens: `api GET /me/api/credential` y luego `/me/api/credential/{id}`. Para revocarlos
  hace falta permiso `DELETE /me/*`, que el token principal no tiene a propósito: se revocan en el
  panel o se dejan caducar.

## Datos que conviene saber

- **El crédito de un proyecto Public Cloud no paga un VPS clásico** ni otros productos. Antes de
  elegir producto, mira dónde está el dinero: `/me/ovhAccount`, `/cloud/project/<p>/credit`,
  `/me/payment/method`.
- Al aparcar, el disco pasa a un snapshot `*-shelved` que se paga a 0,011 €/GB/mes. Se conserva la IP.
  Se pierde la RAM, y también los discos NVMe passthrough de los flavors IOPS/T1/T2 (el b3-16 no
  los tiene).
- Unshelve vuelve a colocar la instancia en un host, y podría fallar por capacidad (inferido de
  OpenStack, no documentado por OVH). `up` espera hasta 30 minutos y para si la ve en `ERROR`.
- **La IPv4 se cobra: 0,0027 €/h** (≈1,97 €/mes), verificado en `usage/current` (`type: publicip`)
  el 2026-11-04. El catálogo público dice 0 €: está mal. Previsiblemente sigue cobrándose con la
  instancia aparcada.
- `usage/current` se actualiza aproximadamente cada hora (`lastUpdate`), así que el presupuesto va
  con hasta una hora de retraso.
- Crear la instancia b3-16 con Windows 2022 tardó 442 s hasta `ACTIVE` (2026-11-04).
- La VM Windows viene con la zona horaria del Pacífico. Al agente no le afecta, porque solo compara
  horas de la propia VM.
- Tiempos medidos el 2026-11-04 (b3-16, Windows 2022, 100 GB):
  - **shelve: 598 s**, hasta `SHELVED_OFFLOADED`;
  - **unshelve: 279 s**, hasta `ACTIVE`;
  - la IP se conserva (<REDACTED-IP> antes y después).
  Cuenta 5 minutos desde `up` hasta poder conectar por RDP.
- **Sin verificar:**
  - si durante los 10 minutos de `SHELVING` se sigue cobrando la instancia;
  - si la licencia Windows de la gama 3 se cobra aparte (la instancia tiene
    `licensePlanCode: null`; confirmarlo en `usage/current` → `instanceOption`).
- Primer arranque de Windows: no hay contraseña inicial por email. Se fija en la consola (`vnc`)
  eligiendo idioma, teclado y contraseña del `Administrator`. Esto lo hace el usuario.
