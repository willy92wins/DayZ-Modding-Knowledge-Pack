# OVHcloud API — chuleta (verificada 2026-11-04)

Fuentes: esquemas públicos `https://eu.api.ovh.com/1.0/{cloud,vps,auth,order}.json`,
`https://eu.api.ovh.com/v2/publicCloud.json`, docs `https://docs.ovhcloud.com/en/llms.txt`
(cada guía tiene versión `.md`). Las rutas marcadas **[probado]** se ejecutaron contra la cuenta.

## Autenticación (v1)

- Firma: `X-Ovh-Signature = "$1$" + sha1(AS + "+" + CK + "+" + METHOD + "+" + URL + "+" + BODY + "+" + TS)`,
  con `TS` de `GET /auth/time` y `URL` completa (incluida la query). Cabeceras: `X-Ovh-Application`,
  `X-Ovh-Consumer`, `X-Ovh-Timestamp`, `X-Ovh-Signature`.
- Pedir un token sin panel **[probado]**: `POST /auth/credential` solo con `X-Ovh-Application`,
  body `{"accessRules":[{"method":"GET","path":"/*"}, ...]}` → `{consumerKey, validationUrl,
  state:"pendingValidation"}`. El usuario abre `validationUrl`, hace login y elige duración.
- Ver qué puede hacer el token **[probado]**: `GET /auth/currentCredential` → `rules`, `expiration`.
- Página manual: `https://auth.eu.ovhcloud.com/api/createToken` (o `eu.api.ovh.com/createToken`).
- Trampa **[probado]**: una ruta vacía `""` o con espacio `" /*"` se acepta al crear pero no
  casa con nada → todo da `403 NOT_GRANTED_CALL`. Las rutas empiezan por `/` sin espacios.
- Endpoint EU: `https://eu.api.ovh.com/1.0` (también `/v2`). Alias `api.eu.ovhcloud.com`.
- SDK oficial `python-ovh` (PyPI 1.2.0, 2024) y CLI oficial `ovhcloud`
  (github.com/ovh/ovhcloud-cli). `ovhpc.py` no depende de ninguno.

## Cuenta y saldo

| Llamada | Qué da |
|---|---|
| `GET /me` | país, subsidiaria, moneda |
| `GET /me/ovhAccount/{ES}` | saldo **prepago** (no es crédito Public Cloud) |
| `GET /me/payment/method` | medios de pago registrados |
| `GET /cloud/eligibility` | `actionsRequired` (p. ej. `addPaymentMethod`) |

## Public Cloud — proyecto

| Llamada | Qué da |
|---|---|
| `GET /cloud/project` | ids de proyecto **[probado]** |
| `GET /cloud/project/{p}` | estado, `unleash` **[probado]** |
| `GET /cloud/project/{p}/credit` → `/credit/{id}` | crédito: `available_credit`, `validity.to`, `voucher` **[probado]** |
| `POST /cloud/project/{p}/credit {code}` | canjear voucher |
| `GET /cloud/project/{p}/usage/current` | consumo del mes sin facturar (`totalPrice`); 404 si no hay **[probado]** |
| `GET /cloud/project/{p}/usage/forecast` | previsión + `usableCredits` |
| `GET/POST /cloud/project/{p}/alerting` | alerta por email (`monthlyThreshold`, `emails`, `delay`) |
| `GET /cloud/project/{p}/quota` | límites por región (cores, RAM, instancias) **[probado]** |
| `GET /cloud/project/{p}/region` | regiones activas **[probado]** |
| `GET /cloud/project/{p}/flavor[?region=]` | flavors: `id`, `name`, `osType`, `vcpus`, `ram`, `disk` **[probado]** |
| `GET /cloud/project/{p}/image[?region=&osType=windows]` | imágenes **[probado]** |
| `GET/POST /cloud/project/{p}/sshkey` | claves SSH `{name, publicKey}` |

## Public Cloud — instancia (v1)

- Crear: `POST /cloud/project/{p}/instance` `{name, region, flavorId, imageId, monthlyBilling:false,
  sshKeyId?, userData?, networks?, autobackup?}`.
- Ciclo de vida: `POST .../instance/{id}/{start|stop|shelve|unshelve|resume|vnc|rescueMode}` sin body;
  `reboot {type: soft|hard}`, `reinstall {imageId}`, `resize {flavorId}`, `snapshot {snapshotName}`.
- `activeMonthlyBilling`: **irreversible**; no usar en un flujo de encendido y apagado.
- `DELETE .../instance/{id}`.
- Estados: `BUILD → ACTIVE`; `SHELVING → SHELVED_OFFLOADED`; `UNSHELVING → ACTIVE`; también
  `SHUTOFF`/`STOPPED` (se facturan enteros) y `ERROR`.
- v2 equivalente: `POST /v2/publicCloud/project/{p}/compute/instance/{id}/action {type: SHELVE|UNSHELVE|START|STOP|...}`.

## VPS clásico (por si acaso)

`GET /vps`, `POST /vps/{sn}/{start|stop|reboot}`, `POST /vps/{sn}/rebuild` (BETA; `/reinstall` y
`/status` obsoletos desde 2026-10-15), `POST /vps/{sn}/createSnapshot` (1 snapshot máximo).
Factura mensual fija: parar el VPS no ahorra nada. Pedido por carrito:
`POST /order/cart {ovhSubsidiary}` → `POST /order/cart/{id}/vps {planCode, duration:"P1M", pricingMode}`
→ `POST .../item/{i}/configuration` (`vps_datacenter`, `vps_os`) → `POST .../assign` →
`GET .../checkout` (previsualizar) → `POST .../checkout`.
**El checkout crea un pedido facturable: siempre con OK explícito del usuario.**

## Catálogo público (sin auth)

`GET /order/catalog/public/cloud?ovhSubsidiary=ES` y `.../vps?ovhSubsidiary=ES`. Precio en
`pricings[].price / 1e8` €, sin IVA (`locale.taxRate`). Flavors Public Cloud en `addons[]` con
`product == "publiccloud-instance"` y `planCode` `<flavor>.consumption` (por hora) o
`.monthly.postpaid`. VPS en `plans[]` (`vps-2025-modelN`, `vps-2027-modelN`), specs en
`products[].blobs.technical`.
