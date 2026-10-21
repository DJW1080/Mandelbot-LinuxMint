#version 400 core

uniform sampler2D uImage;
uniform vec2 uResolution;
uniform vec2 uScale;
uniform float uOpacity;
out vec4 fragmentColour;

void main() {
    // The camera follows the exact exponential path between completed detail frames.
    vec2 uv = (gl_FragCoord.xy / uResolution - 0.5) * uScale + 0.5;
    vec3 linearColour = texture(uImage, uv).rgb;
    // sRGB textures filter in linear light, avoiding dark seams during movement.
    vec3 colour = mix(linearColour * 12.92,
        1.055 * pow(linearColour, vec3(1.0 / 2.4)) - 0.055,
        greaterThan(linearColour, vec3(0.0031308)));
    fragmentColour = vec4(colour * uOpacity, 1.0);
}
