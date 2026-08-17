# Motion quality contract

The contract separates sampling from judgment. `sample_blender_motion.py` evaluates scene data into a neutral report. `validate_motion_contract.py` evaluates that report against checks. This lets unit fixtures run without Blender and prevents a scene-specific script from silently defining its own success.

## Report schema v1

```json
{
  "schema_version": 1,
  "metadata": {
    "fps": 30.0,
    "frame_start": 0,
    "frame_end": 290,
    "action_bindings": [{"object": "Rig", "action": "clip", "frame_start": 0.0, "frame_end": 290.0}]
  },
  "frames": {
    "52": {
      "points": {"contact": [0.1, 0.2, 0.3]},
      "segments": {"finger2": {"a": [0, 0, 0], "b": [0, 0.03, 0], "radius_m": 0.006}},
      "transforms": {"hand": {"p": [0, 0, 0], "q": [0, 0, 0, 1]}}
    }
  }
}
```

Units are metres, degrees and seconds. JSON quaternions are always `[x,y,z,w]`.

## Blender sampling fields

Top-level sampler fields:

- `sample_frames`: increasing unique integer frames for isolated poses;
- `sample_ranges`: inclusive `{start,end,step}` ranges; use `step: 1` for continuous contact, lock and collision windows;
- `action_bindings`: optional `{object, action}` pairs temporarily assigned and restored;
- `landmarks`: named point specifications;
- `transforms`: named world transforms;
- `segments`: named capsule centre-lines with mandatory non-negative `radius_m`;
- `checks`: ignored by the sampler and consumed by the validator, allowing one file to hold the full task contract.

Landmark types:

- `bone_head`, `bone_tail`, `bone_point` (`factor` in `0..1`);
- `object_origin`;
- `mesh_vertex_centroid` with explicit evaluated-mesh vertex indices;
- `average` with named `sources`;
- optional `offset_world` on any landmark.

Transform types:

- `pose_bone_world`;
- `pose_bone_local` (`matrix_basis`, for joint limits relative to the rest/parent chain);
- `object_world`.

Missing objects, bones, vertices, frames, Actions, radii or non-finite values are invalid input. Frames outside the scene timeline are invalid. They produce exit `2`, never an omitted channel.

## Check catalog

### `timeline`

Checks exact FPS, scene start/end and inclusive frame count. With `require_action_range: true`, every bound Action must expose the same range. Get expected values from the current DayZ contract.

### `point_distance_band`

Checks positive contact or controlled clearance. The measured value is:

`surface_gap = distance(point_a, point_b) - radius_a_m - radius_b_m`

Use `min_m`/`max_m`. A negative gap is penetration; a positive gap above the maximum is separation.

### `segment_clearance`

Computes minimum capsule surface distance. Use explicit `segment_pairs` for anatomy and self-collision so segments of the same chain are never compared accidentally. Cartesian `segments_a`/`segments_b` remains useful for disjoint object groups.

### `ordered_projection`

Projects point groups onto either a fixed `axis` or a per-frame `axis_from_points`. Use several groups along a chain—roots, intermediate joints and tips. Endpoint-only order is insufficient.

### `relative_transform_lock`

Evaluates the target transform in actor-local space on every frame and compares it with the first contact frame. It requires at least two frames. Declare translation and rotation drift tolerances, and use a consecutive `frame_range` for a rigid window. Split windows around an intentional slip or release.

### `joint_angle_range`

Measures quaternion angle from a declared reference. A scalar swing angle cannot distinguish twist from flexion; use this as a coarse guard and add axis-specific/domain review when anatomy is load-bearing.

### `joint_swing_twist_range`

Decomposes a local joint quaternion around a declared local `twist_axis`. Declares signed twist bounds and a maximum swing. Feed it `pose_bone_local`, not a world transform.

### `continuity_limit`

Measures point speed, acceleration and jerk across increasing frames. Declare only limits supported by the action/reference. Impact or snap windows should be excluded or separately contracted.

### `rotation_continuity_limit`

Measures quaternion angular speed, acceleration and jerk as shortest-path rotation vectors. Use local transforms for anatomical stutter and world/object transforms for mechanical stutter.

### `endpoint_match`

Compares named points/transforms at two frames. For loops, add a continuity check around the seam when matching derivatives matters; identical poses alone do not prove a seamless loop.

### `seam_derivative_match`

Compares incoming velocity at the loop end with outgoing velocity at the loop start. It supports point linear velocity or transform linear/angular velocity. This is the derivative gate that complements `endpoint_match`.

## Result semantics

Each check returns:

- `pass` and `required`;
- `worst_frame`;
- `measured` and `limit`;
- an explanatory message.

`overall_pass` is the conjunction of required checks. Optional diagnostics remain visible but cannot disguise a required failure. The result also echoes `contract_mode` and reports `eligible_for_offline_pass`; that field is true only when a production contract passes every required check.

## Tolerance discipline

Choose tolerances from one of these sources, in order:

1. approved reference pose/motion;
2. measured geometry and known surface thickness;
3. verified vanilla clip distribution;
4. explicit user decision recorded in the task contract.

Never derive the tolerance solely from the candidate being judged. Always run a corrected or positive fixture to prove the check is not tautological.

`contract_mode` is required and accepts exactly `diagnostic` or `production`. Contracts that can grant `OFFLINE_PASS` set `contract_mode: "production"`. Every check then requires:

```json
"provenance": {
  "source_kind": "approved_reference | measured_geometry | verified_vanilla | explicit_user_decision",
  "source": "path, asset, capture or recorded decision",
  "verified_date": "YYYY-MM-DD",
  "method": "how the numeric bound was derived"
}
```

If any `segment_clearance` check is present, add `segment_radius_provenance` with the same fields. Production checks for contact, collision, relative lock, ordering, joint range, and continuity must use a consecutive `frame_range` with `step: 1`; explicit or sparse `frames` are diagnostic evidence only. Diagnostic contracts may omit provenance, but they cannot support a production PASS even when `overall_pass` is true.
