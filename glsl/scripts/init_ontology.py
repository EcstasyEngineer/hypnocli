#!/usr/bin/env python3
"""
init_ontology.py
----------------
Bootstrap glsl/ontology.json with layered technique and quality trees.

Layers (explicit in each node):
  geometry      — the mathematical field/structure (radial, noise, flow, etc.)
  colorization  — how field values map to color (ONE selected per shader)
  shaping       — post-processing modifiers (contrast, glow, gamma)
  timing        — animation rhythm tricks (decoupled speeds, precision)
  meta          — archetypes, quality dims, constraints, priors

Run once to initialize. Safe to re-run — will not overwrite unless --force.
"""

import argparse
import json
from pathlib import Path

GLSL_DIR = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = GLSL_DIR / "ontology.json"


def node(id_, type_, parent, label, description, layer="meta", **kwargs):
    return {
        "id": id_,
        "type": type_,
        "parent": parent,
        "layer": layer,
        "label": label,
        "description": description,
        "score": 0.0,
        "confidence": 0,
        "active": True,
        "retired": False,
        "flag_for_review": False,
        "sample_shader_ids": [],
        **kwargs,
    }


def build_ontology():
    nodes = []

    # ── Archetypes ────────────────────────────────────────────────────────────
    archetypes = [
        ("convergent",         "Convergent spiral",    "Radial inversion pulls gaze to vanishing center."),
        ("linear_rings",       "Linear rings / beat",  "Counter-rotating arms create moiré beat pattern."),
        ("log_arms",           "Log-arm galaxy",       "Logarithmic spiral arms mimic natural galaxy depth cues."),
        ("sdf_outline",        "SDF isoline glow",     "Signed-distance isoline structure with glow falloff."),
        ("kaleidoscopic",      "Kaleidoscope fold",    "N-fold mirror symmetry diffuses focal point."),
        ("domain_warped",      "Domain-warped fBm",    "Triple-warp Quilez fBm; organic flow, no repeating tiles."),
        ("fractal_zoom",       "Fractal zoom",         "Exponential Mandelbrot zoom; scale invariance prevents depth calibration."),
        ("reflective_capture", "Reflective sphere",    "Convex mirror enclosure archetype; distorted self-reflection."),
        ("flow_field",         "Flow field",           "Velocity potential Φ = Σ±log(r); rings expand from sources, contract into sinks."),
    ]
    for id_, label, desc in archetypes:
        nodes.append(node(
            f"archetypes/{id_}", "archetype", "archetypes", label, desc, layer="meta",
            prompt_fragment=f"Use the {label.lower()} archetype as your primary visual structure.",
        ))

    # ── LAYER: geometry / radial ───────────────────────────────────────────────
    for id_, label, desc, pf in [
        ("inversion_sqrt",   "Sqrt inversion",   "1/(r+ε) compresses outer ring toward center",
         "Use sqrt-based radial inversion: r_inv = 1.0/(r + 0.01) to compress outer distance toward center."),
        ("inversion_linear", "Linear inversion", "Sign-flip on radius phase for counter-rotation",
         "Use linear radial inversion via negated phase offset to create counter-rotating symmetry."),
        ("log_shear",        "Log shear",        "log_r = log(r+ε)*k for logarithmic spiral winding",
         "Use log(r) as the radial coordinate to create logarithmic spiral self-similarity."),
        ("raw_linear",       "Raw linear r",     "r used directly without transformation",
         "Use raw linear radius r as the radial coordinate."),
    ]:
        nodes.append(node(f"techniques/radial/{id_}", "technique", "techniques/radial",
                          label, desc, layer="geometry", prompt_fragment=pf))

    # ── LAYER: geometry / angular ─────────────────────────────────────────────
    for id_, label, desc, pf in [
        ("arm_count",     "Arm count",     "N arms via atan*N/(2π)",
         "Set arm_count = N (3–6 recommended) to control the number of spiral arms or fold sectors."),
        ("spiral_offset", "Spiral offset", "log_r*k added to angular phase for winding",
         "Add log(r) * tightness to the angular phase to wind arms into a logarithmic spiral."),
        ("sdf_analytic",  "SDF analytic",  "sdSpiral(): distance to nearest spiral arm",
         "Compute analytic signed distance to the nearest spiral arm isoline for sharp glow edges."),
    ]:
        nodes.append(node(f"techniques/angular/{id_}", "technique", "techniques/angular",
                          label, desc, layer="geometry", prompt_fragment=pf))

    # ── LAYER: geometry / noise ───────────────────────────────────────────────
    for id_, label, desc, pf in [
        ("fbm_single",       "fBm single",      "6-octave fBm on Cartesian UVs",
         "Use 6-octave fractional Brownian motion on Cartesian UVs as a base noise layer."),
        ("fbm_triple_warp",  "fBm triple warp", "Quilez triple-domain-warp: f(p+f(p+f(p)))",
         "Use Inigo Quilez's triple domain warp for organic non-repeating flow."),
        ("fbm_polar",        "fBm polar",       "fBm on (r,θ) polar coords; no grid artifacts",
         "Apply fBm in polar coordinates to avoid rectangular grid artifacts."),
        ("domain_repetition","Domain repetition","Rotated lattice mat2 to break axis-aligned tiling",
         "Use a rotated lattice matrix in fBm octave steps to break axis-aligned tiling."),
    ]:
        nodes.append(node(f"techniques/noise/{id_}", "technique", "techniques/noise",
                          label, desc, layer="geometry", prompt_fragment=pf))

    # ── LAYER: geometry / flow ────────────────────────────────────────────────
    for id_, label, desc, pf in [
        ("velocity_potential", "Velocity potential", "Φ = Σ±log(r); radial rings expand/contract at poles",
         "Use velocity potential Φ = sum of ±log(r) for each source/sink. Level curves are concentric rings that expand from sources and contract into sinks. Animate with phase = Φ - iTime*speed."),
        ("curl_noise",         "Curl noise",         "Curl of 2D scalar field → divergence-free flow",
         "Use curl of a 2D noise field for divergence-free flow: vel = (-∂f/∂y, ∂f/∂x)."),
        ("source_sink",        "Source/sink",        "Inverse-square point sources and sinks",
         "Add inverse-square source/sink pairs to create local attractors and repellers."),
        ("stream_function",    "Stream function",    "Ψ = Σ atan(dy,dx); angular streamline bands",
         "Use stream function Ψ = sum of ±atan(dy,dx) for source/sink flow. Level curves are streamlines (angular bands). Use velocity potential instead for radial rings."),
    ]:
        nodes.append(node(f"techniques/flow/{id_}", "technique", "techniques/flow",
                          label, desc, layer="geometry", prompt_fragment=pf))

    # ── LAYER: geometry / reflection ──────────────────────────────────────────
    for id_, label, desc, pf in [
        ("sphere_sdf",     "Sphere SDF",      "sdSphere for convex mirror boundary",
         "Use a sphere SDF (length(p) - r) to define a convex mirror surface in 2D screen space."),
        ("env_reflection", "Env reflection",  "r = d - 2(d·n)n ray reflection for env lookup",
         "Compute reflected ray direction using r = d - 2*(d·n)*n and sample an environment function."),
        ("paraboloid_warp", "Paraboloid warp","Project sphere normal to (θ,φ) for env map lookup",
         "Map sphere surface normal to (θ,φ) polar coordinates for a paraboloid environment map lookup."),
    ]:
        nodes.append(node(f"techniques/reflection/{id_}", "technique", "techniques/reflection",
                          label, desc, layer="geometry", prompt_fragment=pf))

    # ── LAYER: colorization ───────────────────────────────────────────────────
    # ONE colorization node is selected per shader — it defines the complete
    # strategy for mapping field values/vectors to pixel color.
    colorizations = [
        ("posterized_rainbow",
         "Posterized rainbow",
         "Quantized hue bands with soft transitions. Full saturation, distinct color regions.",
         """Map the scalar field to full-saturation rainbow with posterized (quantized) hue bands:
  float hue_raw = fract(field_value * scale);
  float steps = 7.0;
  float cell = hue_raw * steps;
  float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;
  col = hsv(hue, 1.0, 0.9);
Gives distinct color bands (mostly one hue) with semi-abrupt transitions. No black gaps."""),

        ("field_rainbow",
         "Field rainbow",
         "Smooth continuous rainbow mapped to field value. Every pixel fully saturated.",
         """Map the scalar field to a smooth continuous rainbow:
  float hue = fract(field_value * scale + iTime * drift);
  col = hsv(hue, 1.0, 0.85);
No posterization — smooth gradient everywhere. Use when you want flowing color with no band structure."""),

        ("velocity_hue",
         "Velocity hue",
         "HSV hue mapped to flow direction angle. Reveals vector field structure via color.",
         """Color pixels by the angle of the velocity/gradient vector:
  vec2 vel = /* your gradient or flow field */;
  float hue = atan(vel.y, vel.x) / 6.28318 + 0.5;
  float brightness = 0.3 + 0.7 * tanh(length(vel) * speed_scale);
  col = hsv(hue, 0.85, brightness);
Best with flow fields, domain warps, or any field with a meaningful gradient direction."""),

        ("iq_cosine_palette",
         "IQ cosine palette",
         "a + b*cos(2π(c*t+d)) for perceptually smooth gradients without hue cycling.",
         """Use Inigo Quilez's cosine palette for smooth, perceptually uniform color:
  vec3 iq_palette(float t) {
      vec3 a = vec3(0.5, 0.5, 0.5);
      vec3 b = vec3(0.5, 0.5, 0.5);
      vec3 c = vec3(1.0, 1.0, 1.0);
      vec3 d = vec3(0.00, 0.33, 0.67);
      return a + b * cos(6.28318 * (c * t + d));
  }
  col = iq_palette(field_value + iTime * drift);
Good for depth illusion — smooth gradients without jarring hue jumps."""),

        ("monochromatic_glow",
         "Monochromatic glow",
         "Single hue, brightness and saturation driven by field value. Clean and hypnotic.",
         """Use a single fixed hue with brightness and saturation from the field:
  float hue = 0.7;  // or vary slowly with iTime
  float brightness = pow(field_value, 0.6);
  float sat = 0.7 + 0.3 * field_value;
  col = hsv(hue, sat, brightness);
Most effective for convergent spirals and SDF structures where depth matters more than variety."""),

        ("channel_offset",
         "RGB channel offset",
         "R/G/B channels driven by the same field at offset phases. Creates chromatic shimmer.",
         """Drive each RGB channel from the same field at offset phases:
  col.r = field_func(uv, iTime * 1.00);
  col.g = field_func(uv, iTime * 1.00 + 1.047);
  col.b = field_func(uv, iTime * 1.00 + 2.094);
Creates chromatic aberration shimmer. Combine with any geometry."""),
    ]
    for id_, label, desc, pf in colorizations:
        nodes.append(node(f"techniques/colorization/{id_}", "technique", "techniques/colorization",
                          label, desc, layer="colorization", prompt_fragment=pf))

    # ── LAYER: shaping ────────────────────────────────────────────────────────
    for id_, label, desc, pf in [
        ("abs_fold",       "Abs fold",       "abs(x) folds negative into positive; ripple/wing symmetry",
         "Use abs() on oscillating values to fold negative halves into positive for symmetric ripple patterns."),
        ("sqrt_gamma",     "Sqrt gamma",     "sqrt(v) softens contrast, prevents harsh edge aliasing",
         "Apply sqrt() gamma correction to brightness values for perceptually smooth falloff."),
        ("pow_contrast",   "Pow contrast",   "pow(v,k) — k<1 lifts shadows, k>1 crushes blacks",
         "Use pow(v, k) with k ∈ [0.5, 2.0] to control contrast."),
        ("triangle_wave",  "Triangle wave",  "abs(fract(x)-0.5)*2 for sharp-crest rings",
         "Use abs(fract(x) - 0.5) * 2 for triangle wave rings."),
        ("glow_inversion", "Glow inversion", "exp(-d*k) gives bright-at-zero glow from SDF distance",
         "Use exp(-d * sharpness) to convert an SDF distance into a glow that peaks at the isoline."),
    ]:
        nodes.append(node(f"techniques/shaping/{id_}", "technique", "techniques/shaping",
                          label, desc, layer="shaping", prompt_fragment=pf))

    # ── LAYER: timing ─────────────────────────────────────────────────────────
    for id_, label, desc, pf in [
        ("decoupled_speeds",     "Decoupled speeds",     "Inner/outer or R/G/B on independent time multipliers",
         "Drive different regions or channels on decoupled time multipliers (×1.0, ×1.3, ×1.7) to prevent temporal adaptation."),
        ("fract_time_precision", "Fract time precision", "fract(phase) wrapping prevents float precision loss at long runtimes",
         "Wrap phase values with fract() before large multiplications to maintain float precision in long sessions."),
        ("breathing_scale",      "Breathing scale",      "Slowly oscillating scale/radius adds organic life",
         "Add a slow sine oscillation to a key parameter (radius, scale, arm count) to create gentle breathing motion."),
    ]:
        nodes.append(node(f"techniques/timing/{id_}", "technique", "techniques/timing",
                          label, desc, layer="timing", prompt_fragment=pf))

    # ── Priors ────────────────────────────────────────────────────────────────
    for tier in ("good", "bad", "weak"):
        nodes.append(node(f"priors/{tier}", "prior_bucket", "priors",
                          tier.capitalize() + " priors",
                          f"Technique combinations rated {tier}. Populated by score.py.", layer="meta"))

    # ── Constraints ───────────────────────────────────────────────────────────
    for id_, label, desc in [
        ("max_iterations_64",         "Max 64 iterations",        "Loop bodies must not exceed 64 iterations."),
        ("no_texture_without_check",  "No iChannel without check","iChannel* may be unbound; avoid or guard."),
        ("avoid_negative_zoom",       "Avoid negative zoom",      "zoom = exp(-t*k) with k > 0."),
        ("avoid_variable_loop_count", "Avoid variable loop count","Loop bounds must be compile-time constant."),
        ("avoid_atan_seam",           "Avoid atan() seam",        "atan(y,x) has a branch cut at angle=±π, creating a visible hard edge in spiral/angular shaders. Fix: build angular patterns using sin/cos directly, or apply fract() to the full phase before modulating, or use smoothly-wrapped polar coordinates that don't expose the ±π discontinuity."),
    ]:
        nodes.append(node(f"constraints/{id_}", "constraint", "constraints", label, desc, layer="meta"))

    # ── Quality tree ──────────────────────────────────────────────────────────
    for id_, label, desc, rp in [
        ("depth_illusion",     "Depth illusion",     "Does the shader create convincing depth or infinite recession?",
         "Rate depth_illusion (0–1): does this image create convincing depth, 3D layering, or infinite recession?"),
        ("attentional_capture","Attentional capture","Does the visual pull and hold gaze involuntarily?",
         "Rate attentional_capture (0–1): does this image pull and hold the viewer's gaze involuntarily?"),
        ("motion_clarity",     "Motion clarity",     "Is motion smooth and free of strobing or jitter?",
         "Rate motion_clarity (0–1): is the motion smooth and continuous, free of strobing or noise?"),
        ("loop_seamlessness",  "Loop seamlessness",  "Does animation appear to continue indefinitely?",
         "Rate loop_seamlessness (0–1): does the motion appear to continue indefinitely without a reset point?"),
        ("affect_induction",   "Affect induction",   "PRIMARY: would continuous viewing induce trance?",
         "Rate affect_induction (0–1): PRIMARY SIGNAL. Would viewing this for 5–10 minutes induce trance or altered state?"),
    ]:
        nodes.append({
            "id": f"quality/{id_}",
            "type": "quality",
            "parent": "quality",
            "layer": "meta",
            "label": label,
            "description": desc,
            "resolver_prompt": rp,
            "score": 0.0,
            "confidence": 0,
            "active": True,
            "retired": False,
            "flag_for_review": False,
            "evolvable": True,
            "sample_shader_ids": [],
        })

    return {"version": "2.0", "nodes": nodes}


def main():
    parser = argparse.ArgumentParser(description="Initialize glsl/ontology.json")
    parser.add_argument("--force", action="store_true", help="Overwrite existing ontology")
    args = parser.parse_args()

    if ONTOLOGY_PATH.exists() and not args.force:
        print(f"ontology.json already exists. Use --force to overwrite.")
        data = json.loads(ONTOLOGY_PATH.read_text())
        print(f"Current: v{data.get('version','?')}  {len(data['nodes'])} nodes")
        return

    ontology = build_ontology()
    ONTOLOGY_PATH.write_text(json.dumps(ontology, indent=2))

    by_layer: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for n in ontology["nodes"]:
        by_layer[n["layer"]] = by_layer.get(n["layer"], 0) + 1
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

    print(f"Wrote {ONTOLOGY_PATH}")
    print(f"Total nodes: {len(ontology['nodes'])}")
    print("By layer:")
    for k, v in sorted(by_layer.items()):
        print(f"  {k:16s}: {v}")
    print("By type:")
    for k, v in sorted(by_type.items()):
        print(f"  {k:16s}: {v}")


if __name__ == "__main__":
    main()
