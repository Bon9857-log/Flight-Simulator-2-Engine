"""
Assemble the Flight Simulator 2.0 - Engine Core project.json.

Single sprite ("Renderer", hidden) holds all logic; the Stage holds the
global variables/lists and a backdrop. All custom blocks are warp (turbo)
mode. Rendering is via the Pen extension: solid back-to-front (painter's
algorithm) triangle fills with simple directional + ambient shading.
"""

import json
import hashlib
import zipfile
import os

from sb3lib import (
    Script, mkblock, new_id, make_procedure, call_procedure, item, var,
    add, sub, mul, div, mod, lt, gt, eq, and_, or_, not_, join_, absf,
    roundf, sqrtf, sinf, cosf, arg_n, key_pressed_expr, two_min, two_max,
    three_min, three_max, clampf, timer_, Lit,
)
import geometry

OUT_DIR = "/home/claude/sb3build"

# ---------------------------------------------------------------------------
# Lookup-table trig helpers (361-entry tables covering 0..360 inclusive)
# ---------------------------------------------------------------------------

def SIN(angle_expr):
    return item("sin_table", add(roundf(mod(angle_expr, 360)), 1))


def COS(angle_expr):
    return item("cos_table", add(roundf(mod(angle_expr, 360)), 1))


# ---------------------------------------------------------------------------
# Global variable / list names
# ---------------------------------------------------------------------------

CONFIG_VARS = [
    "cam_yaw", "cam_pitch", "cam_dist", "model_yaw",
    "focal", "render_dist", "near_clip",
    "light_x", "light_y", "light_z",
    "frame_count", "controls_info", "fps_display",
]

TEMP_VARS = [
    "t_i", "t_j", "t_f", "t_a", "t_b", "t_c",
    "t_mx", "t_my", "t_mz",
    "t_x2", "t_y2", "t_z2", "t_x3", "t_y3", "t_z3",
    "t_nx", "t_ny", "t_nz", "t_nlen", "t_dot", "t_bright",
    "t_fr", "t_fg", "t_fb",
    "t_key", "t_keydepth",
    "t_ymin", "t_ymax", "t_scany", "t_xa", "t_xb", "t_found", "t_tmpx",
    "t_sa", "t_facedepth",
]

ALL_VARS = CONFIG_VARS + TEMP_VARS

VERT_LISTS = ["vx", "vy", "vz", "tx", "ty", "tz", "px", "py", "pvis"]
FACE_LISTS = ["fv1", "fv2", "fv3", "fcr", "fcg", "fcb", "face_depth"]
OTHER_LISTS = ["face_order", "sin_table", "cos_table"]
ALL_LISTS = VERT_LISTS + FACE_LISTS + OTHER_LISTS

N_VERTS = len(geometry.VERTICES)
N_FACES = len(geometry.FACES)


# ---------------------------------------------------------------------------
# Build the Renderer sprite's blocks
# ---------------------------------------------------------------------------

