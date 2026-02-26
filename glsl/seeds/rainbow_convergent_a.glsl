// shader_id: 728549fb0cea
// archetype: convergent
// colorization: posterized_rainbow
// techniques: inversion_sqrt, arm_count, spiral_offset
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

vec3 hsv2rgb(vec3 hsv) {
    vec3 rgb;
    float h = hsv.x * 6.0;
    float i = floor(h);
    float f = h - i;
    float p = hsv.z * (1.0 - hsv.y);
    float q = hsv.z * (1.0 - hsv.y * f);
    float t = hsv.z * (1.0 - hsv.y * (1.0 - f));
    
    if (i < 1.0) rgb = vec3(hsv.z, t, p);
    else if (i < 2.0) rgb = vec3(q, hsv.z, p);
    else if (i < 3.0) rgb = vec3(p, hsv.z, t);
    else if (i < 4.0) rgb = vec3(p, q, hsv.z);
    else if (i < 5.0) rgb = vec3(t, p, hsv.z);
    else rgb = vec3(hsv.z, p, q);
    
    return rgb;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float r = length(uv);
    float r_inv = 1.0 / (r + 0.01);
    
    float theta = atan(uv.y, uv.x);
    float log_r = log(r + 0.001);
    
    float arm_count = 4.0;
    float tightness = 2.0;
    
    float t1 = iTime * 0.4;
    float t2 = iTime * 0.52;
    float t3 = iTime * 0.68;
    
    float spiral_phase = theta / (2.0 * 3.14159) * arm_count + log_r * tightness + t1;
    
    float angle_component = sin(spiral_phase * 6.28318) * 0.5 + 0.5;
    float radial_component = sin(log_r * 8.0 - t2 * 1.2) * 0.5 + 0.5;
    float modulation = cos(r * 5.0 + t3 * 0.9) * 0.5 + 0.5;
    
    float field_value = (angle_component * 0.5 + radial_component * 0.3 + modulation * 0.2);
    
    float glow = exp(-r * 3.0) * 0.8;
    float convergence_pull = smoothstep(2.0, 0.0, r_inv * 0.15);
    
    float field_with_glow = field_value + glow * 0.4 + convergence_pull * 0.3;
    
    float scale = 3.5;
    float hue_raw = fract(field_with_glow * scale);
    float steps = 7.0;
    float cell = hue_raw * steps;
    float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;
    
    vec3 col = hsv2rgb(vec3(hue, 1.0, 0.9));
    
    float depth_darkening = smoothstep(3.0, 0.0, r);
    col *= (0.3 + depth_darkening * 0.7);
    
    float vignette = smoothstep(2.5, 0.5, r);
    col *= vignette;
    
    fragColor = vec4(col, 1.0);
}