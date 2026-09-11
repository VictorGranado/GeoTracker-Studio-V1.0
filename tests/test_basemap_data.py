import math

from geotracker_studio.basemap_data import (
    OPENSTREETMAP,
    choose_tile_plan,
    global_pixel_to_latlon,
    latlon_to_global_pixel,
    tile_plan_latlon_bounds,
    tile_url,
)


def test_web_mercator_pixel_roundtrip():
    lat, lon = 43.8231, -111.7924
    x, y = latlon_to_global_pixel(lat, lon, 17)
    lat2, lon2 = global_pixel_to_latlon(x, y, 17)
    assert abs(lat2 - lat) < 1e-9
    assert abs(lon2 - lon) < 1e-9


def test_tile_plan_is_bounded_and_covers_demo_route():
    lat_min, lon_min = 43.8230, -111.7925
    lat_max, lon_max = 43.8251, -111.7908
    plan = choose_tile_plan(
        lat_min, lon_min, lat_max, lon_max,
        provider=OPENSTREETMAP,
        preferred_zoom=17,
        max_tiles=16,
    )
    assert plan.tile_count <= 16
    assert plan.zoom <= 17
    p_lat_min, p_lon_min, p_lat_max, p_lon_max = tile_plan_latlon_bounds(plan)
    assert p_lat_min <= lat_min <= p_lat_max
    assert p_lat_min <= lat_max <= p_lat_max
    assert p_lon_min <= lon_min <= p_lon_max
    assert p_lon_min <= lon_max <= p_lon_max


def test_large_route_automatically_uses_lower_zoom():
    small = choose_tile_plan(43.82, -111.80, 43.83, -111.79, preferred_zoom=17, max_tiles=16)
    large = choose_tile_plan(43.0, -112.5, 44.0, -111.0, preferred_zoom=17, max_tiles=16)
    assert large.zoom < small.zoom
    assert large.tile_count <= 16


def test_osm_tile_url_is_https_and_xyz():
    url = tile_url(OPENSTREETMAP, 17, 24835, 47311)
    assert url == "https://tile.openstreetmap.org/17/24835/47311.png"
