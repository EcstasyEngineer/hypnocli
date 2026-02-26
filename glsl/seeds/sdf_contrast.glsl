// shader_id: 2b5069643e86
// archetype: sdf_outline
// techniques: inversion_linear, log_shear, spiral_offset, pow_contrast, decoupled_speeds, fbm_single, fbm_triple_warp
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;

// FBM helper
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    
    float ab = mix(a, b, f.x);
    float cd = mix(c, d, f.x);
    return mix(ab, cd, f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float amp = 1.0;
    float freq = 1.0;
    for(int i = 0; i < 6; i++) {
        v += noise(p * freq) * amp;
        amp *= 0.5;
        freq *= 2.0;
    }
    return v;
}

float sdSpiral(vec2 p, float arms, float tightness, float t) {
    float r = length(p);
    if(r < 0.001) r = 0.001;
    
    float theta = atan(p.y, p.x);
    float log_r = log(r);
    
    float phase = (theta / 6.28318 * arms + log_r * tightness - t);
    float dist = abs(fract(phase + 0.5) - 0.5) / arms;
    
    return dist * r;
}

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    
    // Linear inversion phase offset
    float invPhase = -iTime * 0.15;
    vec2 uvInv = uv * cos(invPhase * 0.3) - vec2(uv.y, -uv.x) * sin(invPhase * 0.3);
    
    // Log shear: use log(r) as coordinate
    float r = length(uv);
    if(r < 0.001) r = 0.001;
    float log_r = log(r);
    
    // Decoupled time speeds
    float t1 = iTime * 0.3;
    float t2 = iTime * 0.39;
    float t3 = iTime * 0.51;
    
    // Spiral offset with log shear
    float spiral1 = sdSpiral(uv, 5.0, 2.2 + log_r * 0.3, t1);
    float spiral2 = sdSpiral(uvInv, 3.0, 1.8 - log_r * 0.2, t2);
    
    // FBM domain warp (triple warp principle)
    vec2 p = uv * 3.0;
    float fbm1 = fbm(p);
    vec2 warped1 = p + fbm1 * 0.4;
    float fbm2 = fbm(warped1 + fbm(warped1) * 0.3);
    vec2 warped2 = warped1 + fbm2 * 0.4;
    float fbm3 = fbm(warped2 + log_r * 2.0);
    
    // Combine spirals and FBM
    float d = min(spiral1 * 0.8, spiral2 * 0.9) * (0.7 + fbm3 * 0.3);
    
    // Glow with inversion principle
    float glow = exp(-d * 25.0);
    float outline = smoothstep(0.02, 0.008, d);
    
    // Pow contrast: k varies between 0.6 and 1.2 over time
    float k = 0.8 + 0.4 * sin(iTime * 0.2);
    float v = pow(glow * 0.8 + outline * 0.6, k);
    
    // Log shear color cycling
    float baseHue = log_r * 0.15 + iTime * 0.08;
    float hue1 = mod(baseHue + fbm1 * 0.2, 1.0);
    float hue2 = mod(baseHue * 1.3 + fbm2 * 0.15 + t2 * 0.05, 1.0);
    
    // Decoupled channel saturation
    vec3 col1 = hsv2rgb(vec3(hue1, 0.7 + 0.2 * sin(t1), v * 0.9));
    vec3 col2 = hsv2rgb(vec3(hue2, 0.65 + 0.25 * sin(t3), v * 0.85));
    
    // Blend with depth layering
    vec3 finalCol = mix(col1, col2, 0.5 + 0.5 * sin(iTime * 0.25));
    
    // Additional radial glow for depth illusion
    float depthGlow = exp(-length(uv) * 1.5) * 0.3;
    finalCol += depthGlow * vec3(0.2, 0.15, 0.3);
    
    // Subtle rotation of the entire pattern
    float rotAngle = iTime * 0.05;
    vec2 rotUV = vec2(
        uv.x * cos(rotAngle) - uv.y * sin(rotAngle),
        uv.x * sin(rotAngle) + uv.y * cos(rotAngle)
    );
    float spiralRot = sdSpiral(rotUV, 4.0, 1.5, iTime * 0.25);
    float glowRot = exp(-spiralRot * 20.0);
    
    finalCol += glowRot * vec3(0.1, 0.12, 0.15) * pow(v, 0.5);
    
    // Smooth falloff at edges for vignette
    float vignette = smoothstep(2.5, 0.5, length(uv));
    finalCol *= vignette;
    
    fragColor = vec4(finalCol, 1.0);
}