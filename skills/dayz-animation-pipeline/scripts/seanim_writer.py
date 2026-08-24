#!/usr/bin/env python3
"""
seanim_writer.py - write (and read, for verification) the SEAnim animation
format. SEAnim is the OPEN bridge format to DayZ's proprietary .anm: author or
edit keyframes here in-sandbox, then the user runs DayZATool --generate-anim
to produce the .anm. (Layer 2 of the dayz-animation-pipeline skill.)

The binary layout below is transcribed field-for-field from the PRIMARY source,
SE2Dev/io_anim_seanim seanim.py:
  https://raw.githubusercontent.com/SE2Dev/io_anim_seanim/master/seanim.py
Nothing here is guessed. The --self-test round-trips a file (write -> read ->
assert equal) AND checks the on-disk structure (magic, header size, key data),
so a regression in the layout is caught immediately rather than silently
producing a .seanim that DayZATool rejects.

File layout (in order):
  [Info  8B ] b'SEAnim' (6) + version int16 (=1)
  [Header   ] headerSize int16 (=28) + 26B payload '=6BfII4BI'
  [Names    ] boneCount x null-terminated UTF-8
  [Modifiers] boneAnimModifierCount x (bone_index:bone_t + modifier:u8)
  [Bone data] boneCount x { flags:u8, [loc][rot][scale] blocks }
  [Notes    ] if note bit: noteCount x (frame:frame_t + name:nul-UTF-8)

A loc/scale block is: keyCount(frame_t) then keyCount x (frame:frame_t, 3xfloat32).
A rot block is:       keyCount(frame_t) then keyCount x (frame:frame_t, 4xfloat32 XYZW).
Endianness: little-endian.

API:
  write_seanim(path, bones, framerate=30.0, looped=False, anim_type=0, notes=None)
    bones: list of {"name": str,
                    "pos_keys":  [(frame:int, (x,y,z)), ...],     # optional
                    "rot_keys":  [(frame:int, (x,y,z,w)), ...],   # optional, XYZW
                    "scale_keys":[(frame:int, (x,y,z)), ...]}     # optional
  read_seanim(path) -> dict  (for verification / editing round-trips)
"""
import struct
import sys

MAGIC = b"SEAnim"
VERSION = 1

SEANIM_BONE_LOC = 1 << 0
SEANIM_BONE_ROT = 1 << 1
SEANIM_BONE_SCALE = 1 << 2
SEANIM_PRESENCE_NOTE = 1 << 6
SEANIM_FLAG_LOOPED = 1 << 0

HEADER_PAYLOAD_FMT = "=6BfII4BI"  # 26 bytes; see seanim.py Header


def _frame_char(frame_count):
    if frame_count <= 0xFF:
        return "B"
    if frame_count <= 0xFFFF:
        return "H"
    return "I"


def write_seanim(path, bones, framerate=30.0, looped=False, anim_type=0, notes=None):
    notes = notes or []

    # presence flags: set a channel bit globally if ANY bone uses that channel
    presence = 0
    if any(b.get("pos_keys") for b in bones):
        presence |= SEANIM_BONE_LOC
    if any(b.get("rot_keys") for b in bones):
        presence |= SEANIM_BONE_ROT
    if any(b.get("scale_keys") for b in bones):
        presence |= SEANIM_BONE_SCALE
    if notes:
        presence |= SEANIM_PRESENCE_NOTE

    # frame count = max key/note frame index + 1
    max_frame = 0
    for b in bones:
        for grp in ("pos_keys", "rot_keys", "scale_keys"):
            for fr, _ in b.get(grp, []):
                max_frame = max(max_frame, fr)
    for fr, _ in notes:
        max_frame = max(max_frame, fr)
    frame_count = max_frame + 1

    bone_count = len(bones)
    fc = _frame_char(frame_count)
    anim_flags = SEANIM_FLAG_LOOPED if looped else 0
    data_property_flags = 0  # float32 precision (no SEANIM_PRECISION_HIGH)
    bone_modifier_count = 0  # not emitted by this writer (v1)

    buf = bytearray()
    # Info
    buf += MAGIC
    buf += struct.pack("<h", VERSION)
    # Header: payload then prepend size
    payload = struct.pack(
        HEADER_PAYLOAD_FMT,
        anim_type, anim_flags, presence, data_property_flags, 0, 0,
        float(framerate), frame_count, bone_count,
        bone_modifier_count, 0, 0, 0,
        len(notes),
    )
    header_size = len(payload) + 2  # the reader does read(headerSize-2)
    buf += struct.pack("<h", header_size)
    buf += payload
    # Bone names (null-terminated UTF-8, in order)
    for b in bones:
        nm = b["name"].encode("utf-8")
        buf += struct.pack("%ds" % (len(nm) + 1), nm)
    # Bone anim modifiers: none (bone_modifier_count == 0)
    # Per-bone keyframe data
    for b in bones:
        buf += struct.pack("B", 0)  # per-bone flags (unused here)
        if presence & SEANIM_BONE_LOC:
            keys = b.get("pos_keys", [])
            buf += struct.pack(fc, len(keys))
            for fr, (x, y, z) in keys:
                buf += struct.pack("=" + fc + "3f", fr, x, y, z)
        if presence & SEANIM_BONE_ROT:
            keys = b.get("rot_keys", [])
            buf += struct.pack(fc, len(keys))
            for fr, (x, y, z, w) in keys:
                buf += struct.pack("=" + fc + "4f", fr, x, y, z, w)
        if presence & SEANIM_BONE_SCALE:
            keys = b.get("scale_keys", [])
            buf += struct.pack(fc, len(keys))
            for fr, (x, y, z) in keys:
                buf += struct.pack("=" + fc + "3f", fr, x, y, z)
    # Notes
    if presence & SEANIM_PRESENCE_NOTE:
        for fr, name in notes:
            buf += struct.pack(fc, fr)
            nm = name.encode("utf-8")
            buf += struct.pack("%ds" % (len(nm) + 1), nm)

    with open(path, "wb") as f:
        f.write(buf)
    return bytes(buf)


