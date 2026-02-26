// sdf_spiral.glsl
// Archetype: sdf_outline
// Core motivation: Two counter-rotating spiral sets create glowing isoline intersections
//   that pulse rhythmically. Each intersection is a "wave" of brightness — the pulsing
//   catches attention without any net directional drift. The SDF glow at each isoline
//   simulates depth layering.
// atan note: uses atan() safely — fract(theta/(2pi)*arms) for integer arms masks the
//   branch cut. The integer jump at +/-pi disappears under fract().
// Known issues: glow radius depends on screen resolution — use iResolution-normalized distances.

float sdSpiral(vec2 p, float arms, float tightness, float t) {
    float r = length(p);
    float theta = atan(p.y, p.x);
    float log_r = log(r + 0.001);

    // Distance to nearest spiral arm isoline
    float phase = (theta / (2.0 * 3.14159) * arms + log_r * tightness - t);
    float dist = abs(fract(phase + 0.5) - 0.5) / arms;

    return dist * r;  // scale by radius for perspective-like falloff
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    // Counter-rotating spirals: eliminates directional flow,
    // creates pulsing intersection nodes where arms cross
    float d1 = sdSpiral(uv, 4.0, 1.8,  iTime * 0.3);
    float d2 = sdSpiral(uv, 4.0, 1.8, -iTime * 0.3);
    float d = min(d1, d2);

    // glow_inversion: bright at d=0, dark at d=large
    float glow = exp(-d * 30.0);
    float outline = smoothstep(0.015, 0.01, d);

    // pow_contrast: enhance glow falloff
    float v = pow(glow + outline * 0.5, 0.6);

    // Color tied to radius only — no time drift
    float r = length(uv);
    float hue_shift = log(r + 0.1) * 0.5;

    vec3 col = vec3(
        v * (0.6 + 0.4 * sin(hue_shift)),
        v * (0.6 + 0.4 * sin(hue_shift + 2.094)),
        v * (0.6 + 0.4 * sin(hue_shift + 4.189))
    );

    fragColor = vec4(col, 1.0);
}
