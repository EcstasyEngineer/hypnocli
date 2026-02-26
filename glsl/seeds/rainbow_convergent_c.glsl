// shader_id: 7820b1207770
// archetype: convergent
// colorization: posterized_rainbow
// techniques: inversion_linear, spiral_offset, sdf_analytic
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

vec3 hsv(float h, float s, float v) {
    float c = v * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    vec3 rgb = vec3(0.0);
    
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
    
    // Layer 1: GEOMETRY
    // Radial inversion with linear negation for counter-rotating symmetry
    float r = length(uv);
    float r_safe = max(r, 0.005);
    
    // inversion_linear: create convergent field
    float r_inv = 1.0 / (r_safe + 0.02);
    
    // Angular coordinate
    float theta = atan(uv.y, uv.x);
    
    // spiral_offset: logarithmic spiral with tightness
    float log_r = log(r_safe + 0.001);
    float arm_count = 5.0;
    float tightness = 2.2;
    
    // Decoupled time speeds for animation
    float t1 = iTime * 0.8;
    float t2 = iTime * 1.04;
    float t3 = iTime * 1.36;
    
    // Spiral phase with inversion_linear counter-rotation
    float spiral_phase = theta * arm_count / (2.0 * 3.14159) + log_r * tightness - t1 * 0.6;
    
    // sdf_analytic: compute signed distance to spiral arm
    float arm_width = 0.15;
    float spiral_wave = sin(spiral_phase * 6.28318) * 0.5 + 0.5;
    float spiral_sdf = abs(spiral_wave - 0.5) * 2.0;
    float arm_glow = exp(-spiral_sdf * 8.0);
    
    // Radial depth field with decoupled speed
    float radial_modulation = sin(log_r * 5.5 + t2 * 1.2) * 0.5 + 0.5;
    float radial_sdf = smoothstep(0.4, 0.0, abs(radial_modulation - 0.5));
    
    // Combine geometry layers
    float field_value = arm_glow * 0.7 + radial_sdf * 0.3;
    
    // Add convergent center pull
    float convergence_pull = exp(-r_inv * 0.3) * 0.8;
    field_value = mix(field_value, 1.0, convergence_pull * 0.4);
    
    // Layer 2: COLORIZATION - posterized_rainbow (EXACTLY as specified)
    float field_scaled = field_value;
    float scale = 3.5 + sin(t3 * 0.5) * 0.5;
    
    float hue_raw = fract(field_scaled * scale);
    float steps = 7.0;
    float cell = hue_raw * steps;
    float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;
    
    vec3 col = hsv(hue, 1.0, 0.9);
    
    // Layer 3: SHAPING - sqrt_gamma for perceptually smooth falloff
    // Add depth illusion through nested modulation
    float depth_wave = sin(log_r * 7.2 - t1 * 0.8) * 0.5 + 0.5;
    float brightness_modulation = field_value * depth_wave;
    
    // sqrt_gamma correction
    brightness_modulation = sqrt(brightness_modulation);
    
    col *= brightness_modulation;
    
    // Secondary spiral at different phase for interference pattern
    float spiral_phase_2 = theta * arm_count / (2.0 * 3.14159) - log_r * tightness * 0.8 + t2 * 0.4;
    float spiral_wave_2 = sin(spiral_phase_2 * 6.28318) * 0.5 + 0.5;
    float spiral_sdf_2 = abs(spiral_wave_2 - 0.5) * 2.0;
    float arm_glow_2 = exp(-spiral_sdf_2 * 6.0);
    
    // Blend secondary for depth
    float hue_raw_2 = fract((1.0 - arm_glow_2) * scale * 1.3);
    float cell_2 = hue_raw_2 * steps;
    float hue_2 = (floor(cell_2) + smoothstep(0.0, 0.35, fract(cell_2))) / steps;
    vec3 col_2 = hsv(hue_2, 0.95, 0.85);
    
    col = mix(col, col_2, arm_glow_2 * 0.4);
    
    // Vanishing point glow
    float vanish_glow = exp(-r_inv * 0.15) * 0.5;
    col += vec3(0.3, 0.2, 0.5) * vanish_glow;
    
    // Feather edges to prevent hard cutoff
    float edge_fade = smoothstep(2.5, 0.5, r);
    col *= edge_fade;
    
    fragColor = vec4(col, 1.0);
}