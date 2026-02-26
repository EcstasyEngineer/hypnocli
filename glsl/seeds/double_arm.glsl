// double_arm.glsl
// Archetype: linear_rings
// Core motivation: Create a beating interference pattern that bypasses voluntary attention.
//   Two counter-rotating arm sets produce a moire that oscillates at the difference
//   frequency — the viewer can't track either arm independently, forcing the visual system
//   into a global "defocused" state. Color channels on offset clocks add chromatic drift.
// atan note: uses atan() safely — sin(2*theta + ...) masks the branch cut (integer N in sin).
// Known issues: arm_count > 2 makes the beat too fast to be hypnotic.

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);

    // Two counter-rotating arms
    float arm1 = sin(theta * 2.0 + r * 10.0 - iTime * 1.5);
    float arm2 = sin(theta * 2.0 - r * 10.0 + iTime * 1.1);  // inversion_linear via sign flip
    float beat = arm1 * arm2;  // interference

    // abs_fold: fold negative values into positive — creates ripple from 0
    float folded = abs(beat);

    // triangle_wave via abs(fract - 0.5) for rings
    float rings = abs(fract(r * 6.0 - iTime * 0.3) - 0.5) * 2.0;  // triangle_wave

    float v = mix(folded, rings, 0.3);

    // channel_time_offset: R, G, B on different clocks
    float r_val = abs(sin(theta * 2.0 + r * 10.0 - iTime * 1.5 + 0.0));
    float g_val = abs(sin(theta * 2.0 + r * 10.0 - iTime * 1.5 + 1.0));
    float b_val = abs(sin(theta * 2.0 + r * 10.0 - iTime * 1.5 + 2.0));

    vec3 col = vec3(
        v * r_val,
        v * g_val * 0.8,
        v * b_val * 1.2
    );

    fragColor = vec4(col, 1.0);
}
