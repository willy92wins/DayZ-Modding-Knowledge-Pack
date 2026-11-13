# Script network arrays (26220720)

Local runtime probe of `array<int>` over `ScriptRPC` and `ScriptInputUserData`, on DayZ build `26220720`. The probe ran a diag client and server on loopback on one machine. It measured what the receiver read and whether the client saw an ACK; it did not measure wire size, fragmentation, packet loss or Internet latency.

The probe PBO was rebuilt with `AddonBuilder` after fixing a duplicate declaration in `NetProbePlayer.c`; the build reported `Build Successful`. PBO SHA-256: `ca0b88c18a1cf6dc9e31d8b161c260f66b0bdcbaea1e55d325d7b69624fd957e`. Run: `ae70ec7d-d975-4b9a-b6cb-07236d87cb8b`.

## `ScriptRPC` with `array<int>`

The client wrote sequence, count and an `array<int>` of 1, 64, 255 and 256 elements. The server read sequence, count and the array, then sent an ACK carrying sequence and count. All four writes succeeded and all four reads returned `read_ok=true`; `values.Count()` matched the declared count. The client received all four ACKs with `read_ok=true`.

| count | client `Write` | server `Read` | server `values.Count()` | client ACK `read_ok` |
|---:|---|---|---:|---|
| 1 | true | true | 1 | true |
| 64 | true | true | 64 | true |
| 255 | true | true | 255 | true |
| 256 | true | true | 256 | true |

Evidence: client log `script_2026-11-12_20-11-39.log:322-330`; server log `script_2026-11-12_20-11-16.log:119-126`. [EXACT][CLAIM-NET-ARRAY-RPC]

## `ScriptInputUserData` with `array<int>`

The client wrote message type, sequence, count and an `array<int>` of 1, 16, 32, 36 and 37 elements. The server read sequence, count and the array, then sent an ACK carrying sequence and count. All five writes succeeded and all five reads returned `read_ok=true`; `values.Count()` matched the declared count. The client received all five ACKs with `read_ok=true`. This channel was not tested with 64, 128, 255 or 256 elements.

| count | client `Write` | server `Read` | server `values.Count()` | client ACK `read_ok` |
|---:|---|---|---:|---|
| 1 | true | true | 1 | true |
| 16 | true | true | 16 | true |
| 32 | true | true | 32 | true |
| 36 | true | true | 36 | true |
| 37 | true | true | 37 | true |

Evidence: client log `script_2026-11-12_20-11-39.log:331-347`; server log `script_2026-11-12_20-11-16.log:127-136`. [EXACT][CLAIM-NET-ARRAY-INPUT]

## ACK and read status

In this probe the server sent the ACK after reading sequence and count, and the client's ACK handler recorded `read_ok=true` for every array message. The ACK carried sequence and count, not a content hash. An ACK therefore proves that the handler ran and that the declared count was read; it does not prove that the receiver validated every value. [EXACT][CLAIM-NET-ARRAY-ACK]

## Scope

The results are local loopback observations on build `26220720`, not universal limits. They cover `array<int>` only; `array<string>`, `array<float>`, `array<bool>`, nested arrays and maps were not tested. No wire size, no real packet loss, no fragmentation and no Internet latency were measured. `ScriptRPC` worked through 256 integers; `ScriptInputUserData` worked through 37 integers in this probe. [EXACT][CLAIM-NET-ARRAY-SCOPE]

## Practical reading

- For compact state, an `array<int>` over `ScriptRPC` worked at 256 elements in this build; do not fragment at 64 merely because of the serializer.
- For `ScriptInputUserData`, keep arrays small until a larger run is measured; check `CanStoreInputUserData()` and the return of `Write` before `Send()`.
- On the receiving side, check that `ctx.Read` succeeded and that `values.Count()` matches the declared count before accepting the message.
- For anti-cheat, sequence plus count is useful for idempotency, but add a hash or a per-element check when the values themselves matter.
