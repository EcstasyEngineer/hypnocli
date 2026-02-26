// rainbow_vortex.glsl
// Archetype: convergent
// Core motivation: Posterized HSV rainbow creates bold color bands that shift through hue
//   space. Five spiral arms with smoothstep-softened posterization boundaries avoid hard
//   banding. Multiple wave layers (angular oscillation, radial waves, arm glow) create
//   complex non-repeating field. Center convergence pulls attention inward.
// atan note: uses atan() safely — sin(spiral_phase * arms) where arms=5 (integer) means
//   the 2pi jump maps to exactly 5 full sin periods. sin(theta * arms) likewise safe.
// Graduated from: 9270064e0ff5

uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

vec3 hsv(float h, float s, float v) {
    h = fract(h);
    float c = v * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    vec3 rgb;
    if (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
    else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
    else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
    else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
    else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);
    return rgb + m;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    float r = length(uv);
    float theta = atan(uv.y, uv.x);

    float r_safe = max(r, 0.02);
    float log_r = log(r_safe);

    float arms = 5.0;
    float tightness = 2.2;

    float t1 = iTime * 0.4;
    float t2 = iTime * 0.52;
    float t3 = iTime * 0.68;

    float spiral_phase = theta + log_r * tightness + t1;

    float angle_oscillation = sin(spiral_phase * arms) * 0.5 + 0.5;

    float radial_wave1 = sin(log_r * 6.0 - t2 * 1.3) * 0.5 + 0.5;

    float arm_pattern = sin(theta * arms + log_r * 3.5 + t1 * 0.8);
    float arm_contrib = smoothstep(-0.3, 0.7, arm_pattern) * 0.5 + 0.5;

    float field_value = angle_oscillation * 0.4 + radial_wave1 * 0.25 + arm_contrib * 0.35;

    float convergence = exp(-r * 2.5) * 0.8;
    field_value = field_value * (1.0 - convergence * 0.4) + convergence * 0.5;

    float spiral_arm_dist = abs(sin(theta * arms + log_r * tightness));
    float arm_glow = exp(-spiral_arm_dist * 8.0) * 0.6;
    field_value = mix(field_value, field_value + arm_glow * 0.3, 0.7);

    // Posterized hue with smoothstep transitions
    float hue_raw = fract(field_value * 3.5);
    float steps = 7.0;
    float cell = hue_raw * steps;
    float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;

    vec3 col = hsv(hue, 1.0, 0.9);

    col *= sqrt(field_value);

    float center_glow = exp(-r * 3.2) * 0.5;
    col += center_glow * vec3(0.3, 0.2, 0.5);

    float vignette = smoothstep(2.5, 0.5, r);
    col *= mix(vec3(0.4), vec3(1.0), vignette);

    col = mix(col, col * col, 0.15);

    fragColor = vec4(col, 1.0);
}
