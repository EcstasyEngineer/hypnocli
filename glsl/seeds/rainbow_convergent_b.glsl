// shader_id: be3df88a8199
// archetype: convergent
// colorization: posterized_rainbow
// techniques: inversion_linear, inversion_sqrt, spiral_offset, sdf_analytic
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // inversion_sqrt: compress outer distance toward center
    float r_inv = 1.0 / (r + 0.01);
    
    // spiral_offset: logarithmic spiral arms
    float log_r = log(r + 0.001);
    float arm_count = 5.0;
    float tightness = 2.2;
    float spiral_phase = theta / 6.28318 * arm_count + log_r * tightness + iTime * 0.35;
    
    // decoupled_speeds: multiple time scales prevent adaptation
    float time_1 = iTime * 1.0;
    float time_2 = iTime * 1.3;
    float time_3 = iTime * 1.7;
    
    // sdf_analytic: signed distance to spiral arm
    float wave1 = sin(spiral_phase * 6.28318);
    float wave2 = sin(spiral_phase * 6.28318 + time_2 * 0.5);
    float field_base = mix(wave1, wave2, 0.5) * 0.5 + 0.5;
    
    // Radial depth modulation: creates 3D recession illusion
    float depth_scale = 1.0 / (1.0 + r * 2.0);
    float radial_wave = sin(log_r * 5.0 + time_1 * 0.8) * 0.5 + 0.5;
    float radial_wave2 = sin(log_r * 7.0 + time_3 * 0.6) * 0.5 + 0.5;
    
    // Convergent glow: pulls attention to center
    float convergence_glow = exp(-r * 3.5) * (1.0 + 0.5 * sin(time_1 * 2.0));
    
    // Compose field value for colorization
    float field_value = field_base * 0.4 + radial_wave * 0.3 + radial_wave2 * 0.3;
    field_value = mix(field_value, convergence_glow, smoothstep(0.0, 0.3, 1.0 - r));
    
    // Spiral arm glow: creates sharp bright ridges
    float arm_sharpness = 4.0;
    float arm_glow = exp(-abs(wave1) * arm_sharpness) * 0.6;
    field_value += arm_glow * 0.4;
    
    // posterized_rainbow colorization (EXACTLY as specified)
    float hue_raw = fract(field_value * 3.5);
    float steps = 7.0;
    float cell = hue_raw * steps;
    float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;
    
    // hsv to rgb conversion
    vec3 col = vec3(0.0);
    float h = hue * 6.0;
    float x = (1.0 - abs(mod(h, 2.0) - 1.0));
    
    if (h < 1.0) col = vec3(1.0, x, 0.0);
    else if (h < 2.0) col = vec3(x, 1.0, 0.0);
    else if (h < 3.0) col = vec3(0.0, 1.0, x);
    else if (h < 4.0) col = vec3(0.0, x, 1.0);
    else if (h < 5.0) col = vec3(x, 0.0, 1.0);
    else col = vec3(1.0, 0.0, x);
    
    col *= 0.9;  // posterized_rainbow: full saturation, V=0.9
    
    // Extra depth via brightness modulation
    float brightness_mod = 0.7 + 0.3 * sin(iTime * 0.4 + theta * 3.0);
    col *= brightness_mod;
    
    // Center convergence brightening
    col += convergence_glow * vec3(0.2, 0.1, 0.3) * 0.8;
    
    // Smooth out near-center to prevent singularities
    col *= smoothstep(0.0, 0.05, r);
    
    fragColor = vec4(col, 1.0);
}