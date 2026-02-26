// fractal_palette.glsl
// Archetype: fractal_zoom
// Technique nodes: fbm_single, pow_contrast, iq_cosine_palette, fract_time_precision, sqrt_gamma
// Hypnotic mechanic: zoom into fractal boundary exploits scale invariance — viewer
//   cannot determine absolute size. Slow exponential zoom (not linear) maintains constant
//   apparent speed regardless of zoom level. IQ palette keeps gradients from banding.
// Known issues: Mandelbrot zoom center must be on attractor boundary; (−0.7269, 0.1889)
//   is a reliable default.

#define MAX_ITER 128

vec3 iq_palette(float t) {
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 1.0);
    vec3 d = vec3(0.00, 0.10, 0.20);
    return a + b * cos(6.28318 * (c * t + d));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // fract_time_precision: fractional zoom level for smooth continuous zoom
    float zoom = exp(-iTime * 0.25);  // exponential zoom in

    // Center on a deep attractor boundary
    vec2 center = vec2(-0.7269, 0.1889);

    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    vec2 c = center + uv * zoom * 2.5;

    // Mandelbrot iteration (fbm_single pattern: repeated self-similar operation)
    vec2 z = vec2(0.0);
    float i = 0.0;
    for (int n = 0; n < MAX_ITER; n++) {
        if (dot(z, z) > 4.0) break;
        z = vec2(z.x*z.x - z.y*z.y, 2.0*z.x*z.y) + c;
        i++;
    }

    // Smooth iteration count (pow_contrast + sqrt_gamma)
    float smooth_i = i - log2(log2(dot(z, z))) + 4.0;
    float t = sqrt(smooth_i / float(MAX_ITER));  // sqrt_gamma
    t = pow(t, 0.7);  // pow_contrast

    vec3 col;
    if (i >= float(MAX_ITER)) {
        col = vec3(0.0);  // interior: black
    } else {
        col = iq_palette(t + iTime * 0.04);  // iq_cosine_palette with slow time drift
    }

    fragColor = vec4(col, 1.0);
}