def build_renderer_blocks():
    blocks = {}

    # ---- init_engine -----------------------------------------------------
    body, _ = make_procedure(blocks, "init engine", [], x=0, y=0)
    blocks[body.parent] = blocks[body.parent]  # no-op, keep lint happy

    # trig tables (361 entries: degrees 0..360 inclusive)
    body.add("data_deletealloflist", fields={"LIST": ["sin_table", "sin_table"]})
    body.add("data_deletealloflist", fields={"LIST": ["cos_table", "cos_table"]})
    body.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["t_i", "t_i"]})
    body.add_c("control_repeat", inputs={"TIMES": 361}, body=lambda s: (
        s.add("data_addtolist", inputs={"ITEM": sinf(var("t_i"))}, fields={"LIST": ["sin_table", "sin_table"]}),
        s.add("data_addtolist", inputs={"ITEM": cosf(var("t_i"))}, fields={"LIST": ["cos_table", "cos_table"]}),
        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]}),
    ))

    # vertex data (model space)
    for ln in ("vx", "vy", "vz"):
        body.add("data_deletealloflist", fields={"LIST": [ln, ln]})
    for (_name, x, y, z) in geometry.VERTICES:
        body.add("data_addtolist", inputs={"ITEM": x}, fields={"LIST": ["vx", "vx"]})
        body.add("data_addtolist", inputs={"ITEM": y}, fields={"LIST": ["vy", "vy"]})
        body.add("data_addtolist", inputs={"ITEM": z}, fields={"LIST": ["vz", "vz"]})

    # face data (1-indexed vertex numbers + base colors)
    for ln in ("fv1", "fv2", "fv3", "fcr", "fcg", "fcb"):
        body.add("data_deletealloflist", fields={"LIST": [ln, ln]})
    for (v1, v2, v3, (r, g, b)) in geometry.FACES:
        body.add("data_addtolist", inputs={"ITEM": v1 + 1}, fields={"LIST": ["fv1", "fv1"]})
        body.add("data_addtolist", inputs={"ITEM": v2 + 1}, fields={"LIST": ["fv2", "fv2"]})
        body.add("data_addtolist", inputs={"ITEM": v3 + 1}, fields={"LIST": ["fv3", "fv3"]})
        body.add("data_addtolist", inputs={"ITEM": r}, fields={"LIST": ["fcr", "fcr"]})
        body.add("data_addtolist", inputs={"ITEM": g}, fields={"LIST": ["fcg", "fcg"]})
        body.add("data_addtolist", inputs={"ITEM": b}, fields={"LIST": ["fcb", "fcb"]})

    # per-vertex working lists, zero-filled placeholders
    for ln in ("tx", "ty", "tz", "px", "py", "pvis"):
        body.add("data_deletealloflist", fields={"LIST": [ln, ln]})
    body.add_c("control_repeat", inputs={"TIMES": N_VERTS}, body=lambda s: (
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["tx", "tx"]}),
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["ty", "ty"]}),
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["tz", "tz"]}),
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["px", "px"]}),
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["py", "py"]}),
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["pvis", "pvis"]}),
    ))

    body.add("data_deletealloflist", fields={"LIST": ["face_depth", "face_depth"]})
    body.add_c("control_repeat", inputs={"TIMES": N_FACES}, body=lambda s: (
        s.add("data_addtolist", inputs={"ITEM": 0}, fields={"LIST": ["face_depth", "face_depth"]}),
    ))

    body.add("data_deletealloflist", fields={"LIST": ["face_order", "face_order"]})

    # camera / projection config
    body.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["cam_yaw", "cam_yaw"]})
    body.add("data_setvariableto", inputs={"VALUE": -12}, fields={"VARIABLE": ["cam_pitch", "cam_pitch"]})
    body.add("data_setvariableto", inputs={"VALUE": 260}, fields={"VARIABLE": ["cam_dist", "cam_dist"]})
    body.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["model_yaw", "model_yaw"]})
    body.add("data_setvariableto", inputs={"VALUE": 320}, fields={"VARIABLE": ["focal", "focal"]})
    body.add("data_setvariableto", inputs={"VALUE": 2000}, fields={"VARIABLE": ["render_dist", "render_dist"]})
    body.add("data_setvariableto", inputs={"VALUE": 5}, fields={"VARIABLE": ["near_clip", "near_clip"]})
    # light direction, pre-normalized (1,2,-1)/sqrt(6)
    body.add("data_setvariableto", inputs={"VALUE": 0.408}, fields={"VARIABLE": ["light_x", "light_x"]})
    body.add("data_setvariableto", inputs={"VALUE": 0.816}, fields={"VARIABLE": ["light_y", "light_y"]})
    body.add("data_setvariableto", inputs={"VALUE": -0.408}, fields={"VARIABLE": ["light_z", "light_z"]})
    body.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["frame_count", "frame_count"]})
    body.add("data_setvariableto",
             inputs={"VALUE": Lit("ARROWS: orbit camera  |  Z/X: zoom  |  model auto-rotates")},
             fields={"VARIABLE": ["controls_info", "controls_info"]})
    body.add("data_setvariableto", inputs={"VALUE": Lit("FPS: --")},
             fields={"VARIABLE": ["fps_display", "fps_display"]})
    body.add("sensing_resettimer")

    # ---- transform_vertices ------------------------------------------------
    body, _ = make_procedure(blocks, "transform vertices", [], x=400, y=0)

    def transform_loop(s):
        # --- model spin (rotation about Y, lookup-table based) ---
        s.add("data_setvariableto",
              inputs={"VALUE": sub(mul(item("vx", var("t_i")), COS(var("model_yaw"))),
                                    mul(item("vz", var("t_i")), SIN(var("model_yaw"))))},
              fields={"VARIABLE": ["t_mx", "t_mx"]})
        s.add("data_setvariableto", inputs={"VALUE": item("vy", var("t_i"))},
              fields={"VARIABLE": ["t_my", "t_my"]})
        s.add("data_setvariableto",
              inputs={"VALUE": add(mul(item("vx", var("t_i")), SIN(var("model_yaw"))),
                                    mul(item("vz", var("t_i")), COS(var("model_yaw"))))},
              fields={"VARIABLE": ["t_mz", "t_mz"]})

        # --- camera yaw (rotation about Y by cam_yaw) ---
        s.add("data_setvariableto",
              inputs={"VALUE": sub(mul(var("t_mx"), COS(var("cam_yaw"))),
                                    mul(var("t_mz"), SIN(var("cam_yaw"))))},
              fields={"VARIABLE": ["t_x2", "t_x2"]})
        s.add("data_setvariableto", inputs={"VALUE": var("t_my")},
              fields={"VARIABLE": ["t_y2", "t_y2"]})
        s.add("data_setvariableto",
              inputs={"VALUE": add(mul(var("t_mx"), SIN(var("cam_yaw"))),
                                    mul(var("t_mz"), COS(var("cam_yaw"))))},
              fields={"VARIABLE": ["t_z2", "t_z2"]})

        # --- camera pitch (rotation about X by cam_pitch) ---
        s.add("data_setvariableto",
              inputs={"VALUE": add(mul(var("t_y2"), COS(var("cam_pitch"))),
                                    mul(var("t_z2"), SIN(var("cam_pitch"))))},
              fields={"VARIABLE": ["t_y3", "t_y3"]})
        s.add("data_setvariableto",
              inputs={"VALUE": add(mul(var("t_z2"), COS(var("cam_pitch"))),
                                    mul(var("t_y2"), mul(-1, SIN(var("cam_pitch")))))},
              fields={"VARIABLE": ["t_z3", "t_z3"]})
        s.add("data_setvariableto", inputs={"VALUE": var("t_x2")},
              fields={"VARIABLE": ["t_x3", "t_x3"]})

        # --- store view-space coords (push back by cam_dist) ---
        s.add("data_replaceitemoflist", inputs={"INDEX": var("t_i"), "ITEM": var("t_x3")},
              fields={"LIST": ["tx", "tx"]})
        s.add("data_replaceitemoflist", inputs={"INDEX": var("t_i"), "ITEM": var("t_y3")},
              fields={"LIST": ["ty", "ty"]})
        s.add("data_replaceitemoflist",
              inputs={"INDEX": var("t_i"), "ITEM": add(var("t_z3"), var("cam_dist"))},
              fields={"LIST": ["tz", "tz"]})

        # --- visibility flag (in front of near-clip plane?) ---
        s.add_c("control_if_else",
                inputs={"CONDITION": gt(add(var("t_z3"), var("cam_dist")), var("near_clip"))},
                body=lambda s2: s2.add("data_replaceitemoflist",
                                        inputs={"INDEX": var("t_i"), "ITEM": 1},
                                        fields={"LIST": ["pvis", "pvis"]}),
                body2=lambda s2: s2.add("data_replaceitemoflist",
                                         inputs={"INDEX": var("t_i"), "ITEM": 0},
                                         fields={"LIST": ["pvis", "pvis"]}))

        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})

    body.add("data_setvariableto", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})
    body.add_c("control_repeat", inputs={"TIMES": N_VERTS}, body=transform_loop)

    # ---- project_vertices ----------------------------------------------
    body, _ = make_procedure(blocks, "project vertices", [], x=800, y=0)

    def project_loop(s):
        s.add_c("control_if_else",
                inputs={"CONDITION": eq(item("pvis", var("t_i")), 1)},
                body=lambda s2: (
                    s2.add("data_replaceitemoflist",
                           inputs={"INDEX": var("t_i"),
                                   "ITEM": roundf(div(mul(item("tx", var("t_i")), var("focal")),
                                                       item("tz", var("t_i"))))},
                           fields={"LIST": ["px", "px"]}),
                    s2.add("data_replaceitemoflist",
                           inputs={"INDEX": var("t_i"),
                                   "ITEM": roundf(div(mul(item("ty", var("t_i")), var("focal")),
                                                       item("tz", var("t_i"))))},
                           fields={"LIST": ["py", "py"]}),
                ),
                body2=lambda s2: (
                    s2.add("data_replaceitemoflist", inputs={"INDEX": var("t_i"), "ITEM": 0},
                           fields={"LIST": ["px", "px"]}),
                    s2.add("data_replaceitemoflist", inputs={"INDEX": var("t_i"), "ITEM": 0},
                           fields={"LIST": ["py", "py"]}),
                ))
        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})

    body.add("data_setvariableto", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})
    body.add_c("control_repeat", inputs={"TIMES": N_VERTS}, body=project_loop)

    # ---- compute_visibility (depth + frustum/back-face/distance culling) -
    body, _ = make_procedure(blocks, "compute visibility", [], x=1200, y=0)

    def vis_loop(s):
        s.add("data_setvariableto", inputs={"VALUE": item("fv1", var("t_f"))},
              fields={"VARIABLE": ["t_a", "t_a"]})
        s.add("data_setvariableto", inputs={"VALUE": item("fv2", var("t_f"))},
              fields={"VARIABLE": ["t_b", "t_b"]})
        s.add("data_setvariableto", inputs={"VALUE": item("fv3", var("t_f"))},
              fields={"VARIABLE": ["t_c", "t_c"]})

        # average view-space depth, for painter's-algorithm sort + distance cull
        s.add("data_setvariableto",
              inputs={"VALUE": div(add(add(item("tz", var("t_a")), item("tz", var("t_b"))),
                                        item("tz", var("t_c"))), 3)},
              fields={"VARIABLE": ["t_facedepth", "t_facedepth"]})
        s.add("data_replaceitemoflist", inputs={"INDEX": var("t_f"), "ITEM": var("t_facedepth")},
              fields={"LIST": ["face_depth", "face_depth"]})

        # 2D signed area of the projected triangle -> back-face test.
        # NOTE: sign convention picked for this model's winding order; even
        # if inverted on your machine, back-to-front painter's-algorithm
        # sorting still renders a correct silhouette (just culls the wrong
        # half of faces) - flip this ">" to "<" if the model looks hollow.
        s.add("data_setvariableto",
              inputs={"VALUE": sub(
                  mul(sub(item("px", var("t_b")), item("px", var("t_a"))),
                      sub(item("py", var("t_c")), item("py", var("t_a")))),
                  mul(sub(item("px", var("t_c")), item("px", var("t_a"))),
                      sub(item("py", var("t_b")), item("py", var("t_a")))))},
              fields={"VARIABLE": ["t_sa", "t_sa"]})

        all_visible = and_(eq(item("pvis", var("t_a")), 1),
                            and_(eq(item("pvis", var("t_b")), 1),
                                 eq(item("pvis", var("t_c")), 1)))
        in_range = and_(lt(var("t_facedepth"), var("render_dist")),
                         gt(var("t_facedepth"), var("near_clip")))
        front_facing = gt(var("t_sa"), 0)

        s.add_c("control_if",
                inputs={"CONDITION": and_(and_(all_visible, in_range), front_facing)},
                body=lambda s2: s2.add("data_addtolist", inputs={"ITEM": var("t_f")},
                                        fields={"LIST": ["face_order", "face_order"]}))

        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_f", "t_f"]})

    body.add("data_deletealloflist", fields={"LIST": ["face_order", "face_order"]})
    body.add("data_setvariableto", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_f", "t_f"]})
    body.add_c("control_repeat", inputs={"TIMES": N_FACES}, body=vis_loop)

    # ---- sort_face_order (insertion sort, descending depth = back-to-front)
    body, _ = make_procedure(blocks, "sort face order", [], x=1600, y=0)

    body.add("data_setvariableto", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})
    body.add_c("control_repeat",
               inputs={"TIMES": sub(("data_lengthoflist", {"LIST": ["face_order", "face_order"]}, {}), 1)},
               body=lambda s: (
                   s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]}),
                   s.add("data_setvariableto", inputs={"VALUE": item("face_order", var("t_i"))},
                         fields={"VARIABLE": ["t_key", "t_key"]}),
                   s.add("data_setvariableto", inputs={"VALUE": item("face_depth", var("t_key"))},
                         fields={"VARIABLE": ["t_keydepth", "t_keydepth"]}),
                   s.add("data_setvariableto", inputs={"VALUE": sub(var("t_i"), 1)},
                         fields={"VARIABLE": ["t_j", "t_j"]}),
                   s.add_c("control_repeat_until",
                           inputs={"CONDITION": or_(
                               lt(var("t_j"), 1),
                               gt(item("face_depth", item("face_order", var("t_j"))), -999999999)) },
                           body=lambda s2: None),  # placeholder, replaced below
               ))

    # The repeat-until above needs a body that both checks the sort
    # condition and shifts; rebuild it explicitly to keep the boolean
    # logic and the shift body correctly associated.
    # (Re-do sort_face_order cleanly from scratch below.)
    PROCS_TO_DROP = []
    for bid, blk in list(blocks.items()):
        pass

    # Remove the half-built sort procedure and rebuild correctly.
    _rebuild_sort_face_order(blocks)

    # ---- fill_triangle(x1,y1,x2,y2,x3,y3,cr,cg,cb) -----------------------
    body, A = make_procedure(
        blocks, "fill triangle",
        [("x1", "number"), ("y1", "number"), ("x2", "number"), ("y2", "number"),
         ("x3", "number"), ("y3", "number"), ("cr", "number"), ("cg", "number"), ("cb", "number")],
        x=2000, y=0)

    x1, y1, x2, y2, x3, y3 = A["x1"], A["y1"], A["x2"], A["y2"], A["x3"], A["y3"]
    cr, cg, cb = A["cr"], A["cg"], A["cb"]

    body.add("pen_setPenColorToColor",
             inputs={"COLOR": add(add(mul(cr, 65536), mul(cg, 256)), cb)})
    body.add("pen_setPenSizeTo", inputs={"SIZE": 2})
    body.add("data_setvariableto", inputs={"VALUE": three_min(y1, y2, y3)},
             fields={"VARIABLE": ["t_ymin", "t_ymin"]})
    body.add("data_setvariableto", inputs={"VALUE": three_max(y1, y2, y3)},
             fields={"VARIABLE": ["t_ymax", "t_ymax"]})
    body.add("data_setvariableto", inputs={"VALUE": var("t_ymin")},
             fields={"VARIABLE": ["t_scany", "t_scany"]})

    def edge_check(s, xa, ya, xb, yb):
        cond = and_(and_(gt(var("t_scany"), sub(two_min(ya, yb), 0.001)),
                         lt(var("t_scany"), add(two_max(ya, yb), 0.001))),
                    not_(eq(ya, yb)))
        s.add_c("control_if",
                inputs={"CONDITION": cond},
                body=lambda s2: (
                    s2.add("data_setvariableto",
                           inputs={"VALUE": add(xa, div(mul(sub(var("t_scany"), ya), sub(xb, xa)),
                                                          sub(yb, ya)))},
                           fields={"VARIABLE": ["t_tmpx", "t_tmpx"]}),
                    s2.add_c("control_if_else",
                             inputs={"CONDITION": eq(var("t_found"), 0)},
                             body=lambda s3: (
                                 s3.add("data_setvariableto", inputs={"VALUE": var("t_tmpx")},
                                        fields={"VARIABLE": ["t_xa", "t_xa"]}),
                                 s3.add("data_setvariableto", inputs={"VALUE": 1},
                                        fields={"VARIABLE": ["t_found", "t_found"]}),
                             ),
                             body2=lambda s3: (
                                 s3.add("data_setvariableto", inputs={"VALUE": var("t_tmpx")},
                                        fields={"VARIABLE": ["t_xb", "t_xb"]}),
                                 s3.add("data_setvariableto", inputs={"VALUE": 2},
                                        fields={"VARIABLE": ["t_found", "t_found"]}),
                             )),
                ))

    def scan_body(s):
        s.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["t_found", "t_found"]})
        s.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["t_xa", "t_xa"]})
        s.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["t_xb", "t_xb"]})
        edge_check(s, x1, y1, x2, y2)
        edge_check(s, x2, y2, x3, y3)
        edge_check(s, x3, y3, x1, y1)
        s.add_c("control_if",
                inputs={"CONDITION": eq(var("t_found"), 2)},
                body=lambda s2: (
                    s2.add("pen_penUp"),
                    s2.add("motion_gotoxy", inputs={"X": two_min(var("t_xa"), var("t_xb")), "Y": var("t_scany")}),
                    s2.add("pen_penDown"),
                    s2.add("motion_gotoxy", inputs={"X": two_max(var("t_xa"), var("t_xb")), "Y": var("t_scany")}),
                    s2.add("pen_penUp"),
                ))
        s.add("data_changevariableby", inputs={"VALUE": 2}, fields={"VARIABLE": ["t_scany", "t_scany"]})

    body.add_c("control_repeat_until",
               inputs={"CONDITION": gt(var("t_scany"), var("t_ymax"))},
               body=scan_body)
    body.add("pen_penUp")

    # ---- render_frame -----------------------------------------------------
    body, _ = make_procedure(blocks, "render frame", [], x=2600, y=0)

    def render_loop(s):
        s.add("data_setvariableto", inputs={"VALUE": item("face_order", var("t_i"))},
              fields={"VARIABLE": ["t_f", "t_f"]})
        s.add("data_setvariableto", inputs={"VALUE": item("fv1", var("t_f"))},
              fields={"VARIABLE": ["t_a", "t_a"]})
        s.add("data_setvariableto", inputs={"VALUE": item("fv2", var("t_f"))},
              fields={"VARIABLE": ["t_b", "t_b"]})
        s.add("data_setvariableto", inputs={"VALUE": item("fv3", var("t_f"))},
              fields={"VARIABLE": ["t_c", "t_c"]})

        a, b, c = var("t_a"), var("t_b"), var("t_c")

        def D(L, p, q):
            return sub(item(L, q), item(L, p))

        # face normal (cross product of two edges, in view space)
        s.add("data_setvariableto",
              inputs={"VALUE": sub(mul(D("ty", a, b), D("tz", a, c)), mul(D("tz", a, b), D("ty", a, c)))},
              fields={"VARIABLE": ["t_nx", "t_nx"]})
        s.add("data_setvariableto",
              inputs={"VALUE": sub(mul(D("tz", a, b), D("tx", a, c)), mul(D("tx", a, b), D("tz", a, c)))},
              fields={"VARIABLE": ["t_ny", "t_ny"]})
        s.add("data_setvariableto",
              inputs={"VALUE": sub(mul(D("tx", a, b), D("ty", a, c)), mul(D("ty", a, b), D("tx", a, c)))},
              fields={"VARIABLE": ["t_nz", "t_nz"]})

        s.add("data_setvariableto",
              inputs={"VALUE": two_max(
                  sqrtf(add(add(mul(var("t_nx"), var("t_nx")), mul(var("t_ny"), var("t_ny"))),
                            mul(var("t_nz"), var("t_nz")))),
                  0.001)},
              fields={"VARIABLE": ["t_nlen", "t_nlen"]})

        s.add("data_setvariableto",
              inputs={"VALUE": add(add(
                  mul(div(var("t_nx"), var("t_nlen")), var("light_x")),
                  mul(div(var("t_ny"), var("t_nlen")), var("light_y"))),
                  mul(div(var("t_nz"), var("t_nlen")), var("light_z")))},
              fields={"VARIABLE": ["t_dot", "t_dot"]})

        s.add("data_setvariableto",
              inputs={"VALUE": clampf(add(0.5, mul(0.5, var("t_dot"))), 0.3, 1)},
              fields={"VARIABLE": ["t_bright", "t_bright"]})

        s.add("data_setvariableto", inputs={"VALUE": roundf(mul(item("fcr", var("t_f")), var("t_bright")))},
              fields={"VARIABLE": ["t_fr", "t_fr"]})
        s.add("data_setvariableto", inputs={"VALUE": roundf(mul(item("fcg", var("t_f")), var("t_bright")))},
              fields={"VARIABLE": ["t_fg", "t_fg"]})
        s.add("data_setvariableto", inputs={"VALUE": roundf(mul(item("fcb", var("t_f")), var("t_bright")))},
              fields={"VARIABLE": ["t_fb", "t_fb"]})

        call_procedure(s, "fill triangle", [
            item("px", a), item("py", a), item("px", b), item("py", b), item("px", c), item("py", c),
            var("t_fr"), var("t_fg"), var("t_fb"),
        ])

        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})

    body.add("pen_clear")
    body.add("data_setvariableto", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})
    body.add_c("control_repeat",
               inputs={"TIMES": ("data_lengthoflist", {"LIST": ["face_order", "face_order"]}, {})},
               body=render_loop)

    # ---- main loop ----------------------------------------------------
    main = Script(blocks)
    main.add_top("event_whenflagclicked", x=0, y=-400)
    call_procedure(main, "init engine", [])
    main.add("sensing_resettimer")
    main.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["frame_count", "frame_count"]})

    def forever_body(s):
        # --- camera + input handling ---
        s.add_c("control_if", inputs={"CONDITION": key_pressed_expr("left arrow")},
                body=lambda s2: s2.add("data_changevariableby", inputs={"VALUE": -3},
                                        fields={"VARIABLE": ["cam_yaw", "cam_yaw"]}))
        s.add_c("control_if", inputs={"CONDITION": key_pressed_expr("right arrow")},
                body=lambda s2: s2.add("data_changevariableby", inputs={"VALUE": 3},
                                        fields={"VARIABLE": ["cam_yaw", "cam_yaw"]}))

        def pitch_change(s2, delta):
            s2.add("data_changevariableby", inputs={"VALUE": delta}, fields={"VARIABLE": ["cam_pitch", "cam_pitch"]})
            s2.add("data_setvariableto", inputs={"VALUE": clampf(var("cam_pitch"), -80, 60)},
                   fields={"VARIABLE": ["cam_pitch", "cam_pitch"]})

        s.add_c("control_if", inputs={"CONDITION": key_pressed_expr("up arrow")},
                body=lambda s2: pitch_change(s2, -2))
        s.add_c("control_if", inputs={"CONDITION": key_pressed_expr("down arrow")},
                body=lambda s2: pitch_change(s2, 2))

        def zoom_change(s2, delta):
            s2.add("data_changevariableby", inputs={"VALUE": delta}, fields={"VARIABLE": ["cam_dist", "cam_dist"]})
            s2.add("data_setvariableto", inputs={"VALUE": clampf(var("cam_dist"), 120, 700)},
                   fields={"VARIABLE": ["cam_dist", "cam_dist"]})

        s.add_c("control_if", inputs={"CONDITION": key_pressed_expr("z")},
                body=lambda s2: zoom_change(s2, -6))
        s.add_c("control_if", inputs={"CONDITION": key_pressed_expr("x")},
                body=lambda s2: zoom_change(s2, 6))

        s.add("data_changevariableby", inputs={"VALUE": 0.6}, fields={"VARIABLE": ["model_yaw", "model_yaw"]})

        # --- engine pipeline ---
        call_procedure(s, "transform vertices", [])
        call_procedure(s, "project vertices", [])
        call_procedure(s, "compute visibility", [])
        call_procedure(s, "sort face order", [])
        call_procedure(s, "render frame", [])

        # --- fps display, updated once per second ---
        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["frame_count", "frame_count"]})
        s.add_c("control_if",
                inputs={"CONDITION": gt(timer_(), 1)},
                body=lambda s2: (
                    s2.add("data_setvariableto",
                           inputs={"VALUE": join_(Lit("FPS: "), roundf(div(var("frame_count"), timer_())))},
                           fields={"VARIABLE": ["fps_display", "fps_display"]}),
                    s2.add("data_setvariableto", inputs={"VALUE": 0}, fields={"VARIABLE": ["frame_count", "frame_count"]}),
                    s2.add("sensing_resettimer"),
                ))

    main.add_c("control_forever", body=forever_body)

    # merge main's blocks (they were created directly into `blocks`)
    return blocks


