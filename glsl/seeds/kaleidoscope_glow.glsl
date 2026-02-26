// shader_id: 7b2084c033da
// archetype: kaleidoscopic
// techniques: inversion_linear, spiral_offset, arm_count, glow_inversion, decoupled_speeds, fbm_single, fbm_triple_warp
#define PI 3.14159265359
#define SQRT2 1.41421356237

uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

// FBM with 6 octaves
float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 1.0;
    float frequency = 1.0;
    float maxValue = 0.0;
    
    for(int i = 0; i < 6; i++) {
        value += amplitude * sin(p.x * frequency + iTime * 0.1) * cos(p.y * frequency + iTime * 0.07);
        maxValue += amplitude;
        amplitude *= 0.5;
        frequency *= 2.0;
        p *= 2.0;
    }
    return value / maxValue;
}

// Triple domain warp: fbm(p + fbm(p + fbm(p)))
float fbmWarp(vec2 p) {
    vec2 p1 = p + fbm(p) * 0.3;
    vec2 p2 = p1 + fbm(p1) * 0.3;
    return fbm(p2 + fbm(p2 + vec2(iTime * 0.05)) * 0.2);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // arm_count = 5 for pentagonal kaleidoscope
    float N = 5.0;
    float sector = 2.0 * PI / N;
    
    // abs_fold: mirror symmetry into sector
    float t_folded = mod(theta, sector);
    if (t_folded > sector * 0.5) {
        t_folded = sector - t_folded;
    }
    
    // inversion_linear: counter-rotating phase via negated offset
    float inverted_phase = -t_folded;
    
    // spiral_offset: logarithmic spiral via log(r)
    float tightness = 2.5;
    float spiral_phase = log(max(r, 0.01)) * tightness;
    
    // decoupled_speeds for inner and outer regions
    float inner_time = iTime * 0.25;
    float mid_time = iTime * 0.38;
    float outer_time = iTime * 0.61;
    
    float depth_blend = smoothstep(0.1, 0.9, r);
    float speed_mod = mix(inner_time, outer_time, depth_blend);
    
    // Combined phase for spiral arms
    float phase = t_folded * N * 1.8 + spiral_phase + speed_mod + inverted_phase * 0.5;
    float phase2 = t_folded * N * 2.3 + spiral_phase * 0.7 + mid_time + inverted_phase * 0.3;
    
    // fbm_single: base noise layer
    float noise1 = fbm(uv * 2.0 + vec2(iTime * 0.1, iTime * 0.07));
    
    // fbm_triple_warp: organic warped flow
    float noise2 = fbmWarp(uv * 3.0);
    
    // Spiral arm pattern
    float spiral = sin(phase) * 0.5 + 0.5;
    spiral *= cos(phase2 * 0.5) * 0.5 + 0.5;
    
    // Radial rings with counter-rotation
    float ringPattern = abs(fract(r * 8.0 - iTime * 0.2) - 0.5) * 2.0;
    ringPattern = pow(ringPattern, 0.8);
    
    // Angular grating in folded space
    float angularGrate = abs(sin(t_folded * 12.0 + spiral_phase * 0.5 + mid_time)) * 0.7;
    
    // Distance field for glow_inversion effect
    float dist = abs(sin(phase) * r);
    float sharpness = 4.0;
    float glow = exp(-dist * sharpness) * 0.8;
    
    // Combine patterns with FBM modulation
    float pattern1 = spiral * ringPattern * (noise1 * 0.5 + 0.5);
    float pattern2 = angularGrate * (noise2 * 0.3 + 0.7);
    float combined = mix(pattern1, pattern2, 0.5) + glow;
    
    // Smooth gamma compression for depth illusion
    combined = sqrt(combined);
    combined = pow(combined, 0.85);
    
    // decoupled_speeds for color channels
    float colR = 0.5 + 0.5 * sin(speed_mod * 1.0 + phase);
    float colG = 0.5 + 0.5 * sin(speed_mod * 1.3 + phase + 2.094);
    float colB = 0.5 + 0.5 * sin(speed_mod * 1.7 + phase + 4.189);
    
    // Color gradient with radial falloff
    vec3 col = vec3(colR, colG, colB) * combined;
    
    // Add subtle iridescence from noise modulation
    col += vec3(
        noise1 * 0.15,
        noise2 * 0.12,
        mix(noise1, noise2, 0.5) * 0.1
    );
    
    // Depth vignette: pull attention inward
    float vignette = 1.0 - smoothstep(0.3, 1.2, r) * 0.4;
    col *= vignette;
    
    // Ensure smooth color transitions
    col = mix(col, vec3(0.1), smoothstep(1.0, 1.5, r));
    
    fragColor = vec4(col, 1.0);
}