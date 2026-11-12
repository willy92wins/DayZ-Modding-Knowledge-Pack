# Script network limits (build 26220720)

Runtime measurements from a local DayZ diag client/server pair. No reverse engineering was used. The numbers describe the tested string payloads on this build, not wire bytes or universal engine limits. The probe source is `P:\NetProbe`; the full evidence and raw log names are in the vault note `AI/20_Knowledge/dayz-script-network-limits-probe.md`.

## ScriptRPC string payload

A repeated ASCII string was sent from the client to the server through a custom `ScriptRPC`; the server read the payload and returned an ACK.

- 1023 ASCII characters were read successfully; 1024 failed in `ctx.Read(blob)`, and the server still sent an ACK. [EXACT][CLAIM-NET-RPC-ASCII]
- With two-byte UTF-8 `"ñ"`, 511 characters (`Length()=1022`) were read successfully; 512 characters (`Length()=1024`) failed. [EXACT][CLAIM-NET-RPC-UTF8]

Practical reading: keep `ScriptRPC` string payloads at or below 1023 bytes and fragment larger data. Do not treat an ACK as proof that the payload was read: the ACK was sent even when `ctx.Read` failed.

## ScriptInputUserData string payload

The same payloads were sent through `ScriptInputUserData` and read by the server.

- 143 ASCII characters were accepted; at 144, `CanStoreInputUserData()` was still true but `msg.Write(blob)` returned false and nothing arrived. [EXACT][CLAIM-NET-INPUT-ASCII]
- With two-byte UTF-8 `"ñ"`, 71 and 72 characters (`Length()` 142 and 144) arrived; 143 characters (`Length()=286`) was rejected by `Write`. [EXACT][CLAIM-NET-INPUT-UTF8]

The results are consistent with two limits acting together: at most 143 characters and at most 144 bytes for this string field. The probe did not isolate which limit rejected each case. Treat both as boundaries and always check the return value of `Write`; `CanStoreInputUserData()==true` is not enough.

## Input queue

Ten input messages were sent in one frame for payload sizes of 1, 16, 64, 128 and 143 characters.

- In every size, `CanStoreInputUserData()` was true for the first four messages and false from the fifth; the server received four. [EXACT][CLAIM-NET-QUEUE]

Practical reading: the observed capacity was four messages, not a byte budget; payload size did not change the count in this range. Check the gate before sending and retry after the queue drains.

## RPC burst and ordering

Ten small RPCs were sent, alternating `guaranteed=true` and `guaranteed=false`.

- All ten arrived and all ten ACKs were received, but the guaranteed messages arrived before the unguaranteed ones; the original interleaving was not preserved. [EXACT][CLAIM-NET-ORDER]

Practical reading: carry a sequence number and make handlers idempotent; do not rely on send order across reliability modes.

## ACK semantics

The server ACK was a small RPC carrying sequence and declared size, not the payload.

- An ACK arrived for RPC payloads whose `ctx.Read(blob)` had failed, including 1024 and 2048 ASCII characters. [EXACT][CLAIM-NET-ACK]

Practical reading: ACK means the RPC envelope reached the handler, not that the payload was read. For anti-cheat and state sync, send the ACK only after `ctx.Read` succeeds, and bind it to the sequence, the actual received length and a hash/checksum of the received content; a declared length or a small ACK alone does not prove payload integrity.

## Measurement scope

- Local loopback client/server on one machine; no packet loss or Internet latency.
- Strings only: ASCII and two-byte UTF-8; arrays, integers and binary serialization were not measured.
- `Length()` returned bytes for UTF-8; the exact wire overhead was not measured.
- No fragmentation, no real-loss test, no reverse engineering.
- Build 26220720; the probe PBO and source hashes are recorded in the vault note.
