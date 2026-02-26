// sdf_spiral.glsl
// Archetype: sdf_outline
// Technique nodes: sdf_analytic, glow_inversion, log_shear, pow_contrast, fract_time_precision
// Hypnotic mechanic: SDF-based spiral outlines create isoline structure; the glow at each
//   isoline simulates depth layering. fract_time_precision allows sub-frame timing precision
//   for smooth continuous motion without temporal aliasing.
// Known issues: glow radius depends on screen resolution — use iResolution-normalized distances.

float sdSpiral(vec2 p, float arms, float tightness, float t) {
    // sdf_analytic: distance to logarithmic spiral
    float r = length(p);
    float theta = atan(p.y, p.x);
    float log_r = log(r + 0.001);

    // Distance to nearest spiral arm isoline
    float phase = (theta / (2.0 * 3.14159) * arms + log_r * tightness - t);
    float dist = abs(fract(phase + 0.5) - 0.5) / arms;  // fract_time_precision-style wrapping

    return dist * r;  // scale by radius for perspective-like falloff
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    float d = sdSpiral(uv, 4.0, 1.8, iTime * 0.3);

    // glow_inversion: bright at d=0, dark at d=large
    float glow = exp(-d * 30.0);
    float outline = smoothstep(0.015, 0.01, d);  // sharp isoline edge

    // pow_contrast: enhance glow falloff
    float v = pow(glow + outline * 0.5, 0.6);

    // log_shear color: hue shifts with log radius
    float r = length(uv);
    float hue_shift = log(r + 0.1) * 0.3 + iTime * 0.1;

    vec3 col = vec3(
        v * (0.6 + 0.4 * sin(hue_shift)),
        v * (0.6 + 0.4 * sin(hue_shift + 2.094)),
        v * (0.6 + 0.4 * sin(hue_shift + 4.189))
    );

    fragColor = vec4(col, 1.0);
}
