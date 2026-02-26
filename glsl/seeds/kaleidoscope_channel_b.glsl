// shader_id: 227cb7aa6e34
// archetype: kaleidoscopic
// colorization: channel_offset
// techniques: spiral_offset
#define PI 3.14159265359
#define TAU 6.28318530718

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // fract_time_precision: wrap phase for long sessions
    float t = fract(iTime * 0.1) * 10.0;
    
    // arm_count: 8-fold kaleidoscopic symmetry
    float N = 8.0;
    float sector = TAU / N;
    float t_folded = mod(theta, sector);
    if (t_folded > sector * 0.5) t_folded = sector - t_folded;
    
    // Reconstruct folded UV
    vec2 uv_fold = r * vec2(cos(t_folded), sin(t_folded));
    
    // Depth illusion: logarithmic inversion creates infinite recession
    float depth = log(r + 0.1) * 0.5;
    
    // Convergent motion: pull toward center via modified radius
    float r_pull = r - depth * 0.3;
    r_pull = max(r_pull, 0.01);
    
    // spiral_offset: logarithmic spiral winds arms inward
    float spiral_phase = t_folded * N * 2.0 + log(r_pull + 0.1) * 2.5;
    
    // Decoupled rotation speeds create vortex without nausea
    float inner_rot = sin(t * 0.3) * PI;
    float outer_rot = cos(t * 0.5) * PI;
    float rot_mix = smoothstep(0.1, 0.7, r);
    float rotation = mix(inner_rot, outer_rot, rot_mix);
    
    // Main oscillating field
    float field = sin(spiral_phase + rotation + depth * 3.0) * 0.5 + 0.5;
    
    // triangle_wave: create animated ring pattern
    float ring_phase = fract(r * 4.0 - t * 0.25);
    float rings = abs(ring_phase - 0.5) * 2.0;
    
    // Combine field and rings
    float pattern = mix(field, rings, 0.35 + 0.2 * sin(t * 0.7));
    
    // Additional radial oscillation for motion
    float radial_osc = sin(r * 8.0 - t * 2.0) * 0.3 + 0.7;
    pattern *= radial_osc;
    
    // Spiral distortion layer
    float spiral_dist = sin(t_folded * 3.0 + t * 1.2) * 0.2;
    float dist_r = r + spiral_dist;
    dist_r = max(dist_r, 0.01);
    
    // Secondary field with different frequency
    float field2 = sin(dist_r * 6.0 + t * 0.8 + theta * 4.0) * 0.5 + 0.5;
    pattern = mix(pattern, field2, 0.25);
    
    // sqrt_gamma: perceptually smooth falloff and brightness
    pattern = sqrt(max(pattern, 0.0));
    
    // channel_offset: chromatic aberration via phase offset
    float r_base = pattern;
    
    // Construct field_func equivalent with channel offsets
    float field_r = sin(spiral_phase + rotation + depth * 3.0 + t * 1.0) * 0.5 + 0.5;
    float field_g = sin(spiral_phase + rotation + depth * 3.0 + t * 1.0 + 1.047) * 0.5 + 0.5;
    float field_b = sin(spiral_phase + rotation + depth * 3.0 + t * 1.0 + 2.094) * 0.5 + 0.5;
    
    // Apply sqrt_gamma to each channel
    field_r = sqrt(max(field_r, 0.0));
    field_g = sqrt(max(field_g, 0.0));
    field_b = sqrt(max(field_b, 0.0));
    
    // Blend with secondary patterns
    field_r = mix(field_r, field2, 0.2) * pattern;
    field_g = mix(field_g, field2 * 0.8, 0.2) * pattern;
    field_b = mix(field_b, field2 * 1.2, 0.2) * pattern;
    
    // Radial falloff for depth
    float vignette = exp(-r * r * 0.8);
    
    vec3 col = vec3(field_r, field_g, field_b) * vignette;
    
    // Smooth saturation shift over time
    float hue_shift = sin(t * 0.3) * 0.5 + 0.5;
    col += vec3(
        sin(hue_shift * PI) * 0.2,
        sin(hue_shift * PI + 2.094) * 0.2,
        sin(hue_shift * PI + 4.189) * 0.2
    ) * pattern;
    
    // Final contrast enhancement
    col = mix(col, col * col, 0.3);
    
    fragColor = vec4(col, 1.0);
}