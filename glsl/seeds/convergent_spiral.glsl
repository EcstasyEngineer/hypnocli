// convergent_spiral.glsl
// Archetype: convergent
// Core motivation: Create an inescapable pull toward the center. Radial inversion makes
//   the viewer's gaze feel physically drawn inward, while logarithmic spiral arms create
//   self-similar depth that suggests infinite recession. Decoupled speeds between angle
//   and radius prevent the eye from locking onto any single feature.
// atan note: avoids atan entirely — uses Chebyshev T4 on rotated direction vector for
//   seam-free angular pattern (safest approach for any arm count).
// Known issues: at very high arm counts (>8) aliasing near origin. Keep arm_count <= 6.

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    // Radial inversion: sqrt pulls outer ring into center
    float r = length(uv);
    float r_inv = 1.0 / (r + 0.01);  // inversion_sqrt: compressed outer radius

    // Seam-free angular pattern: use sin/cos on the unit direction directly.
    // This avoids the atan() branch cut at ±π entirely.
    float log_r = log(r + 0.001);
    vec2 dir = uv / (r + 1e-6);
    float arms = 4.0;  // arm_count
    float spiral_wind = log_r * 1.5 + iTime * 0.4;  // spiral_offset + log_shear

    // Rotate direction by spiral_wind, then use Chebyshev T₄ for 4 arms
    float cw = cos(spiral_wind), sw = sin(spiral_wind);
    vec2 rot = vec2(dir.x * cw - dir.y * sw, dir.x * sw + dir.y * cw);
    // cos(4θ) = 8cos⁴θ - 8cos²θ + 1  (Chebyshev T₄)
    float c2 = rot.x * rot.x;
    float c4 = 8.0 * c2 * c2 - 8.0 * c2 + 1.0;

    // Angular pattern with decoupled time speeds
    float angle_wave = c4 * 0.5 + 0.5;
    float depth_wave = sin(log_r * 8.0 - iTime * 1.2) * 0.5 + 0.5;  // decoupled_speeds

    // Compose
    float v = mix(angle_wave, depth_wave, 0.4) * (1.0 - smoothstep(0.0, 1.5, r_inv * r));
    float glow = exp(-r * 3.0) * 0.5;  // center glow for convergence pull

    vec3 col = vec3(
        v * 0.3 + glow,
        v * 0.6 * abs(sin(iTime * 0.3)),
        v * 0.9 + glow * 0.5
    );

    fragColor = vec4(col, 1.0);
}
