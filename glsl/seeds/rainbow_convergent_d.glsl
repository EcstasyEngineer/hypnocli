// shader_id: 5d1ff09b48eb
// archetype: convergent
// colorization: posterized_rainbow
// techniques: log_shear, spiral_offset, sdf_analytic
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

vec3 hsv(float h, float s, float v) {
    float c = v * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    vec3 rgb;
    if (h < 1.0/6.0) rgb = vec3(c, x, 0.0);
    else if (h < 2.0/6.0) rgb = vec3(x, c, 0.0);
    else if (h < 3.0/6.0) rgb = vec3(0.0, c, x);
    else if (h < 4.0/6.0) rgb = vec3(0.0, x, c);
    else if (h < 5.0/6.0) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);
    return rgb + m;
}

float sdf_spiral_arm(float theta, float log_r, float arm_width, float tightness) {
    float spiral_curve = log_r * tightness;
    float theta_normalized = mod(theta / (2.0 * 3.14159) * 4.0, 1.0);
    float angle_phase = spiral_curve / (2.0 * 3.14159);
    float dist = abs(mod(theta_normalized - angle_phase + 0.5, 1.0) - 0.5);
    return dist - arm_width;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float r = length(uv);
    float theta = atan(uv.y, uv.x);
    
    float epsilon = 0.02;
    float log_r = log(r + epsilon);
    
    float tightness = 2.2;
    float spiral_offset = log_r * tightness + iTime * 0.5;
    
    float arms = 4.0;
    float spiral_phase = theta + spiral_offset;
    float arm_angle = mod(spiral_phase / (2.0 * 3.14159) * arms, 1.0);
    
    float arm_width = 0.12;
    float arm_sdf = abs(mod(arm_angle + 0.5, 1.0) - 0.5) - arm_width;
    float arm_glow = exp(-abs(arm_sdf) * 4.0) * 0.8;
    
    float radial_depth = sin(log_r * 5.0 - iTime * 0.8) * 0.5 + 0.5;
    float angular_depth = sin(theta * 3.0 + iTime * 0.6) * 0.5 + 0.5;
    float time_depth = sin(iTime * 1.2) * 0.5 + 0.5;
    
    float composite = arm_glow * 0.6 + radial_depth * 0.25 + angular_depth * 0.15;
    
    float r_inv = 1.0 / (r + 0.05);
    float convergence_pull = exp(-r * 2.5) * 0.7;
    
    float field_value = composite + convergence_pull;
    field_value = mod(field_value, 1.0);
    
    float hue_raw = fract(field_value * 3.5);
    float steps = 7.0;
    float cell = hue_raw * steps;
    float hue = (floor(cell) + smoothstep(0.0, 0.35, fract(cell))) / steps;
    
    vec3 col = hsv(hue, 1.0, 0.9);
    
    float center_depth = 1.0 - smoothstep(0.0, 0.8, r);
    col = mix(col, vec3(1.0), center_depth * 0.3);
    
    float vignette = smoothstep(2.5, 0.3, r);
    col *= vignette;
    
    fragColor = vec4(col, 1.0);
}