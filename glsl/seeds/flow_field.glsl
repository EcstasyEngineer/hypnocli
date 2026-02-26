// flow_field.glsl
// Archetype: flow_field
// Technique nodes: perlin_gradient, source_sink, streamline_color
// Hypnotic mechanic: velocity potential Φ = Σ ±log(r) for 3 sources + 3 sinks.
//   Level curves of Φ are concentric rings that physically expand from sources
//   and contract into sinks. Posterized rainbow hue gives distinct color bands
//   with soft transitions. Poles slowly drift — never fully periodic.
// Known issues: singularities near poles cycle very fast (feature, not bug).

#define TAU 6.28318530

vec3 hsv(float h, float s, float v) {
    vec3 c = clamp(abs(mod(h*6.0+vec3(0,4,2),6.0)-3.0)-1.0, 0.0, 1.0);
    return v * mix(vec3(1.0), c, s);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5*iResolution.xy) / min(iResolution.x, iResolution.y);

    float t = iTime * 0.10;

    // 3 sources — slowly drift
    vec2 src[3];
    src[0] = vec2( 0.50 + 0.04*sin(t*0.7),   0.12 + 0.05*cos(t*0.9));
    src[1] = vec2(-0.38 + 0.05*cos(t*0.8),   0.42 + 0.04*sin(t*0.6));
    src[2] = vec2( 0.04 + 0.04*sin(t*1.1),  -0.48 + 0.04*cos(t*0.75));

    // 3 sinks
    vec2 snk[3];
    snk[0] = vec2(-0.48 + 0.04*cos(t*0.65), -0.18 + 0.05*sin(t*0.85));
    snk[1] = vec2( 0.28 + 0.05*sin(t*0.95), -0.33 + 0.04*cos(t*0.7));
    snk[2] = vec2(-0.08 + 0.04*cos(t*0.8),   0.50 + 0.04*sin(t*1.0));

    // Velocity potential: Φ = Σ log(r_source) - Σ log(r_sink)
    // Near a source: Φ → -∞, rings expand outward as time increases
    // Near a sink:   Φ → +∞, rings contract inward as time increases
    float phi = 0.0;
    for (int i = 0; i < 3; i++) {
        phi += log(max(length(uv - src[i]), 0.001));
        phi -= log(max(length(uv - snk[i]), 0.001));
    }

    // Animate: slower drift
    float phase = phi - iTime * 0.35;

    // Posterized rainbow: flat bands with quick soft transitions at edges
    float hue_raw = fract(phase * 0.25);
    float steps = 7.0;
    float cell = hue_raw * steps;
    float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;

    vec3 col = hsv(hue, 1.0, 0.9);

    fragColor = vec4(col, 1.0);
}
