// shader_id: 545a8dc3d69f
// archetype: sdf_outline
// colorization: field_rainbow
// techniques: arm_count, sdf_analytic
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

vec3 hsv(float h, float s, float v) {
    float c = v * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    vec3 col = vec3(0.0);
    if(h < 0.16667) col = vec3(c, x, 0.0);
    else if(h < 0.33333) col = vec3(x, c, 0.0);
    else if(h < 0.5) col = vec3(0.0, c, x);
    else if(h < 0.66667) col = vec3(0.0, x, c);
    else if(h < 0.83333) col = vec3(x, 0.0, c);
    else col = vec3(c, 0.0, x);
    return col + m;
}

float sdSpiral(vec2 p, float arms, float tightness, float t) {
    float r = length(p);
    if(r < 0.001) r = 0.001;
    float theta = atan(p.y, p.x);
    float log_r = log(r);
    
    float phase = (theta / 6.28318530718 * arms + log_r * tightness - t);
    float isoline = abs(fract(phase + 0.5) - 0.5);
    
    return isoline * r * 0.5;
}

float triangleWave(float x) {
    return abs(fract(x) - 0.5) * 2.0;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float t = iTime * 0.4;
    float arm_count = 4.0;
    float tightness = 2.2;
    
    float d = sdSpiral(uv, arm_count, tightness, t);
    
    float glow = exp(-d * 25.0);
    float outline = smoothstep(0.02, 0.008, d);
    
    float brightness = glow + outline * 0.6;
    brightness = sqrt(brightness);
    
    float r = length(uv);
    float field_value = fract(r * 3.0 + log(r + 0.2) * 1.5 + t * 0.5);
    
    float tri_wave = triangleWave(field_value * 2.0);
    field_value = mix(field_value, tri_wave, 0.3);
    
    float hue = fract(field_value * 2.5 + iTime * 0.15);
    vec3 col = hsv(hue, 0.95, 0.88);
    
    float depth_factor = 1.0 / (1.0 + r * 0.8);
    brightness *= depth_factor;
    
    float pulsing = 0.9 + 0.1 * sin(iTime * 1.5 + r * 3.0);
    brightness *= pulsing;
    
    col *= brightness;
    col += vec3(0.05) * glow;
    
    fragColor = vec4(col, 1.0);
}