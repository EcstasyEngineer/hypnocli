// shader_id: f3094d9feaaf
// archetype: sdf_outline
// colorization: field_rainbow
// techniques: spiral_offset, sdf_analytic
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

vec3 hsv(float h, float s, float v) {
    h = fract(h);
    float c = v * s;
    float x = c * (1.0 - abs(mod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    vec3 rgb;
    if (h < 0.1667) rgb = vec3(c, x, 0.0);
    else if (h < 0.3333) rgb = vec3(x, c, 0.0);
    else if (h < 0.5) rgb = vec3(0.0, c, x);
    else if (h < 0.6667) rgb = vec3(0.0, x, c);
    else if (h < 0.8333) rgb = vec3(x, 0.0, c);
    else rgb = vec3(c, 0.0, x);
    return rgb + m;
}

float sdSpiral(vec2 p, float arms, float tightness, float t) {
    float r = length(p);
    if (r < 0.001) return 0.0;
    
    float theta = atan(p.y, p.x);
    float log_r = log(r);
    
    float phase = (theta / (2.0 * 3.14159265) * arms + log_r * tightness - t);
    float frac = fract(phase + 0.5) - 0.5;
    float dist = abs(frac) * (2.0 / arms);
    
    return dist * r;
}

float sdNestedRings(vec2 p, float t) {
    float r = length(p);
    if (r < 0.001) return 1.0;
    
    float wave = sin(r * 12.0 - t * 2.5) * 0.5 + 0.5;
    float ring = abs(fract(r * 3.5 - t * 0.8) - 0.5);
    
    return ring * (0.3 + 0.7 * wave);
}

float sdRadialWave(vec2 p, float t) {
    float r = length(p);
    float theta = atan(p.y, p.x);
    
    float wave = sin(theta * 7.0 - t) * sin(r * 8.0 - t * 1.3);
    float radial = sin(r * 15.0 - t * 2.0) * 0.5 + 0.5;
    
    return fract(wave * radial + t * 0.3);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    float t = iTime;
    
    float d1 = sdSpiral(uv, 5.0, 2.2, t * 0.4);
    float d2 = sdSpiral(uv * 0.6, 4.0, 1.8, t * 0.35);
    float d3 = sdNestedRings(uv, t);
    float d4 = sdRadialWave(uv, t);
    
    float glow1 = exp(-d1 * 25.0);
    float glow2 = exp(-d2 * 28.0);
    float glow3 = exp(-d3 * 18.0);
    float glow4 = exp(-d4 * 12.0);
    
    float outline1 = smoothstep(0.02, 0.008, d1);
    float outline2 = smoothstep(0.018, 0.007, d2);
    
    float field = glow1 * 0.4 + glow2 * 0.35 + glow3 * 0.15 + glow4 * 0.1;
    field += outline1 * 0.3 + outline2 * 0.2;
    
    float r = length(uv);
    float convergent = sin(r * 3.0 - t * 1.5) * exp(-r * 1.2);
    field += convergent * 0.15;
    
    float depth_layer = pow(1.0 / (1.0 + r * 0.8), 0.5);
    field = field * depth_layer;
    
    float hue = fract(field * 1.8 + t * 0.25);
    vec3 col = hsv(hue, 1.0, 0.85);
    
    float brightness = pow(field, 0.7);
    col = col * brightness;
    
    col += vec3(0.05 * sin(t * 0.3 + r * 5.0));
    
    fragColor = vec4(col, 1.0);
}