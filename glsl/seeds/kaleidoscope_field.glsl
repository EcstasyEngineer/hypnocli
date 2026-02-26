// shader_id: e05c7373ee55
// archetype: kaleidoscopic
// colorization: field_rainbow
// techniques: spiral_offset, sdf_analytic
#define PI 3.14159265359
#define TAU 6.28318530718

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // Kaleidoscope N-fold symmetry
    float N = 8.0;
    float sector = TAU / N;
    
    // Fold theta into fundamental domain
    float t_folded = mod(theta, sector);
    if (t_folded > sector * 0.5) {
        t_folded = sector - t_folded;
    }
    
    // Decoupled speed multipliers for different radial zones
    float time_inner = iTime * 0.8;
    float time_mid = iTime * 1.3;
    float time_outer = iTime * 1.7;
    
    float blend_mid = smoothstep(0.1, 0.4, r);
    float blend_outer = smoothstep(0.4, 1.2, r);
    
    float anim_time = mix(time_inner, time_mid, blend_mid);
    anim_time = mix(anim_time, time_outer, blend_outer);
    
    // Spiral offset using logarithmic spiral
    float log_r = log(r + 0.5);
    float spiral_tight = 3.5;
    float spiral_phase = t_folded * N * 1.5 + log_r * spiral_tight + anim_time * 0.5;
    
    // Analytic SDF-like spiral field
    float spiral_field = sin(spiral_phase) * 0.5 + 0.5;
    spiral_field = pow(spiral_field, 0.8);
    
    // Radial wave structure with triangle wave
    float radial_wave = abs(fract(r * 8.0 + anim_time * 0.2) - 0.5) * 2.0;
    radial_wave = sqrt(radial_wave);
    
    // Angular resonance in folded sector
    float angular_freq = 4.0;
    float angular_wave = sin(t_folded * angular_freq * PI + anim_time * 0.3) * 0.5 + 0.5;
    
    // Converging field: pull toward center with logarithmic depth
    float depth_pull = exp(-r * 1.5) * (1.0 - r * 0.5);
    depth_pull = max(0.0, depth_pull);
    
    // Combine fields
    float field = spiral_field * 0.4 + radial_wave * 0.3 + angular_wave * 0.2;
    field = field + depth_pull * 0.1;
    
    // Apply sqrt gamma for smooth falloff
    field = sqrt(field);
    
    // Field_rainbow colorization - EXACTLY as specified
    float field_scale = 3.5;
    float drift = 0.15;
    float hue = fract(field * field_scale + iTime * drift);
    
    vec3 col = hsv2rgb(vec3(hue, 1.0, 0.85));
    
    // Enhance depth with radial vignette
    float vignette = exp(-r * r * 0.8);
    col *= vignette * 1.2;
    
    // Subtle glow from field extrema
    float glow = abs(sin(field * PI)) * 0.2;
    col += vec3(glow) * 0.15;
    
    // Ensure values stay in valid range
    col = clamp(col, 0.0, 1.0);
    
    fragColor = vec4(col, 1.0);
}