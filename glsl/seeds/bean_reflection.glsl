// bean_reflection.glsl
// Archetype: reflective_capture
// Technique nodes: sphere_sdf, env_reflection, paraboloid_warp, spiral_offset, sqrt_gamma
// Hypnotic mechanic: convex sphere acts as a fish-eye mirror — viewer sees a distorted
//   reflection of the entire scene compressed into one point. This enclosure archetype
//   creates attentional capture by making the sphere appear to contain an entire world.
//   Slow rotation of the environment behind the sphere generates perpetual discovery.
// Known issues: env_reflection uses an approximate paraboloid warp (not ray-traced);
//   sphere edge may show slight aliasing. Use anti-aliased smoothstep for the SDF boundary.

#define PI 3.14159265

// Simple environment: rotating spiral for reflection
vec3 environment(vec3 dir, float t) {
    // paraboloid_warp: map direction to 2D env coords
    float theta = atan(dir.y, dir.x);
    float phi = acos(clamp(dir.z, -1.0, 1.0));

    // spiral_offset in env space
    float u = (theta / (2.0 * PI) + 0.5) + t * 0.1;
    float v = phi / PI;

    float spiral = sin(u * 12.0 + v * 6.0 - t * 0.5) * 0.5 + 0.5;
    float rings = abs(fract(v * 4.0 - t * 0.2) - 0.5) * 2.0;
    float f = mix(spiral, rings, 0.4);

    // sqrt_gamma for soft env brightness
    f = sqrt(f);

    return vec3(
        f * (0.4 + 0.6 * abs(sin(theta + t * 0.3))),
        f * (0.4 + 0.6 * abs(sin(theta + t * 0.3 + 2.094))),
        f * (0.6 + 0.4 * abs(sin(phi + t * 0.2)))
    );
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);

    // sphere_sdf: sphere at origin, radius 0.45
    float sphere_r = 0.45;
    float dist = length(uv) - sphere_r;

    // Slow breathe: sphere_r oscillates slightly (0.43–0.47)
    sphere_r = 0.45 + 0.02 * sin(iTime * 0.4);

    vec3 col;
    if (dist < 0.0) {
        // Inside sphere: compute env_reflection via convex mirror mapping
        // Normal at surface point (sphere is 2D circle, normal is radial)
        vec2 n2 = normalize(uv);
        vec3 normal = vec3(n2, sqrt(max(0.0, 1.0 - dot(n2, n2))));

        // Incident ray (from screen toward viewer = -Z)
        vec3 ray = normalize(vec3(uv * 0.5, -1.0));

        // Reflect: r = d - 2(d·n)n (env_reflection)
        vec3 reflected = ray - 2.0 * dot(ray, normal) * normal;

        // Sample environment in reflected direction
        col = environment(reflected, iTime);

        // Specular highlight at normal.z peak
        float spec = pow(max(normal.z, 0.0), 8.0);
        col += vec3(1.0, 1.0, 1.0) * spec * 0.4;

    } else {
        // Outside sphere: background environment (rotates slower)
        float theta = atan(uv.y, uv.x);
        float r = length(uv);
        vec3 bg_dir = vec3(cos(theta) * r, sin(theta) * r, 0.5);
        col = environment(normalize(bg_dir), iTime * 0.5) * 0.4;  // dim background

        // Anti-aliased sphere edge
        float edge = smoothstep(0.005, 0.0, dist);
        col = mix(col, vec3(0.1, 0.1, 0.15), edge * 0.5);
    }

    fragColor = vec4(col, 1.0);
}
