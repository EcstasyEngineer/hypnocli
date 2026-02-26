// shader_id: 112b930af900
// archetype: kaleidoscopic
// colorization: channel_offset
// techniques: spiral_offset
#define PI 3.14159265359
#define TAU 6.28318530718

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    // Fract time precision wrapper for long sessions
    float time_wrapped = fract(iTime * 0.1) * 10.0;
    
    // N-fold kaleidoscope symmetry
    float N = 8.0;
    float sector = TAU / N;
    float t_folded = mod(theta, sector);
    if (t_folded > sector * 0.5) {
        t_folded = sector - t_folded;
    }
    
    // Decoupled rotation speeds for vortex effect
    float inner_speed = 0.15;
    float outer_speed = 0.35;
    float depth_mix = smoothstep(0.1, 1.2, r);
    float rot_angle = mix(inner_speed, outer_speed, depth_mix) * time_wrapped;
    
    // Spiral offset: logarithmic spiral winds the arms
    float tightness = 2.5;
    float spiral_phase = t_folded * N + log(max(r, 0.01)) * tightness + rot_angle;
    float spiral_field = sin(spiral_phase) * 0.5 + 0.5;
    
    // Convergent radial waves pull toward center
    float radial_wave = sin(r * 12.0 - time_wrapped * 0.8 + spiral_phase * 0.3);
    float wave_ring = abs(fract(r * 6.0 - time_wrapped * 0.25) - 0.5) * 2.0;
    
    // Triangle wave shaping for sharper depth perception
    float tri_wave = abs(fract(r * 8.0 + time_wrapped * 0.1) - 0.5) * 2.0;
    
    // Layer combination with depth modulation
    float base_field = spiral_field * 0.4 + wave_ring * 0.3 + radial_wave * 0.1 + tri_wave * 0.2;
    
    // Convergent focal point enhancement
    float focal_pull = 1.0 / (0.3 + r * r);
    float field_combined = base_field * (0.7 + focal_pull * 0.3);
    
    // Sqrt gamma correction for perceptually smooth falloff
    field_combined = sqrt(max(field_combined, 0.0));
    
    // Channel offset colorization (EXACTLY as specified)
    vec3 col = vec3(
        field_combined * (0.5 + 0.5 * sin(time_wrapped * 1.00 + spiral_phase)),
        field_combined * (0.5 + 0.5 * sin(time_wrapped * 1.00 + spiral_phase + 1.047)),
        field_combined * (0.5 + 0.5 * sin(time_wrapped * 1.00 + spiral_phase + 2.094))
    );
    
    // Chromatic aberration shimmer from phase offset
    float chroma_offset = 0.03 * sin(time_wrapped * 0.3 + r * 5.0);
    col.r += chroma_offset * 0.15;
    col.b -= chroma_offset * 0.1;
    
    // Outer vignette for infinite depth illusion
    float vignette = smoothstep(2.0, 0.0, r);
    col *= mix(0.3, 1.0, vignette);
    
    // Pulsing center for hypnotic draw
    float pulse = 0.5 + 0.5 * sin(time_wrapped * 0.6 + r * 3.0);
    col += vec3(0.1, 0.05, 0.15) * pulse / (0.5 + r * 2.0);
    
    fragColor = vec4(col, 1.0);
}