// beat_rings.glsl
// Archetype: linear_rings
// Core motivation: Counter-rotating 4-arm spiral sets create a moire beat interference
//   pattern. The abs-folded product generates symmetric ripple structure. Triangle-wave
//   concentric rings provide radial depth. Decoupled RGB channel speeds prevent temporal
//   adaptation — each color channel drifts at its own rate so the eye never settles.
// atan note: uses atan() safely — sin(N*theta) for integer N=4 in both arm phases.
// Graduated from: fdcb31019c25

uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);

    // Log radius for scale invariance
    float logr = log(r + 1.0) * 0.5;

    // Arm count = 4 for rich beat pattern
    float arm_count = 4.0;
    float tightness = 2.5;

    // Spiral offset: adds logarithmic winding
    float spiral_offset = logr * tightness;

    // Inversion_linear: counter-rotating arms with negated phase
    float phase1 = theta * arm_count + spiral_offset + iTime * 1.3;
    float arm1 = sin(phase1);

    float phase2 = -theta * arm_count - spiral_offset + iTime * 0.9;
    float arm2 = sin(phase2);

    // Beat pattern from interference
    float beat = arm1 * arm2;

    // abs_fold: fold into positive symmetric ripple
    float folded = abs(beat);

    // Linear rings with triangle wave
    float rings = abs(fract(r * 8.0 - iTime * 0.25) - 0.5) * 2.0;

    // Combine with smooth crossfade
    float pattern = mix(folded * rings, rings, 0.4);

    // Decoupled channel speeds
    float time_r = iTime * 1.0;
    float time_g = iTime * 1.3;
    float time_b = iTime * 1.7;

    // Smooth continuous color gradients
    float color_r = 0.5 + 0.5 * sin(phase1 + time_r * 0.4 + logr * 1.2);
    float color_g = 0.5 + 0.5 * sin(phase2 + time_g * 0.3 - logr * 0.9);
    float color_b = 0.5 + 0.5 * cos(theta + spiral_offset + time_b * 0.2);

    // Glow halos at structure edges
    float glow = smoothstep(0.1, 0.0, abs(folded - 0.5));

    // Depth illusion: multiplicative falloff with log radius
    float depth = 1.0 / (1.0 + logr * logr * 0.5);

    // Convergent motion: pull toward center
    float convergence = (1.0 - smoothstep(0.0, 2.0, r)) * pattern;

    vec3 col = vec3(
        (color_r * pattern + glow * 0.5) * depth,
        (color_g * pattern + glow * 0.3) * depth * 0.95,
        (color_b * pattern + glow * 0.4) * depth * 1.05
    );

    col += vec3(convergence * 0.2, convergence * 0.15, convergence * 0.25);

    // Smooth contrast boost
    col = mix(col, col * col * 3.0, 0.3);

    fragColor = vec4(col, 1.0);
}
