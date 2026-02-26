# atan(y,x) Branch Cut Guidance for GLSL Generators

## The Problem

`atan(y,x)` returns values in [-pi, +pi]. At the negative x-axis (angle = pi),
the return value jumps discontinuously from +pi to -pi. This is the "branch cut."

If any downstream math exposes this jump as a visible value change, you get a
hard seam in the rendered image — typically a line running from center to the
left edge (or elsewhere if coordinates are rotated/reflected).

## The Actual Rule

**atan() is NOT inherently dangerous.** The branch cut is only visible when
the downstream function is NOT periodic with a period that divides 2*pi.

### SAFE uses of atan() — no visible seam:

1. **sin(N * atan(y,x))** or **cos(N * atan(y,x))** for integer N
   - sin(N*pi) == sin(N*(-pi)) for any integer N, so the jump is invisible.
   - Example: `double_arm.glsl` uses `sin(theta * 2.0 + ...)` — works perfectly.

2. **mod(atan(y,x), 2*pi/N)** for N-fold symmetry folding
   - Explicitly wraps the angle into a sector. The branch cut lands on a sector
     boundary and gets folded away.
   - Example: `kaleidoscope.glsl` uses `mod(theta, sector)` + fold.

3. **fract(atan(y,x) / (2*pi) * N + offset)** for integer N
   - fract() takes the fractional part. At the branch cut, atan jumps by 2*pi,
     so `atan/(2*pi)*N` jumps by N (an integer). fract(integer) = 0 — invisible.
   - Example: `sdf_spiral.glsl` uses `fract(theta/(2*pi)*4 + log_r*tightness - t)`.

### UNSAFE uses — visible seam:

1. **theta / (2*pi) as a UV coordinate** (without integer-multiple fract wrapping)
   - Linear mapping directly exposes the jump as a hard line.
   - Example: `bean_reflection.glsl` (DELETED) used `u = theta/(2*pi) + 0.5`
     in the environment function — created a visible seam through the sphere.

2. **Any non-periodic function of atan** near the branch cut
   - Gradients, interpolations, or color ramps that don't wrap with period 2*pi.

3. **atan on reflected/refracted directions**
   - The reflection can map the branch cut to unexpected screen locations
     (e.g., the seam appears on the RIGHT instead of the LEFT).

## Safest Approach: Avoid atan entirely

For angular patterns, the Chebyshev polynomial approach from `convergent_spiral.glsl`
and `galaxy.glsl` is always safe — it computes cos(N*theta) directly from the unit
direction vector using trig identities, never computing an angle at all:

```glsl
vec2 dir = uv / (length(uv) + 1e-6);
// Rotate by spiral wind
float cw = cos(wind), sw = sin(wind);
vec2 rot = vec2(dir.x*cw - dir.y*sw, dir.x*sw + dir.y*cw);
// cos(4*theta) via Chebyshev T4: 8*cos^4 - 8*cos^2 + 1
float c2 = rot.x * rot.x;
float c4 = 8.0 * c2 * c2 - 8.0 * c2 + 1.0;
```

Common Chebyshev polynomials:
- T2(x) = 2x^2 - 1                    (2 arms)
- T3(x) = 4x^3 - 3x                   (3 arms)
- T4(x) = 8x^4 - 8x^2 + 1            (4 arms)
- T6(x) = 32x^6 - 48x^4 + 18x^2 - 1  (6 arms)

## Guidance for the Generator Model

When writing a new shader:
1. If you need N evenly-spaced arms: prefer Chebyshev T_N (always safe).
2. If you need angle folding for symmetry: `mod(atan(y,x), sector)` is safe.
3. If you use atan in an SDF: ensure fract() wraps with integer arm count.
4. NEVER use `atan(y,x) / (2*pi)` as a raw coordinate — always wrap with fract()*N for integer N.
5. If you're unsure: use the Chebyshev approach. It's a few more lines but never fails.
