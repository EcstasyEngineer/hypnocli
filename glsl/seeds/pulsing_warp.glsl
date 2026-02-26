// pulsing_warp.glsl
// Archetype: linear_rings
// Core motivation: Counter-rotating spiral beat interference layered with triple-domain-warped
//   FBM noise that pulses in intensity. The pulsing noise creates a breathing organic texture
//   over the geometric beat pattern. High saturation from wide phase spread across RGB channels
//   and explicit luma-based saturation boost. Edge glow halos add depth layering.
// atan note: uses atan() safely — sin(N*theta) for integer N=4 in arm phases.
// Graduated from: ff1c204f56a1

uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

float noise(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for(int i = 0; i < 8; i++) {
        v += a * noise(p);
        p = p * 2.0 + vec2(0.1, 0.2);
        a *= 0.5;
    }
    return v;
}

float fbmWarp(vec2 p) {
    float f1 = fbm(p);
    float f2 = fbm(p + vec2(f1 * 0.4));
    return fbm(p + vec2(f2 * 0.4));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    float logR = log(r + 1.5);
    float armCount = 4.0;
    float spiralPhase = logR * 2.5;

    float t1 = iTime * 0.8;
    float t2 = iTime * 1.3;
    float t3 = iTime * 1.7;

    float arm1 = sin(theta * armCount + spiralPhase - t1);
    float arm2 = sin(theta * armCount - spiralPhase + t2);
    float folded = abs(arm1 * arm2);

    float rings = abs(fract(r * 8.0 - t1 * 0.5) - 0.5) * 2.0;
    float rings2 = abs(fract(logR * 6.0 + t2 * 0.3) - 0.5) * 2.0;

    // Pulsing FBM warp
    vec2 warpPos = vec2(r * cos(theta), r * sin(theta));
    float warp = fbmWarp(warpPos + vec2(iTime * 0.3));
    float warpPulse = 0.5 + 0.5 * sin(iTime * 0.7);
    warp *= warpPulse;

    float pattern = folded * 0.5 + rings * 0.3 + rings2 * 0.2;
    pattern = mix(pattern, warp * 0.7, 0.4);

    float edgeGlow = exp(-abs(fract(r * 4.0 - t1 * 0.2) - 0.5) * 8.0) * 0.8;
    float depthFade = 1.0 - smoothstep(0.0, 3.0, r);
    float convergence = sin(theta * 3.0 + logR * 1.5 - t3 * 0.6) * 0.3 + 0.7;

    // Wide phase spread for saturation
    float r_val = abs(sin(theta * armCount + spiralPhase - t1 * 1.0 + 0.0));
    float g_val = abs(sin(theta * armCount + spiralPhase - t1 * 1.3 + 2.5));
    float b_val = abs(sin(theta * armCount + spiralPhase - t1 * 1.7 + 5.0));

    vec3 col = vec3(
        (pattern + edgeGlow) * r_val * convergence * 1.2,
        (pattern * 0.7 + edgeGlow * 0.5) * g_val * convergence * 0.85,
        (pattern * 0.5 + edgeGlow * 0.9) * b_val * convergence * 1.3
    );

    col += vec3(
        warp * 0.35 * sin(t1),
        warp * 0.2 * sin(t2 + 2.0),
        warp * 0.3 * sin(t3 + 4.0)
    );

    col *= depthFade;

    // Saturation boost
    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(luma), col, 1.6);
    col = max(col, 0.0);
    col = mix(col, col * col, 0.15);
    col = pow(col, vec3(0.85));

    fragColor = vec4(col, 1.0);
}
