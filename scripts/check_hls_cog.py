"""Gate 0 / T1.5b access check: windowed read of one HLS-VI band plus its Fmask, straight from COGs.

Usage:  uv run python -u scripts/check_hls_cog.py

Auth: earthaccess logs in from _netrc in memory; `get_fsspec_https_session()` gives an
authenticated fsspec HTTPS filesystem, passed to rasterio as `opener` (rasterio 1.5 docstring:
"A custom dataset opener which can serve GDAL's virtual filesystem machinery via Python file-like
objects"). No credentials, cookies or tokens are written to disk. Only the window is read.
"""

import collections

import earthaccess
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

GRANULE = "HLS-VI.S30.T14SLH.2023185T172901.v2.0"  # docs/api_notes.md (T0.2)
POINT = (-100.90, 38.00)  # Kansas census point (config/regions.yaml)
SIZE = 256  # pixels per side (7.68 km at 30 m)


class CountingOpener:
    """fsspec opener that counts bytes actually read over HTTPS."""

    def __init__(self, fs):
        self.fs, self.bytes = fs, 0

    def __call__(self, path, mode="rb"):
        f = self.fs.open(path, mode)
        outer, raw_read = self, f.read

        def read(n=-1):
            data = raw_read(n)
            outer.bytes += len(data)
            return data

        f.read = read
        return f


def read_window(url: str, opener: CountingOpener):
    with rasterio.open(url, opener=opener) as src:
        x, y = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform(*POINT)
        row, col = src.index(x, y)
        win = Window(col - SIZE // 2, row - SIZE // 2, SIZE, SIZE)
        arr = src.read(1, window=win)
        info = {
            "crs": src.crs.to_string(),
            "size": (src.width, src.height),
            "dtype": src.dtypes[0],
            "nodata": src.nodata,
            "block_shapes": src.block_shapes[0],
            "overviews": src.overviews(1),
            "scales": src.scales[0],
            "tags": {
                k: v
                for k, v in src.tags().items()
                if k.lower() in ("scale_factor", "add_offset", "long_name", "_fillvalue")
            },
        }
    return arr, info


def main() -> None:
    auth = earthaccess.login(strategy="netrc")
    print("authenticated:", bool(auth and auth.authenticated))
    g = earthaccess.search_data(short_name="HLSS30_VI", version="2.0", granule_name=GRANULE)[0]
    links = g.data_links()
    ndvi = next(u for u in links if u.endswith(".NDVI.tif"))
    fmask = next(u for u in links if u.endswith(".Fmask.tif"))
    opener = CountingOpener(earthaccess.get_fsspec_https_session())

    a, info = read_window(ndvi, opener)
    valid = a[a != info["nodata"]] if info["nodata"] is not None else a.ravel()
    print("\n== NDVI", ndvi.rsplit("/", 1)[-1])
    print("  ", info)
    med = np.median(valid) if valid.size else None
    print(f"   window {a.shape}, valid {valid.size}, raw median {med}")
    print(f"   bytes read so far: {opener.bytes / 1e6:.2f} MB")

    m, minfo = read_window(fmask, opener)
    print("\n== Fmask", fmask.rsplit("/", 1)[-1])
    print("  ", minfo)
    print("   value counts:", dict(collections.Counter(m.ravel().tolist()).most_common(8)))
    print(f"   total bytes read: {opener.bytes / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
