// convergent_spiral.glsl
// Archetype: convergent
// Technique nodes: inversion_sqrt, log_shear, arm_count, spiral_offset, decoupled_speeds
// Hypnotic mechanic: radial inversion pulls motion toward center; viewer gaze converges
//   on vanishing point. Logarithmic arms create self-similar depth illusion. Speed
//   decoupling between angle and radius prevents adaptation lock.
// Known issues: at very high arm counts (>8) aliasing near origin. Keep arm_count <= 6.

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    // Radial inversion: sqrt pulls outer ring into center
    float r = length(uv);
    float r_inv = 1.0 / (r + 0.01);  // inversion_sqrt: compressed outer radius

    // Log-shear: logarithmic spiral arms
    float theta = atan(uv.y, uv.x);
    float log_r = log(r + 0.001);
    float arms = 4.0;  // arm_count
    float spiral_phase = theta / (2.0 * 3.14159) * arms + log_r * 1.5 + iTime * 0.4;  // spiral_offset + log_shear

    // Angular pattern with decoupled time speeds
    float angle_wave = sin(spiral_phase * 6.28318) * 0.5 + 0.5;
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
