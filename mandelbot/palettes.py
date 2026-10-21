"""Original cyclic colour stops shared by the GPU and CPU reference renderers."""

from types import MappingProxyType

PALETTE_STOP_COUNT = 6
RGB_CHANNEL_COUNT = 3
MAX_CHANNEL_VALUE = 255

# Ordered dark-to-light arcs return through a complementary shadow colour.
# Keep the original names and values stable for existing saved preferences.
PALETTE_COLOURS = MappingProxyType({
    "Aurora": ((8, 18, 42), (24, 72, 112), (43, 198, 179),
               (216, 244, 213), (137, 104, 196), (33, 28, 82)),
    "Ember": ((25, 9, 30), (103, 24, 68), (223, 72, 55),
              (255, 181, 80), (255, 240, 192), (101, 37, 66)),
    "Ocean": ((3, 16, 40), (10, 59, 112), (21, 132, 182),
              (116, 221, 229), (225, 249, 251), (66, 111, 171)),
    "Forest": ((5, 22, 19), (13, 69, 46), (48, 136, 69),
               (166, 208, 101), (238, 241, 189), (54, 100, 73)),
    "Violet": ((17, 8, 40), (58, 24, 105), (126, 56, 180),
               (204, 139, 236), (246, 227, 255), (87, 58, 151)),
    "Sunset": ((25, 13, 62), (94, 31, 117), (209, 57, 105),
               (255, 131, 85), (255, 223, 157), (142, 64, 117)),
    "Ice": ((8, 20, 34), (34, 73, 99), (99, 155, 177),
            (183, 225, 233), (244, 253, 255), (89, 117, 154)),
    "Rose": ((35, 8, 26), (108, 31, 65), (199, 83, 120),
             (245, 163, 179), (255, 235, 226), (137, 76, 104)),
    "Copper": ((25, 15, 12), (83, 43, 27), (165, 90, 45),
               (221, 158, 100), (255, 232, 182), (101, 65, 46)),
    "Neon": ((12, 5, 37), (76, 16, 150), (241, 37, 181),
             (75, 230, 246), (206, 255, 122), (24, 102, 129)),
    "Sandstone": ((31, 24, 35), (94, 63, 65), (173, 121, 88),
                  (223, 184, 130), (250, 239, 207), (119, 104, 113)),
    "Monochrome": ((9, 9, 9), (45, 45, 45), (109, 109, 109),
                   (192, 192, 192), (249, 249, 249), (93, 93, 93)),
})

PALETTES = tuple(PALETTE_COLOURS)


def palette_channels(name):
    """Return packed RGB stops, keeping colour data out of native source code."""
    return tuple(channel for stop in PALETTE_COLOURS[name] for channel in stop)
