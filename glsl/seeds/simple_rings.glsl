// shader_id: 895e3a4075ed
// archetype: linear_rings
// techniques: log_shear, arm_count, abs_fold, decoupled_speeds, fbm_triple_warp
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

float hash(float n) {
    return fract(sin(n) * 43758.5453);
}

float noise(float x) {
    float i = floor(x);
    float f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(hash(i), hash(i + 1.0), f);
}

float fbm(vec2 p) {
    float v = 0.0;
    float amp = 1.0;
    float freq = 1.0;
    for(int i = 0; i < 5; i++) {
        v += amp * noise(p.x * freq + p.y * freq * 0.5);
        amp *= 0.5;
        freq *= 2.0;
    }
    return v;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // log_shear: use log(r+small) for logarithmic self-similarity
    float logr = log(r + 0.1);
    
    // arm_count = 5 for multi-armed spiral
    int arm_count = 5;
    float arm_phase = theta * float(arm_count);
    
    // decoupled_speeds for R, G, B channels
    float t_r = iTime * 1.0;
    float t_g = iTime * 1.3;
    float t_b = iTime * 1.7;
    
    // Counter-rotating arms with log spiral
    float spiral1 = sin(arm_phase + logr * 3.0 - t_r * 2.0);
    float spiral2 = sin(arm_phase - logr * 2.5 + t_g * 1.8);
    
    // Interference/beat pattern
    float beat = spiral1 * spiral2;
    
    // abs_fold: fold negative values creating symmetric ripples
    float folded = abs(beat);
    
    // Triangle wave rings with log coordinate
    float rings = abs(fract(logr * 4.0 + r * 2.0 - t_r * 0.5) - 0.5) * 2.0;
    
    // fbm_triple_warp: triple domain warp
    vec2 p = vec2(theta, logr);
    vec2 q = p + vec2(fbm(p), fbm(p + 1.0));
    vec2 r_warp = p + 4.0 * vec2(fbm(q), fbm(q + 2.0));
    float organic = fbm(r_warp);
    
    // Convergent motion toward center
    float convergence = 1.0 / (0.1 + r * 0.5);
    
    // Combine patterns
    float pattern = mix(folded, rings, 0.4) + organic * 0.2;
    pattern = abs(sin(pattern + iTime * 0.3));
    
    // Glow halo effect at edges
    float glow = exp(-r * 1.5) * 0.5;
    
    // Decoupled color channels with slight asymmetry
    float r_chan = abs(sin(arm_phase + logr * 3.0 - t_r * 2.0 + 0.5));
    float g_chan = abs(sin(arm_phase - logr * 2.5 + t_g * 1.8 + 1.2));
    float b_chan = abs(sin(arm_phase + logr * 2.0 - t_b * 1.5 + 2.1));
    
    // Smooth color gradient with convergence
    vec3 col = vec3(
        (pattern * 0.7 + folded * 0.3) * r_chan * (0.5 + convergence * 0.3) + glow,
        (pattern * 0.6 + rings * 0.4) * g_chan * (0.4 + convergence * 0.2) + glow * 0.7,
        (pattern * 0.8 + organic * 0.2) * b_chan * (0.6 + convergence * 0.25) + glow * 0.9
    );
    
    // Depth illusion via exponential zoom
    float zoom = exp(-iTime * 0.15) * 0.3 + 0.7;
    col *= zoom;
    
    // Prevent hard edges, add smooth falloff
    col *= smoothstep(1.2, 0.3, r);
    
    fragColor = vec4(col, 1.0);
}