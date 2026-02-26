// spiral_glow_rotate.glsl
// Archetype: convergent
// Core motivation: Variant of spiral_glow with whole-field rotation added. The slow rotation
//   (0.15 rad/s) adds a vestibular component — the entire visual field turns, engaging
//   balance/orientation circuits alongside the convergent spiral pull. Same SDF arm glow
//   and IQ cosine palette underneath.
// atan note: same safety as spiral_glow — rotation is applied before atan, doesn't affect it.
// Variant of: spiral_glow.glsl
// Graduated from: e28902e37bb8

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    // Rotate entire field
    float rot_angle = iTime * 0.15;
    float ca = cos(rot_angle), sa = sin(rot_angle);
    uv = vec2(uv.x * ca - uv.y * sa, uv.x * sa + uv.y * ca);

    float r = length(uv);
    float theta = atan(uv.y, uv.x);

    float log_r = log(r + 0.001);

    float arm_count = 5.0;
    float tightness = 2.2;
    float spiral_phase = theta + log_r * tightness;

    float arm_period = 6.28318 / arm_count;
    float phase_mod = mod(spiral_phase, arm_period);
    float arm_distance = min(phase_mod, arm_period - phase_mod);
    float sdf = arm_distance - 0.4;
    float arm_glow = exp(-abs(sdf) * 8.0);

    float r_inv = 1.0 / (r + 0.02);
    float depth_compression = smoothstep(3.0, 0.1, r_inv);

    float angle_drift = sin(spiral_phase - iTime * 1.3) * 0.5 + 0.5;
    float radial_drift = sin(log_r * 6.0 + iTime * 0.8) * 0.5 + 0.5;

    float field_value = mix(angle_drift, radial_drift, 0.6);
    field_value = mix(field_value, arm_glow, 0.4);
    field_value += depth_compression * 0.3;

    float center_pull = exp(-r * 2.5) * 2.0;
    field_value += center_pull * 0.5;
    field_value = fract(field_value + iTime * 0.25);

    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 1.0);
    vec3 d = vec3(0.00, 0.33, 0.67);

    float drift = iTime * 0.15;
    vec3 col = a + b * cos(6.28318 * (c * (field_value + drift) + d));

    float depth_illusion = 1.0 - smoothstep(0.0, 4.0, log_r);
    col *= mix(0.4, 1.0, depth_illusion);

    col += vec3(0.2, 0.15, 0.25) * center_pull * 0.6;

    float vignette = smoothstep(2.5, 0.0, r);
    col *= mix(0.3, 1.0, vignette);

    fragColor = vec4(col, 1.0);
}
