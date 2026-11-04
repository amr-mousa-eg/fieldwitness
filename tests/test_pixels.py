from shapely.geometry import box

from fieldwitness.resolve.pixels import interior_pixel_counts

ULX, ULY = 300000.0, 4300020.0  # T14SLH origin (CMR metadata)


def square(x0, y0, size):
    """Square whose lower-left corner is offset (x0, y0) metres from the tile's upper-left."""
    return box(ULX + x0, ULY - y0 - size, ULX + x0 + size, ULY - y0)


def test_known_square_counts():
    # 300 m square offset 5 m from the grid: pixel centres at 15, 45, ..., 285 m from its corner
    # side fall inside -> 10 x 10 = 100 with no buffer.
    sq = [square(5, 5, 300)]
    assert interior_pixel_counts(sq, ULX, ULY, buffer_m=0)[0] == 100
    # 15 m inward buffer -> interior spans 20..290 m: centres 45..285 -> 9 x 9 = 81.
    assert interior_pixel_counts(sq, ULX, ULY, buffer_m=15)[0] == 81
    # 30 m inward buffer -> interior spans 35..275 m: centres 45..255 -> 8 x 8 = 64.
    assert interior_pixel_counts(sq, ULX, ULY, buffer_m=30)[0] == 64


def test_small_field_has_no_interior_pixels():
    assert interior_pixel_counts([square(5, 5, 50)], ULX, ULY, buffer_m=30)[0] == 0


def test_counts_never_exceed_unbuffered():
    geoms = [square(5, 5, 300), square(100, 700, 125), square(13, 1000, 61)]
    full = interior_pixel_counts(geoms, ULX, ULY, buffer_m=0)
    for b in (15, 30):
        assert (interior_pixel_counts(geoms, ULX, ULY, buffer_m=b) <= full).all()
