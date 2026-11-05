# Precios OVHcloud ES — instantánea 2026-11-04

Fuente: catálogo público `GET /order/catalog/public/{cloud,vps}?ovhSubsidiary=ES` (sin IVA; IVA 21 %).
Caducan: vuelve a sacarlos del catálogo antes de una decisión de compra.

## Public Cloud (por hora, facturación por segundo con 1 min mínimo)

| Flavor | vCPU | RAM | Disco | €/h | 173 h/mes (40 h/sem) | 730 h |
|---|---|---|---|---|---|---|
| d2-4 | 2 | 4 | 50 NVMe | 0,0206 | 3,56 | 15,0 |
| d2-8 | 4 | 8 | 50 NVMe | 0,0372 | 6,44 | 27,2 |
| b3-8 | 2 | 8 | 50 NVMe | 0,0512 | 8,86 | 37,4 |
| c3-8 | 4 | 8 | 100 NVMe | 0,0913 | 15,8 | 66,6 |
| r3-16 | 2 | 16 | 50 NVMe | 0,0663 | 11,5 | 48,4 |
| b3-16 | 4 | 16 | 100 NVMe | 0,1023 | 17,7 | 74,7 |
| b2-15 | 4 | 15 | 100 SSD | 0,1342 | 23,2 | 48,05 (mensual) |
| win-b2-15 | 4 | 15 | 100 SSD | 0,3504 | 60,6 | 110,38 (mensual) |

- Licencia Windows en la gama 3 (b3/c3/r3): `instance.windows-vcore-license` = **0,0347 €/vCore/h**.
  Por ejemplo, b3-16 con Windows = 0,1023 + 4 × 0,0347 = **0,2411 €/h** (41,7 €/mes a 173 h).
- **Disco local NVMe de la gama 3, cobrado aparte del flavor:** `<flavor>.local-disk-gb` a
  0,0001458 €/GB/h, verificado en el consumo real (b3-16: 100 GB ≈ 0,0146 €/h). Las tablas de €/h de
  arriba no lo incluyen. Sin verificar si se sigue cobrando con la instancia aparcada.
- Licencia Windows de la gama 3: en la primera hora real no apareció en `usage/current`. Pendiente
  de confirmar con la factura.
- Snapshot (lo que se paga con la instancia aparcada): 0,011 €/GB/mes.
- IPv4 pública: **0,0027 €/h, verificado en el consumo real de GRA11** el 2026-11-04. El catálogo dice
  0 €, que es erróneo.
- IP flotante: 1,80 €/mes. Volumen de bloque clásico: ~0,043 €/GB/mes.
- Tráfico de salida incluido en regiones de la UE.

## VPS clásico (mensual, sin permanencia, instalación 0 €)

| Plan | vCPU | RAM | Disco | €/mes | Windows +€/mes |
|---|---|---|---|---|---|
| vps-2025-model1 | 4 | 8 | 75 | 6,49 | 7,50 |
| vps-2025-model2 | 6 | 12 | 100 | 9,99 | 15,50 |
| vps-2025-model3 | 8 | 24 | 200 | 19,99 | — |
| vps-2027-model1 | 2 | 4 | 40 | 4,49 | — |
| vps-2027-model2 | 4 | 8 | 75 | 8,49 | 8,00 |
| vps-2027-model3 | 6 | 12 | 100 | 12,24 | 17,00 |
| vps-2027-model4 | 8 | 24 | 200 | 23,49 | 28,00 |

Con permanencia de 6 o 12 meses baja entre un 5 y un 15 %, pero obliga a pagar el resto si se cancela.

## Dónde se cruzan las dos opciones

Public Cloud solo sale a cuenta si se usa poco: por debajo de unas 23 h/semana para el equivalente
de 6 vCPU y 12 GB, o de unas 29 h/semana para el de 2 vCPU y 8 GB. Por encima, el VPS mensual es más
barato y además está encendido 24/7.
**Pero el crédito Public Cloud solo se gasta en Public Cloud**: si el dinero es crédito o voucher de
un proyecto, la elección ya está hecha.