def _rebuild_sort_face_order(blocks):
    """Remove any partially-built 'sort face order' blocks and build cleanly."""
    # Find and remove the definition/prototype + body for "sort face order"
    to_remove = set()
    target_proccode = None
    for bid, blk in blocks.items():
        if blk.get("opcode") == "procedures_prototype":
            mut = blk.get("mutation", {})
            if mut.get("proccode", "").startswith("sort face order"):
                target_proccode = mut["proccode"]
    if target_proccode is None:
        return

    # Walk from each procedures_definition whose prototype matches, removing
    # the whole connected stack (definition + chained body via 'next').
    def collect(bid, seen):
        if bid is None or bid in seen or bid not in blocks:
            return
        seen.add(bid)
        blk = blocks[bid]
        nxt = blk.get("next")
        if nxt:
            collect(nxt, seen)
        for key, inp in blk.get("inputs", {}).items():
            if isinstance(inp, list) and len(inp) >= 2 and isinstance(inp[1], str):
                collect(inp[1], seen)
            if isinstance(inp, list) and len(inp) >= 3 and isinstance(inp[1], str):
                collect(inp[1], seen)
        if blk.get("opcode") == "procedures_definition":
            proto = blk["inputs"].get("custom_block")
            if proto and isinstance(proto[1], str):
                collect(proto[1], seen)

    for bid, blk in list(blocks.items()):
        if blk.get("opcode") == "procedures_definition":
            proto_id = blk["inputs"]["custom_block"][1]
            proto = blocks.get(proto_id, {})
            if proto.get("mutation", {}).get("proccode") == target_proccode:
                seen = set()
                collect(bid, seen)
                to_remove |= seen

    for bid in to_remove:
        blocks.pop(bid, None)

    from sb3lib import PROCS
    for name in list(PROCS.keys()):
        if PROCS[name]["proccode"] == target_proccode:
            del PROCS[name]

    # Now build it cleanly.
    body, _ = make_procedure(blocks, "sort face order", [], x=1600, y=0)

    body.add("data_setvariableto", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})

    def outer_body(s):
        s.add("data_changevariableby", inputs={"VALUE": 1}, fields={"VARIABLE": ["t_i", "t_i"]})
        s.add("data_setvariableto", inputs={"VALUE": item("face_order", var("t_i"))},
              fields={"VARIABLE": ["t_key", "t_key"]})
        s.add("data_setvariableto", inputs={"VALUE": item("face_depth", var("t_key"))},
              fields={"VARIABLE": ["t_keydepth", "t_keydepth"]})
        s.add("data_setvariableto", inputs={"VALUE": sub(var("t_i"), 1)},
              fields={"VARIABLE": ["t_j", "t_j"]})

        shift_cond = or_(lt(var("t_j"), 1),
                          gt(item("face_depth", item("face_order", var("t_j"))), var("t_keydepth")))

        def shift_body(s2):
            s2.add_c("control_if",
                     inputs={"CONDITION": gt(var("t_j"), 0)},
                     body=lambda s3: (
                         s3.add_c("control_if",
                                  inputs={"CONDITION": lt(item("face_depth", item("face_order", var("t_j"))),
                                                           var("t_keydepth"))},
                                  body=lambda s4: (
                                      s4.add("data_replaceitemoflist",
                                             inputs={"INDEX": add(var("t_j"), 1),
                                                     "ITEM": item("face_order", var("t_j"))},
                                             fields={"LIST": ["face_order", "face_order"]}),
                                      s4.add("data_changevariableby", inputs={"VALUE": -1},
                                             fields={"VARIABLE": ["t_j", "t_j"]}),
                                  )),
                     ))

        # repeat-until: stop once j<1 OR face_depth[face_order[j]] <= keydepth
        # (we shift while face_depth[face_order[j]] < keydepth, i.e. nearer
        # faces, since we sort farthest-first for the painter's algorithm)
        s.add_c("control_repeat_until",
                inputs={"CONDITION": or_(
                    lt(var("t_j"), 1),
                    not_(lt(item("face_depth", item("face_order", var("t_j"))), var("t_keydepth"))))},
                body=lambda s2: (
                    s2.add("data_replaceitemoflist",
                           inputs={"INDEX": add(var("t_j"), 1), "ITEM": item("face_order", var("t_j"))},
                           fields={"LIST": ["face_order", "face_order"]}),
                    s2.add("data_changevariableby", inputs={"VALUE": -1}, fields={"VARIABLE": ["t_j", "t_j"]}),
                ))

        s.add("data_replaceitemoflist", inputs={"INDEX": add(var("t_j"), 1), "ITEM": var("t_key")},
              fields={"LIST": ["face_order", "face_order"]})

    body.add_c("control_repeat",
               inputs={"TIMES": sub(("data_lengthoflist", {"LIST": ["face_order", "face_order"]}, {}), 1)},
               body=outer_body)


