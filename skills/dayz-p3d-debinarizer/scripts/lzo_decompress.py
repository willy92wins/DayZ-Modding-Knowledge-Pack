"""LZO1X stream decompressor for BI ODOL format (canonical reference port).

Faithful translation of the reference lzo1x_decompress C routine. Replaces the
previous hand-rolled port which desynced on certain streams (observed: ODOL v53
Croco quadbike.p3d Geometry LOD — desynced with "Unexpected t<16 in match
sequence" before reaching any M4 match, i.e. independent of the M4 variant).

Variant flag `std_m4`:
  False (default) = BI variant: no -0x4000 in M4 offset (DayZ v54/v55 behaviour).
  True            = standard LZO1X: subtract 0x4000 in M4 offset.
For small blocks (< 16 KB back-reference window) the two are identical because
M4 long-distance matches are never emitted.

Public API unchanged: decompress_lzo(data, offset, expected_size) -> (bytes, consumed)
"""

class LZOError(Exception):
    pass


def _core(data, offset, dst_len, std_m4):
    M2 = 0x0800
    ip = offset
    op = 0
    out = bytearray(dst_len)

    # ---- entry: first_literal_run handling ----
    t = data[ip]
    if t > 17:
        t = t - 17
        ip += 1
        if t < 4:
            # match_next: copy t literals then read a match code
            for _ in range(t):
                out[op] = data[ip]; op += 1; ip += 1
            t = data[ip]; ip += 1
            mode = 'match'
        else:
            for _ in range(t):
                out[op] = data[ip]; op += 1; ip += 1
            mode = 'first_literal_run'
    else:
        mode = 'top'

    while True:
        if mode == 'top':
            t = data[ip]; ip += 1
            if t >= 16:
                mode = 'match'
            else:
                if t == 0:
                    while data[ip] == 0:
                        t += 255; ip += 1
                    t += 15 + data[ip]; ip += 1
                n = t + 3
                out[op:op+n] = data[ip:ip+n]; op += n; ip += n
                mode = 'first_literal_run'

        if mode == 'first_literal_run':
            t = data[ip]; ip += 1
            if t >= 16:
                mode = 'match'
            else:
                m_pos = op - (1 + M2) - (t >> 2) - (data[ip] << 2); ip += 1
                if m_pos < 0 or m_pos >= op:
                    raise LZOError(f"overrun M1-first m_pos={m_pos} op={op}")
                out[op] = out[m_pos]; op += 1
                out[op] = out[m_pos+1]; op += 1
                out[op] = out[m_pos+2]; op += 1
                mode = 'match_done'

        if mode == 'match':
            if t >= 64:
                m_pos = op - 1 - ((t >> 2) & 7) - (data[ip] << 3); ip += 1
                m_len = (t >> 5) - 1
            elif t >= 32:
                m_len = t & 31
                if m_len == 0:
                    while data[ip] == 0:
                        m_len += 255; ip += 1
                    m_len += 31 + data[ip]; ip += 1
                m_pos = op - 1 - ((data[ip] >> 2) + (data[ip+1] << 6)); ip += 2
            elif t >= 16:
                m_pos = op - ((t & 8) << 11)
                m_len = t & 7
                if m_len == 0:
                    while data[ip] == 0:
                        m_len += 255; ip += 1
                    m_len += 7 + data[ip]; ip += 1
                m_pos -= (data[ip] >> 2) + (data[ip+1] << 6); ip += 2
                if m_pos == op:
                    return bytes(out[:op]), ip - offset   # EOF marker
                if std_m4:
                    m_pos -= 0x4000
            else:
                # t < 16 : M1 (2-byte) match
                m_pos = op - 1 - (t >> 2) - (data[ip] << 2); ip += 1
                if m_pos < 0 or m_pos >= op:
                    raise LZOError(f"overrun M1 m_pos={m_pos} op={op}")
                out[op] = out[m_pos]; op += 1
                out[op] = out[m_pos+1]; op += 1
                mode = 'match_done'
                # jump to trailer directly
                t = data[ip-2] & 3
                if t == 0:
                    mode = 'top'; continue
                for _ in range(t):
                    out[op] = data[ip]; op += 1; ip += 1
                t = data[ip]; ip += 1
                mode = 'match'; continue

            if m_pos < 0 or m_pos >= op:
                raise LZOError(f"overrun match m_pos={m_pos} op={op}")
            for j in range(m_len + 2):
                out[op] = out[m_pos + j]; op += 1
            mode = 'match_done'

        if mode == 'match_done':
            t = data[ip-2] & 3
            if t == 0:
                mode = 'top'; continue
            for _ in range(t):
                out[op] = data[ip]; op += 1; ip += 1
            t = data[ip]; ip += 1
            mode = 'match'; continue


def decompress_lzo(data, offset, expected_size, std_m4=False):
    """Public entry point. Decompress an LZO1X block; also consume a trailing
    EOF marker (b'\\x11\\x00\\x00') if the core stopped just before it."""
    result, consumed = _core(data, offset, expected_size, std_m4)
    end = offset + consumed
    if end + 3 <= len(data) and data[end] == 0x11 and data[end+1] == 0 and data[end+2] == 0:
        consumed += 3
    return result, consumed
