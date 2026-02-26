// fbm_warp.glsl
// Archetype: domain_warped
// Technique nodes: fbm_triple_warp, fbm_polar, domain_repetition, iq_cosine_palette
// Hypnotic mechanic: domain-warped fBm (Quilez triple-warp) produces organic, non-repeating
//   flow. No hard edges; attention drifts without anchoring. Polar fBm version prevents
//   the box-like grid artifacts of standard fBm.
// Known issues: expensive on mobile. Cap octaves at 6 for 60fps in browser.

#define PI 3.14159265

// Hash for pseudo-random gradient
vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

// Gradient noise
float gnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);  // smoothstep

    return mix(mix(dot(hash2(i + vec2(0,0)), f - vec2(0,0)),
                   dot(hash2(i + vec2(1,0)), f - vec2(1,0)), u.x),
               mix(dot(hash2(i + vec2(0,1)), f - vec2(0,1)),
                   dot(hash2(i + vec2(1,1)), f - vec2(1,1)), u.x), u.y);
}

// fbm: 6-octave fractional Brownian motion
float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    mat2 rot = mat2(1.6, 1.2, -1.2, 1.6);  // domain_repetition: rotated lattice
    for (int i = 0; i < 6; i++) {
        v += a * gnoise(p);
        p = rot * p;
        a *= 0.5;
    }
    return v;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    // fbm_triple_warp (Quilez): warp q by fbm, then warp r by fbm(q)
    vec2 q = vec2(
        fbm(uv + vec2(0.0, 0.0) + iTime * 0.1),
        fbm(uv + vec2(5.2, 1.3) + iTime * 0.1)
    );
    vec2 r = vec2(
        fbm(uv + 4.0 * q + vec2(1.7, 9.2) + iTime * 0.07),
        fbm(uv + 4.0 * q + vec2(8.3, 2.8) + iTime * 0.07)
    );

    float f = fbm(uv + 4.0 * r + iTime * 0.05);  // fbm_polar: third warp pass

    f = f * 0.5 + 0.5;  // remap to [0,1]

    // iq_cosine_palette
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 0.7, 0.4);
    vec3 d = vec3(0.00, 0.15, 0.20);
    vec3 col = a + b * cos(6.28318 * (c * f + d + iTime * 0.03));

    fragColor = vec4(col, 1.0);
}
