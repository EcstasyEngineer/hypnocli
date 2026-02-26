// neon_spirals.glsl
// Archetype: sdf_outline
// Core motivation: Three overlapping SDF spiral sets at different arm counts (3/4/5) and
//   tightness values create dense glowing intersections. Additive neon color blending
//   produces vivid saturated hues where spirals overlap. Inward-pulling ripple rings
//   and center fade prevent origin blowout while maintaining maximum vibrancy.
// atan note: uses atan() safely — fract(theta/(2pi)*arms) for integer arms in sdSpiral.
//   Hue channels are purely radial (logr-based), no angular color discontinuity.
// Graduated from: 2a039498ee3e

uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

float sdSpiral(vec2 p, float arms, float tightness, float t) {
    float r = length(p);
    if(r < 0.001) r = 0.001;
    float theta = atan(p.y, p.x);
    float logr = log(r);

    float phase = (theta / 6.28318 * arms + logr * tightness - t);
    float dist = abs(fract(phase + 0.5) - 0.5) * 6.28318 / arms;

    return dist * r;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    float t1 = iTime * 0.3;
    float t2 = iTime * 0.39;
    float t3 = iTime * 0.51;

    float r = length(uv);
    float logr = log(r + 0.1);
    float theta = atan(uv.y, uv.x);

    float d1 = sdSpiral(uv, 4.0, 1.8, t1);
    float d2 = sdSpiral(uv, 3.0, 1.5, t2);
    float d3 = sdSpiral(uv, 5.0, 2.1, t3);

    float combined = min(min(d1, d2), d3 * 1.2);

    float glow1 = exp(-d1 * 25.0);
    float glow2 = exp(-d2 * 30.0);
    float glow3 = exp(-d3 * 20.0);

    float outline1 = smoothstep(0.025, 0.008, d1);
    float outline2 = smoothstep(0.02, 0.006, d2);
    float outline3 = smoothstep(0.03, 0.01, d3);

    // sdSpiral returns dist*r, which trivially -> 0 at origin; fade out the artifact
    float center_fade = smoothstep(0.0, 0.1, r);
    glow1 *= center_fade;
    glow2 *= center_fade;
    glow3 *= center_fade;
    outline1 *= center_fade;
    outline2 *= center_fade;
    outline3 *= center_fade;

    float ripple = abs(sin(logr * 3.0 + t1 * 2.0));
    ripple = abs(ripple - 0.5) * 2.0;
    ripple *= exp(-length(uv) * 0.5);

    float hue1 = logr * 0.4 + t1 * 0.2;
    float hue2 = logr * 0.35 + t2 * 0.15;
    float hue3 = logr * 0.45 + t3 * 0.1;

    vec3 col1 = vec3(
        0.5 + 0.5 * sin(hue1),
        0.5 + 0.5 * sin(hue1 + 2.094),
        0.5 + 0.5 * sin(hue1 + 4.189)
    );

    vec3 col2 = vec3(
        0.6 + 0.4 * sin(hue2 + 1.047),
        0.6 + 0.4 * sin(hue2 + 3.142),
        0.6 + 0.4 * sin(hue2 + 5.236)
    );

    vec3 col3 = vec3(
        0.55 + 0.45 * sin(hue3 + 3.0),
        0.55 + 0.45 * sin(hue3 + 1.5),
        0.55 + 0.45 * sin(hue3 + 0.5)
    );

    float v1 = pow(glow1 + outline1 * 0.6, 0.65);
    float v2 = pow(glow2 + outline2 * 0.5, 0.7);
    float v3 = pow(glow3 + outline3 * 0.4, 0.6);

    vec3 final = col1 * v1 * 0.7 + col2 * v2 * 0.6 + col3 * v3 * 0.5;
    final += vec3(ripple * 0.3);

    float depth = exp(-length(uv) * 1.5);
    final *= (0.7 + 0.3 * depth);

    // Saturation push
    float luma = dot(final, vec3(0.299, 0.587, 0.114));
    final = mix(vec3(luma), final, 1.25);
    final = max(final, 0.0);

    final = pow(final, vec3(0.95));

    fragColor = vec4(final, 1.0);
}
