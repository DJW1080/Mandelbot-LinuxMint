/* Original Mandelbot renderer: z[n+1] = z[n]^2 + c, z[0] = 0.
 * The caller owns the pixel buffer; no global mutable state is used. */
#include <math.h>
#include <stddef.h>
#include <stdint.h>

static const double ESCAPE_RADIUS_SQUARED = 4.0;
static const double LOG_TWO = 0.69314718055994530942;
static const double COLOUR_CYCLES_PER_ITERATION = 0.028;
static const uint32_t INTERIOR_COLOUR = 0xff05090f;
enum { MAX_DIMENSION = 1920, MAX_ITERATIONS = 4096, RGB_CHANNELS = 3,
       MIN_PALETTE_STOPS = 2, MAX_PALETTE_STOPS = 256, MAX_PIXELS = 4000000 };

static int known_interior(double real, double imaginary) {
    const double shifted_real = real - 0.25;
    const double imaginary_squared = imaginary * imaginary;
    const double cardioid_distance = shifted_real * shifted_real + imaginary_squared;
    const double bulb_real = real + 1.0;
    return cardioid_distance * (cardioid_distance + shifted_real)
               <= 0.25 * imaginary_squared
        || bulb_real * bulb_real + imaginary_squared <= 0.0625;
}

static int iterate(double real, double imaginary, int limit, double *magnitude) {
    double orbit_real = 0.0, orbit_imaginary = 0.0;
    double real_squared = 0.0, imaginary_squared = 0.0;
    int iteration = 0;
    while (iteration < limit && real_squared + imaginary_squared <= ESCAPE_RADIUS_SQUARED) {
        orbit_imaginary = 2.0 * orbit_real * orbit_imaginary + imaginary;
        orbit_real = real_squared - imaginary_squared + real;
        real_squared = orbit_real * orbit_real;
        imaginary_squared = orbit_imaginary * orbit_imaginary;
        ++iteration;
    }
    *magnitude = real_squared + imaginary_squared;
    return iteration;
}

int mb_escape(double real, double imaginary, int limit) {
    if (!isfinite(real) || !isfinite(imaginary) || limit < 1 || limit > MAX_ITERATIONS)
        return -1;
    if (known_interior(real, imaginary)) return limit;
    double magnitude;
    return iterate(real, imaginary, limit, &magnitude);
}

static uint32_t escape_colour(int iteration, double magnitude,
                              const unsigned char *palette, int palette_stops, double phase) {
    /* Continuous escape counts remove harsh integer iteration bands. */
    const double smooth = iteration + 1.0 - log(log(sqrt(magnitude))) / LOG_TWO;
    double position = smooth * COLOUR_CYCLES_PER_ITERATION + phase;
    position = (position - floor(position)) * palette_stops;
    const int first = (int)position;
    const int second = (first + 1) % palette_stops;
    const double fraction = position - first;
    uint32_t colour = 0xff000000;
    for (int channel = 0; channel < RGB_CHANNELS; ++channel) {
        const double value = palette[first * RGB_CHANNELS + channel] * (1.0 - fraction)
                           + palette[second * RGB_CHANNELS + channel] * fraction;
        colour |= (uint32_t)(value + 0.5) << (16 - 8 * channel);
    }
    return colour;
}

int mb_render(uint32_t *pixels, int width, int height, double centre_real,
              double centre_imaginary, double span, int limit,
              const unsigned char *palette, int palette_stops, double phase) {
    if (!pixels || width < 1 || height < 1 || width > MAX_DIMENSION
        || height > MAX_DIMENSION || (size_t)width * height > MAX_PIXELS
        || !isfinite(centre_real) || !isfinite(centre_imaginary)
        || fabs(centre_real) > 4.0 || fabs(centre_imaginary) > 4.0
        || !isfinite(span) || span < 0.0000001 || span > 8.0
        || !isfinite(phase) || limit < 1 || limit > MAX_ITERATIONS
        || !palette || palette_stops < MIN_PALETTE_STOPS
        || palette_stops > MAX_PALETTE_STOPS) return -1;

    const double pixel_span = span / width;
    for (int row = 0; row < height; ++row) {
        const double imaginary = centre_imaginary + (height * 0.5 - row - 0.5) * pixel_span;
        for (int column = 0; column < width; ++column) {
            const double real = centre_real + (column + 0.5 - width * 0.5) * pixel_span;
            uint32_t colour = INTERIOR_COLOUR;
            if (!known_interior(real, imaginary)) {
                double magnitude;
                const int iteration = iterate(real, imaginary, limit, &magnitude);
                if (iteration < limit)
                    colour = escape_colour(iteration, magnitude, palette, palette_stops, phase);
            }
            pixels[(size_t)row * width + column] = colour;
        }
    }
    return 0;
}
