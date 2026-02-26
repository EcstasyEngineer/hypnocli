// kaleidoscope.glsl
// Archetype: kaleidoscopic
// Core motivation: N-fold mirror symmetry eliminates asymmetric distractors. The viewer
//   can't track any single element — attention diffuses to the global gestalt. Slow rotation
//   at decoupled speeds (inner vs outer) creates vortex pull. The interplay between angular
//   sectors and radial rings produces visual tension that prevents adaptation.
// atan note: uses atan() safely — mod(theta, sector) + fold masks the +/-pi branch cut.
// Known issues: folds < 4 look too simple; folds > 12 may stall GPU on old hardware.

#define PI 3.14159265

vec3 iq_palette(float t) {
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 0.5);
    vec3 d = vec3(0.00, 0.33, 0.67);
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);

    // arm_count: N-fold symmetry via abs_fold on theta
    float N = 6.0;
    float sector = 2.0 * PI / N;
    // abs_fold: fold into [0, sector/2]
    float t_folded = mod(theta, sector);
    if (t_folded > sector * 0.5) t_folded = sector - t_folded;

    // Reconstruct UV in folded sector
    vec2 uv_fold = r * vec2(cos(t_folded), sin(t_folded));

    // Inner domain: slow rotate; outer: faster rotate (decoupled_speeds)
    float inner_speed = 0.2;
    float outer_speed = 0.5;
    float rot_angle = mix(inner_speed, outer_speed, smoothstep(0.2, 0.8, r)) * iTime;

    // spiral_offset in folded domain
    float spiral = sin(t_folded * N * 2.0 + log(r + 0.1) * 3.0 + rot_angle) * 0.5 + 0.5;

    // Radial rings
    float rings = abs(fract(r * 5.0 - iTime * 0.15) - 0.5) * 2.0;

    float v = mix(spiral, rings, 0.4);

    // sqrt_gamma: soften the contrast
    v = sqrt(max(v, 0.0));

    // Rich IQ palette — phase varies with angle and radius for multi-hue spread
    float hue_phase = t_folded * 2.0 + r * 0.8 + rot_angle * 0.3;
    vec3 col = iq_palette(hue_phase) * (v * 0.7 + 0.3);

    // Center glow for convergence pull
    col += vec3(0.15, 0.1, 0.25) * exp(-r * 3.0);

    fragColor = vec4(col, 1.0);
}