# ---------------------------------------------------------------------------
# Costumes (SVG)
# ---------------------------------------------------------------------------

BACKDROP_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="480" height="360" '
    'viewBox="0 0 480 360"><rect width="480" height="360" fill="#11141f"/></svg>'
)

SPRITE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="2" height="2" '
    'viewBox="0 0 2 2"></svg>'
)


def md5_of(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Assemble project.json
# ---------------------------------------------------------------------------

def main():
    renderer_blocks = build_renderer_blocks()

    variables = {name: [name, 0] for name in ALL_VARS}
    # string-typed initial values for the two display vars
    variables["controls_info"] = ["controls_info", "ARROWS: orbit camera  |  Z/X: zoom  |  model auto-rotates"]
    variables["fps_display"] = ["fps_display", "FPS: --"]

    lists = {name: [name, []] for name in ALL_LISTS}

    backdrop_hash = md5_of(BACKDROP_SVG)
    sprite_hash = md5_of(SPRITE_SVG)

    # Create output directory if it doesn't exist
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(OUT_DIR, f"{backdrop_hash}.svg"), "w") as f:
        f.write(BACKDROP_SVG)
    with open(os.path.join(OUT_DIR, f"{sprite_hash}.svg"), "w") as f:
        f.write(SPRITE_SVG)

    stage = {
        "isStage": True,
        "name": "Stage",
        "variables": variables,
        "lists": lists,
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [{
            "assetId": backdrop_hash, "name": "backdrop1",
            "md5ext": f"{backdrop_hash}.svg", "dataFormat": "svg",
            "rotationCenterX": 240, "rotationCenterY": 180,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "on",
        "textToSpeechLanguage": None,
    }

    # comments on key procedures, for readability in the Scratch editor
    comment_targets = {
        "init engine": "Builds the 361-entry sin/cos lookup tables, loads the\n"
                        "Darkstar's 11 vertices / 16 faces, zero-fills the\n"
                        "per-frame working lists, and sets default camera /\n"
                        "projection / lighting constants. Runs once.",
        "transform vertices": "3D ENGINE - core transform stage.\n"
                               "For each vertex: rotate by model_yaw (the\n"
                               "aircraft's own orientation - will be driven by\n"
                               "flight physics later), then by the orbit\n"
                               "camera's yaw and pitch, then push back by\n"
                               "cam_dist. All rotations use the sin/cos lookup\n"
                               "tables (precomputed trig). Sets pvis[i] for\n"
                               "near-plane (frustum) culling.",
        "project vertices": "3D ENGINE - perspective projection.\n"
                             "screenX = x * focal / z,  screenY = y * focal / z.\n"
                             "Scratch's stage coords already match (X-right,\n"
                             "Y-up, origin at center), so px/py map directly to\n"
                             "pen coordinates with no extra flips.",
        "compute visibility": "CULLING - builds face_order with only the faces\n"
                               "that should be drawn this frame:\n"
                               " - all 3 verts in front of the near-clip plane\n"
                               " - average depth within render_dist\n"
                               " - back-face cull via 2D signed-area test\n"
                               "Also records each face's average view-space Z\n"
                               "into face_depth for the depth sort below.",
        "sort face order": "Insertion sort of face_order by face_depth,\n"
                            "farthest-first - this is the painter's algorithm:\n"
                            "drawing back-to-front means nearer solid polygons\n"
                            "correctly overwrite farther ones.",
        "fill triangle": "RASTERIZER - scanline polygon fill.\n"
                          "Packs (cr,cg,cb) into one 24-bit pen color\n"
                          "(r*65536 + g*256 + b), then for each screen row\n"
                          "(stepping by 2px for performance) finds the two\n"
                          "edge/scanline intersections and draws a solid pen\n"
                          "line between them. Reusable for ANY triangle -\n"
                          "terrain, other aircraft, UI panels, etc.",
        "render frame": "RENDER - for each visible face (back-to-front):\n"
                         "computes the view-space face normal, normalizes it,\n"
                         "dots it with the light direction for simple\n"
                         "ambient+directional shading, then calls fill\n"
                         "triangle with the shaded color and the 3 projected\n"
                         "screen coordinates.",
    }

    comments = {}
    for bid, blk in renderer_blocks.items():
        if blk.get("opcode") == "procedures_definition":
            proto_id = blk["inputs"]["custom_block"][1]
            proto = renderer_blocks.get(proto_id, {})
            proccode = proto.get("mutation", {}).get("proccode", "")
            base = proccode.split(" %")[0]
            if base in comment_targets:
                cid = new_id()
                comments[cid] = {
                    "blockId": bid,
                    "x": blk.get("x", 0) - 20, "y": blk.get("y", 0) - 140,
                    "width": 340, "height": 130,
                    "minimized": False,
                    "text": comment_targets[base],
                }

    main_loop_comment_id = new_id()
    # find the whenflagclicked block
    for bid, blk in renderer_blocks.items():
        if blk.get("opcode") == "event_whenflagclicked":
            comments[main_loop_comment_id] = {
                "blockId": bid,
                "x": blk.get("x", 0) - 20, "y": blk.get("y", 0) - 160,
                "width": 360, "height": 150,
                "minimized": False,
                "text": "MAIN LOOP - orbit-camera controls (arrows + Z/X "
                        "zoom), advances the aircraft's auto-spin, then runs\n"
                        "the full per-frame pipeline:\n"
                        "transform -> project -> cull/sort -> render.\n"
                        "Also updates the on-screen FPS counter once/second.",
            }

    renderer = {
        "isStage": False,
        "name": "Renderer",
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": renderer_blocks,
        "comments": comments,
        "currentCostume": 0,
        "costumes": [{
            "assetId": sprite_hash, "name": "blank",
            "md5ext": f"{sprite_hash}.svg", "dataFormat": "svg",
            "rotationCenterX": 1, "rotationCenterY": 1,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 1,
        "visible": False,
        "x": 0, "y": 0,
        "size": 100,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }

    project = {
        "targets": [stage, renderer],
        "monitors": [
            {
                "id": "controls_info", "mode": "default", "opcode": "data_variable",
                "params": {"VARIABLE": "controls_info"}, "spriteName": None,
                "value": "ARROWS: orbit camera  |  Z/X: zoom  |  model auto-rotates",
                "width": 0, "height": 0, "x": 5, "y": 5, "visible": True,
                "sliderMin": 0, "sliderMax": 100, "isDiscrete": True,
            },
            {
                "id": "fps_display", "mode": "default", "opcode": "data_variable",
                "params": {"VARIABLE": "fps_display"}, "spriteName": None,
                "value": "FPS: --",
                "width": 0, "height": 0, "x": 5, "y": 35, "visible": True,
                "sliderMin": 0, "sliderMax": 100, "isDiscrete": True,
            },
        ],
        "extensions": ["pen"],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agentType": "Scratch"},
    }

    with open(os.path.join(OUT_DIR, "project.json"), "w") as f:
        json.dump(project, f)

    # zip into .sb3
    sb3_path = os.path.join(OUT_DIR, "Flight_Simulator_2_Engine_Core.sb3")
    with zipfile.ZipFile(sb3_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(OUT_DIR, "project.json"), "project.json")
        z.write(os.path.join(OUT_DIR, f"{backdrop_hash}.svg"), f"{backdrop_hash}.svg")
        z.write(os.path.join(OUT_DIR, f"{sprite_hash}.svg"), f"{sprite_hash}.svg")

    print("Wrote", sb3_path)
    print("Blocks in Renderer target:", len(renderer_blocks))
    print("Variables:", len(variables), "Lists:", len(lists))


if __name__ == "__main__":
    main()
