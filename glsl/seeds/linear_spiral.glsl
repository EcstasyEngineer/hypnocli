// shader_id: c50b3bb6f8a1
// archetype: linear_rings
// techniques: inversion_linear, log_shear, spiral_offset, arm_count, abs_fold, decoupled_speeds, fbm_triple_warp
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

// Inigo Quilez's hash
float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

// Perlin-like noise
float noise(float x) {
    float i = floor(x);
    float f = fract(x);
    float u = f * f * (3.0 - 2.0 * f);
    return mix(hash(i), hash(i + 1.0), u);
}

// FBM with triple warp
float fbm_warped(vec2 p, float time_offset) {
    float value = 0.0;
    float amplitude = 1.0;
    float frequency = 1.0;
    
    for (int i = 0; i < 6; i++) {
        value += amplitude * noise(p.x * frequency + time_offset + float(i) * 0.1);
        amplitude *= 0.5;
        frequency *= 2.0;
    }
    
    return value;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // [log_shear]: Use log(r) for logarithmic spiral self-similarity
    float log_r = log(r + 1.0);
    
    // [arm_count]: Set to 4 for counter-rotating spiral arms
    float arm_count = 4.0;
    
    // [spiral_offset]: Add log_r * tightness to angular phase for logarithmic spiral
    float tightness = 3.5;
    float spiral_phase = theta * arm_count + log_r * tightness;
    
    // [inversion_linear]: Counter-rotating arms via negated phase offset
    float time_factor = iTime * 0.8;
    
    // Primary spiral arm
    float arm1 = sin(spiral_phase - time_factor);
    
    // Counter-rotating arm (inverted phase)
    float arm2 = sin(-spiral_phase + time_factor * 0.6);
    
    // Additional spiral at different rotation
    float arm3 = sin(spiral_phase * 0.7 + time_factor * 1.3);
    
    // [decoupled_speeds]: Different time multipliers for depth
    float radial_modulation = sin(r * 8.0 - time_factor * 1.7) * cos(theta + time_factor * 0.9);
    
    // Combine arms with beat interference
    float beat = arm1 * arm2 + arm3 * 0.5;
    
    // [abs_fold]: Fold negative halves into positive for symmetric ripples
    float folded_beat = abs(beat);
    
    // Ring pattern with triangle wave
    float ring_freq = 6.0 + sin(time_factor * 0.4) * 2.0;
    float rings = abs(fract(r * ring_freq - time_factor * 0.5) - 0.5) * 2.0;
    
    // Exponential zoom-in effect (avoid negative zoom)
    float zoom = exp(-time_factor * 0.15 + 2.0);
    float zoom_effect = sin(log_r * 5.0 * zoom - time_factor);
    
    // [fbm_triple_warp]: Organic non-repeating warping
    vec2 warp_coord = vec2(theta, log_r);
    float warp1 = fbm_warped(warp_coord * 2.0, time_factor * 0.7);
    float warp2 = fbm_warped(warp_coord + warp1 * 0.5, time_factor * 1.1);
    float warp3 = fbm_warped(warp_coord + warp2 * 0.3, time_factor * 0.5);
    
    // Composite warp pattern
    float organic_flow = warp1 * 0.4 + warp2 * 0.35 + warp3 * 0.25;
    
    // Combine all patterns
    float pattern = mix(folded_beat, rings, 0.4);
    pattern = mix(pattern, zoom_effect, 0.25);
    pattern += organic_flow * 0.3;
    
    // [decoupled_speeds]: Color channels on different time multipliers
    float time_r = iTime * 1.0;
    float time_g = iTime * 1.3;
    float time_b = iTime * 1.7;
    
    // Channel-specific oscillations
    float r_oscillation = abs(sin(spiral_phase + time_r * 2.1 + radial_modulation));
    float g_oscillation = abs(sin(spiral_phase * 1.2 + time_g * 1.8 + organic_flow));
    float b_oscillation = abs(sin(spiral_phase * 0.8 + time_b * 2.4 - radial_modulation));
    
    // Depth color coding based on log_r
    vec3 depth_color = mix(
        vec3(0.2, 0.1, 0.4),
        vec3(0.9, 0.3, 0.6),
        smoothstep(0.0, 3.0, log_r)
    );
    
    // Final color composition
    vec3 col = vec3(
        pattern * r_oscillation * depth_color.r,
        pattern * g_oscillation * depth_color.g,
        pattern * b_oscillation * depth_color.b
    );
    
    // Glow effect at structure edges
    float edge_glow = smoothstep(0.05, 0.0, abs(folded_beat - 0.5)) * 0.6;
    float ring_glow = smoothstep(0.1, 0.0, abs(rings - 1.0)) * 0.4;
    
    col += vec3(edge_glow * 0.8, edge_glow * 0.5, edge_glow) * 0.7;
    col += vec3(ring_glow * 0.3, ring_glow * 0.6, ring_glow * 0.9) * 0.5;
    
    // Smooth fade to prevent harsh boundaries
    float fade = smoothstep(2.5, 0.0, r);
    col *= fade;
    
    // Vignette for convergent attention
    float vignette = 1.0 - smoothstep(0.0, 2.0, r) * 0.3;
    col *= vignette;
    
    fragColor = vec4(col, 1.0);
}