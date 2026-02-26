// galaxy.glsl
// Archetype: log_arms
// Technique nodes: log_shear, arm_count, spiral_offset, sqrt_gamma, iq_cosine_palette
// Hypnotic mechanic: logarithmic spiral arms mimic natural galaxy morphology, exploiting
//   pre-wired depth-from-motion circuits. sqrt_gamma gives smooth brightness falloff.
//   IQ cosine palette keeps colors perceptually uniform to avoid hue saccades.
// Known issues: none; this is the most stable seed.

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
    float theta = atan(uv.y, uv.x);

    // log_shear: logarithmic radial coordinate for spiral arms
    float log_r = log(r + 0.1) * 0.5;

    // arm_count=3, spiral_offset creates winding
    float arms = 3.0;
    float phase = theta / (2.0 * 3.14159) * arms + log_r * 2.0 - iTime * 0.25;  // spiral_offset

    // Arm brightness: cos wave pinched by r falloff
    float arm_bright = cos(phase * 6.28318) * 0.5 + 0.5;
    float falloff = exp(-r * 1.8);  // sqrt_gamma-like smooth falloff

    float v = arm_bright * falloff + falloff * 0.15;  // arms + core glow

    // iq_cosine_palette: map phase to color
    vec3 col = iq_palette(phase * 0.1 + iTime * 0.05) * v;
    col += vec3(1.0, 0.9, 0.7) * falloff * 0.3;  // warm core

    fragColor = vec4(col, 1.0);
}