def _read_cstr(f):
    out = bytearray()
    while True:
        c = f.read(1)
        if c == b"\x00" or c == b"":
            break
        out += c
    return out.decode("utf-8")


def read_seanim(path):
    with open(path, "rb") as f:
        magic = f.read(6)
        if magic != MAGIC:
            raise ValueError("not a SEAnim file (magic=%r)" % magic)
        version = struct.unpack("<h", f.read(2))[0]
        header_size = struct.unpack("<h", f.read(2))[0]
        data = struct.unpack(HEADER_PAYLOAD_FMT, f.read(header_size - 2))
        (anim_type, anim_flags, presence, prop_flags, _r0, _r1,
         framerate, frame_count, bone_count, bone_mod_count,
         _r2, _r3, _r4, note_count) = data
        fc = _frame_char(frame_count)
        names = [_read_cstr(f) for _ in range(bone_count)]
        # modifiers
        bone_char = "B" if bone_count <= 0xFF else ("H" if bone_count <= 0xFFFF else "I")
        for _ in range(bone_mod_count):
            struct.unpack("=" + bone_char + "B", f.read(struct.calcsize("=" + bone_char + "B")))
        bones = []
        for i in range(bone_count):
            f.read(1)  # per-bone flags
            bone = {"name": names[i], "pos_keys": [], "rot_keys": [], "scale_keys": []}
            if presence & SEANIM_BONE_LOC:
                n = struct.unpack(fc, f.read(struct.calcsize(fc)))[0]
                for _ in range(n):
                    rec = struct.unpack("=" + fc + "3f", f.read(struct.calcsize("=" + fc + "3f")))
                    bone["pos_keys"].append((rec[0], (rec[1], rec[2], rec[3])))
            if presence & SEANIM_BONE_ROT:
                n = struct.unpack(fc, f.read(struct.calcsize(fc)))[0]
                for _ in range(n):
                    rec = struct.unpack("=" + fc + "4f", f.read(struct.calcsize("=" + fc + "4f")))
                    bone["rot_keys"].append((rec[0], (rec[1], rec[2], rec[3], rec[4])))
            if presence & SEANIM_BONE_SCALE:
                n = struct.unpack(fc, f.read(struct.calcsize(fc)))[0]
                for _ in range(n):
                    rec = struct.unpack("=" + fc + "3f", f.read(struct.calcsize("=" + fc + "3f")))
                    bone["scale_keys"].append((rec[0], (rec[1], rec[2], rec[3])))
            bones.append(bone)
        notes = []
        if presence & SEANIM_PRESENCE_NOTE:
            for _ in range(note_count):
                fr = struct.unpack(fc, f.read(struct.calcsize(fc)))[0]
                notes.append((fr, _read_cstr(f)))
    return {
        "version": version, "anim_type": anim_type, "looped": bool(anim_flags & SEANIM_FLAG_LOOPED),
        "framerate": framerate, "frame_count": frame_count, "bones": bones, "notes": notes,
    }


def _approx(a, b, eps=1e-5):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


def _self_test():
    # the header payload MUST be 26 bytes or the headerSize value is wrong
    assert struct.calcsize(HEADER_PAYLOAD_FMT) == 26, struct.calcsize(HEADER_PAYLOAD_FMT)
    bones = [
        {"name": "j_hips",
         "pos_keys": [(0, (0.0, 0.0, 0.0)), (10, (0.0, 1.5, 0.0))],
         "rot_keys": [(0, (0.0, 0.0, 0.0, 1.0)), (10, (0.0, 0.707, 0.0, 0.707))]},
        {"name": "j_spine",
         "rot_keys": [(0, (0.0, 0.0, 0.0, 1.0))]},
    ]
    raw = write_seanim("/tmp/_seanim_test.seanim", bones, framerate=30.0,
                       looped=True, notes=[(10, "end")])
    # structural checks
    assert raw[:6] == MAGIC
    assert struct.unpack("<h", raw[6:8])[0] == 1
    assert struct.unpack("<h", raw[8:10])[0] == 28  # headerSize = 26 payload + 2
    # round-trip
    got = read_seanim("/tmp/_seanim_test.seanim")
    assert got["frame_count"] == 11, got["frame_count"]
    assert got["looped"] is True
    assert abs(got["framerate"] - 30.0) < 1e-6
    assert [b["name"] for b in got["bones"]] == ["j_hips", "j_spine"]
    h = got["bones"][0]
    assert len(h["pos_keys"]) == 2 and h["pos_keys"][1][0] == 10
    assert _approx(h["pos_keys"][1][1], (0.0, 1.5, 0.0))
    assert _approx(h["rot_keys"][1][1], (0.0, 0.707, 0.0, 0.707))
    # j_spine has no pos keys but the LOC channel is global -> 0-key block round-trips
    assert got["bones"][1]["pos_keys"] == []
    assert got["notes"] == [(10, "end")]
    print("seanim_writer self-test OK (round-trip + structure verified)")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        sys.stderr.write(__doc__)
        sys.exit(1)
