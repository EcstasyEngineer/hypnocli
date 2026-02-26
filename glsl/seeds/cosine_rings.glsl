// shader_id: 7cf547c0a3a8
// archetype: linear_rings
// techniques: log_shear, inversion_linear, spiral_offset, arm_count, abs_fold, triangle_wave, iq_cosine_palette, channel_time_offset, fbm_triple_warp
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // log_shear: logarithmic radial coordinate for self-similarity
    float logr = log(r + 1.5);
    
    // spiral_offset: wind arms into logarithmic spiral
    float tightness = 2.8;
    float spiral_phase = logr * tightness;
    
    // arm_count: 4 arms for balanced hypnotic pattern
    float arm_count = 4.0;
    float arm_phase = theta * arm_count;
    
    // inversion_linear: counter-rotating arms via negated phase offset
    float arm1_phase = arm_phase + spiral_phase - iTime * 1.2;
    float arm2_phase = arm_phase - spiral_phase + iTime * 0.9;
    
    // oscillating arm strength with depth modulation
    float arm1 = sin(arm1_phase) * (0.5 + 0.5 * sin(iTime * 0.7));
    float arm2 = sin(arm2_phase) * (0.5 + 0.5 * cos(iTime * 0.5));
    
    // abs_fold: fold negative values to create symmetric ripple
    float interference = abs(arm1 * arm2);
    float arm_strength = abs(arm1) + abs(arm2);
    
    // triangle_wave: smooth ring pattern using abs(fract(x) - 0.5) * 2
    float ring_radii = r * 8.0 - iTime * 0.4;
    float rings = abs(fract(ring_radii) - 0.5) * 2.0;
    rings = mix(rings, 1.0 - rings, 0.5);
    
    // fbm_triple_warp: organic non-repeating flow
    // Simplified warp using layered sine waves for compile-time safety
    float warp1 = sin(logr * 3.5 + iTime * 0.3) * 0.4;
    float warp2 = sin(theta * 5.0 - iTime * 0.5) * 0.3;
    float warp3 = sin((logr + warp1) * 2.0 + iTime * 0.2) * 0.2;
    
    float warped_r = r + warp1 + warp2 * 0.1;
    float warped_theta = theta + warp3;
    
    // Recalculate with warped coordinates for organic flow
    float organic_base = sin(warped_theta * 6.0 + warped_r * 5.0 - iTime * 0.8);
    organic_base = abs(organic_base);
    
    // Combine patterns with depth perception
    float depth_layer = exp(-r * 1.5) * 0.7;
    float mid_layer = interference * rings * (0.5 + 0.5 * sin(iTime * 0.4));
    float surface = arm_strength * organic_base * (1.0 - r * 0.4);
    
    float pattern = mix(mid_layer, surface, 0.6) + depth_layer * 0.4;
    pattern = smoothstep(0.0, 1.0, pattern);
    
    // channel_time_offset: RGB on different phase clocks for chromatic drift
    // Offset each by 2π/3 (approximately 2.09)
    float phase_r = iTime * 0.6 + 0.0;
    float phase_g = iTime * 0.6 + 2.09;
    float phase_b = iTime * 0.6 + 4.19;
    
    // iq_cosine_palette: Inigo Quilez smooth perceptually uniform colors
    vec3 palette_a = vec3(0.5, 0.5, 0.5);
    vec3 palette_b = vec3(0.5, 0.5, 0.5);
    vec3 palette_c = vec3(1.0, 1.0, 1.0);
    vec3 palette_d = vec3(0.0, 0.33, 0.67);
    
    vec3 col_r = palette_a + palette_b * cos(6.28318 * (palette_c * sin(phase_r) * 0.5 + palette_d));
    vec3 col_g = palette_a + palette_b * cos(6.28318 * (palette_c * sin(phase_g) * 0.5 + palette_d + 0.33));
    vec3 col_b = palette_a + palette_b * cos(6.28318 * (palette_c * sin(phase_b) * 0.5 + palette_d + 0.67));
    
    float contrast = 1.8;
    float r_channel = pow(col_r.r, 2.2) * pattern * contrast;
    float g_channel = pow(col_g.g, 2.2) * pattern * contrast * 0.9;
    float b_channel = pow(col_b.b, 2.2) * pattern * contrast * 1.1;
    
    // Add glow halos at structure edges
    float edge_glow = smoothstep(0.8, 0.1, abs(fract(ring_radii) - 0.5)) * 0.4;
    r_channel += edge_glow * col_r.r;
    g_channel += edge_glow * col_g.g;
    b_channel += edge_glow * col_b.b;
    
    // Vignette and radial falloff for convergent motion
    float vignette = smoothstep(2.0, 0.3, r);
    
    vec3 col = vec3(r_channel, g_channel, b_channel) * vignette;
    
    fragColor = vec4(col, 1.0);
}