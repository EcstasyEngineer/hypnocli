// galaxy.glsl
// Archetype: log_arms
// Core motivation: Mimic natural galaxy morphology to exploit pre-wired depth-from-motion
//   circuits. The human visual system parses spiral arm structure as depth cues — three
//   log-spiral arms with warm-core IQ palette create an immediate sense of gazing into
//   deep space. The sqrt falloff gives smooth brightness that pulls gaze toward the core.
// atan note: avoids atan entirely — uses Chebyshev T3 on rotated direction vector for
//   seam-free angular pattern.

vec3 iq_palette(float t) {
    // iq_cosine_palette: a + b * cos(2π(c*t + d))
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 1.0);
    vec3 d = vec3(0.00, 0.33, 0.67);
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);

    // log_shear: logarithmic radial coordinate for spiral arms
    float log_r = log(r + 0.1) * 0.5;

    // Seam-free angular pattern: use sin/cos directly instead of atan().
    // For N arms, compute sin(N * angle + spiral_offset) via trig identity
    // on the unit direction vector, avoiding the ±π branch cut entirely.
    vec2 dir = uv / (r + 1e-6);
    float arms = 3.0;
    float spiral_wind = log_r * 2.0 - iTime * 0.25;
    // Chebyshev expansion: cos(3θ + φ) from cos(θ), sin(θ)
    // Use complex-number multiplication to rotate by spiral_wind first
    float cw = cos(spiral_wind), sw = sin(spiral_wind);
    vec2 rotated = vec2(dir.x * cw - dir.y * sw, dir.x * sw + dir.y * cw);
    // cos(3θ) = 4cos³θ - 3cosθ  (Chebyshev T₃)
    float c3 = 4.0 * rotated.x * rotated.x * rotated.x - 3.0 * rotated.x;

    // Arm brightness: smooth cosine wave pinched by r falloff
    float arm_bright = c3 * 0.5 + 0.5;
    float falloff = exp(-r * 1.8);  // sqrt_gamma-like smooth falloff

    float v = arm_bright * falloff + falloff * 0.15;  // arms + core glow

    // iq_cosine_palette: use smooth phase from log_r for color (also seam-free)
    float color_phase = log_r * 0.3 + iTime * 0.05;
    vec3 col = iq_palette(color_phase) * v;
    col += vec3(1.0, 0.9, 0.7) * falloff * 0.3;  // warm core

    fragColor = vec4(col, 1.0);
}
