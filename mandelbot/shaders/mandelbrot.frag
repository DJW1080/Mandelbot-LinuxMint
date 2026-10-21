#version 400 core

uniform dvec2 uCentre;
uniform double uPixelSpan;
uniform vec2 uResolution;
uniform int uIterations;
uniform int uSamples;
const int PALETTE_STOP_COUNT = __PALETTE_STOP_COUNT__;
uniform vec3 uPaletteStops[PALETTE_STOP_COUNT];
uniform float uPhase;
uniform float uOpacity;
uniform int uDiagnostic;
out vec4 fragmentColour;

const double ESCAPE_RADIUS_SQUARED = 65536.0LF;
const double CLASSIC_ESCAPE_SQUARED = 4.0LF;
const vec3 INTERIOR = vec3(5.0, 9.0, 15.0) / 255.0;
const float COLOUR_CYCLES_PER_ITERATION = 0.028;
const vec2 SAMPLE_OFFSETS[4] = vec2[4](
    vec2(-0.375, -0.125), vec2(0.125, -0.375),
    vec2(0.375, 0.125), vec2(-0.125, 0.375));

bool knownInterior(dvec2 c) {
    double shifted = c.x - 0.25LF;
    double imaginarySquared = c.y * c.y;
    double radius = shifted * shifted + imaginarySquared;
    bool cardioid = radius * (radius + shifted) <= 0.25LF * imaginarySquared;
    bool bulb = (c.x + 1.0LF) * (c.x + 1.0LF) + imaginarySquared <= 0.0625LF;
    return cardioid || bulb;
}

// The diagnostic uses the same orbit arithmetic with the classical escape radius.
vec2 orbit(dvec2 c) {
    if (knownInterior(c)) return vec2(float(uIterations), 0.0);
    precise dvec2 z = dvec2(0.0LF);
    double magnitudeSquared = 0.0LF;
    double escapeSquared = uDiagnostic == 1 ? CLASSIC_ESCAPE_SQUARED : ESCAPE_RADIUS_SQUARED;
    int iteration = 0;
    for (; iteration < uIterations; ++iteration) {
        z = dvec2(z.x * z.x - z.y * z.y, 2.0LF * z.x * z.y) + c;
        magnitudeSquared = dot(z, z);
        if (magnitudeSquared > escapeSquared) {
            ++iteration;
            break;
        }
    }
    if (iteration >= uIterations) return vec2(float(uIterations), 0.0);
    float smoothIteration = float(iteration) + 1.0 - log2(log(sqrt(float(magnitudeSquared))));
    return vec2(float(iteration), smoothIteration);
}

vec3 paletteStop(int index) {
    return uPaletteStops[(index + PALETTE_STOP_COUNT) % PALETTE_STOP_COUNT] / 255.0;
}

vec3 palette(float smoothIteration) {
    float position = fract(smoothIteration * COLOUR_CYCLES_PER_ITERATION + uPhase) * float(PALETTE_STOP_COUNT);
    int index = int(floor(position));
    float t = fract(position);
    vec3 before = paletteStop(index - 1);
    vec3 first = paletteStop(index);
    vec3 second = paletteStop(index + 1);
    vec3 after = paletteStop(index + 2);
    // Cyclic Catmull-Rom interpolation has continuous slopes at the colour stops.
    return clamp(0.5 * ((2.0 * first) + (-before + second) * t
        + (2.0 * before - 5.0 * first + 4.0 * second - after) * t * t
        + (-before + 3.0 * first - 3.0 * second + after) * t * t * t), 0.0, 1.0);
}

vec3 toLinear(vec3 colour) {
    return mix(colour / 12.92, pow((colour + 0.055) / 1.055, vec3(2.4)),
               greaterThan(colour, vec3(0.04045)));
}

vec3 toSRGB(vec3 colour) {
    return mix(colour * 12.92, 1.055 * pow(colour, vec3(1.0 / 2.4)) - 0.055,
               greaterThan(colour, vec3(0.0031308)));
}

dvec2 coordinate(vec2 offset) {
    dvec2 pixel = dvec2(gl_FragCoord.xy + offset) - dvec2(uResolution) * 0.5LF;
    // Share the CPU's correctly rounded pixel spacing and prevent FMA contraction.
    precise dvec2 point = uCentre + pixel * uPixelSpan;
    return point;
}

void main() {
    if (uDiagnostic == 1) {
        int count = int(orbit(coordinate(vec2(0.0))).x);
        fragmentColour = vec4(float(count & 255) / 255.0, float(count >> 8) / 255.0, 0.0, 1.0);
        return;
    }
    vec3 linearColour = vec3(0.0);
    for (int index = 0; index < uSamples; ++index) {
        vec2 offset = uSamples == 1 ? vec2(0.0) : SAMPLE_OFFSETS[index];
        if (uSamples == 2) offset = index == 0 ? vec2(-0.25) : vec2(0.25);
        vec2 result = orbit(coordinate(offset));
        vec3 colour = result.x >= float(uIterations) ? INTERIOR : palette(result.y);
        linearColour += toLinear(colour);
    }
    vec3 colour = toSRGB(linearColour / float(uSamples)) * uOpacity;
    // Stationary sub-LSB dithering softens 8-bit gradients without temporal noise.
    float noise = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))));
    fragmentColour = vec4(clamp(colour + (noise - 0.5) / 255.0, 0.0, 1.0), 1.0);
}
