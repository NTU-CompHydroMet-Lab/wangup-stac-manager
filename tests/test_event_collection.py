"""Unit tests for event aggregation helpers (no I/O required)."""

from datetime import datetime, timezone
from pathlib import Path

import pystac
import pytest

from src.core.event_collection import (
    asset_ext,
    bbox_to_polygon,
    parse_iso_datetime,
    product_alias,
    resolve_href,
    select_event_assets,
    to_iso_utc_z,
    union_extent,
)


def _make_collection(bbox, temporal_start, temporal_end, col_id="test"):
    return pystac.Collection(
        id=col_id,
        description="test",
        extent=pystac.Extent(
            pystac.SpatialExtent([bbox]),
            pystac.TemporalExtent([[temporal_start, temporal_end]]),
        ),
    )


class TestUnionExtent:
    def test_single_collection(self):
        col = _make_collection(
            [120.0, 24.0, 122.0, 26.0],
            datetime(2021, 6, 4, tzinfo=timezone.utc),
            datetime(2021, 6, 5, tzinfo=timezone.utc),
        )
        ext = union_extent([col])
        assert ext.spatial.bboxes == [[120.0, 24.0, 122.0, 26.0]]
        assert ext.temporal.intervals[0][0] == datetime(2021, 6, 4, tzinfo=timezone.utc)

    def test_two_collections_union(self):
        c1 = _make_collection(
            [120.0, 24.0, 122.0, 26.0],
            datetime(2021, 6, 4, tzinfo=timezone.utc),
            datetime(2021, 6, 5, tzinfo=timezone.utc),
        )
        c2 = _make_collection(
            [119.0, 23.0, 121.0, 25.0],
            datetime(2021, 6, 3, tzinfo=timezone.utc),
            datetime(2021, 6, 6, tzinfo=timezone.utc),
        )
        ext = union_extent([c1, c2])
        assert ext.spatial.bboxes == [[119.0, 23.0, 122.0, 26.0]]
        assert ext.temporal.intervals[0][0] == datetime(2021, 6, 3, tzinfo=timezone.utc)
        assert ext.temporal.intervals[0][1] == datetime(2021, 6, 6, tzinfo=timezone.utc)

    def test_global_bbox_ignored(self):
        c1 = _make_collection(
            [-180.0, -90.0, 180.0, 90.0],
            datetime(2021, 1, 1, tzinfo=timezone.utc),
            datetime(2021, 12, 31, tzinfo=timezone.utc),
        )
        c2 = _make_collection(
            [120.0, 24.0, 122.0, 26.0],
            datetime(2021, 6, 4, tzinfo=timezone.utc),
            datetime(2021, 6, 5, tzinfo=timezone.utc),
        )
        ext = union_extent([c1, c2])
        assert ext.spatial.bboxes == [[120.0, 24.0, 122.0, 26.0]]

    def test_all_global_falls_back(self):
        c1 = _make_collection(
            [-180.0, -90.0, 180.0, 90.0],
            datetime(2021, 1, 1, tzinfo=timezone.utc),
            datetime(2021, 12, 31, tzinfo=timezone.utc),
        )
        ext = union_extent([c1])
        assert ext.spatial.bboxes == [[-180.0, -90.0, 180.0, 90.0]]


class TestProductAlias:
    def test_rainfall(self):
        assert product_alias("flood_event_20210604_rainfall_wgs84") == "rain_forcing"

    def test_max_depth(self):
        assert product_alias("flood_event_20210604_max_depth_faces") == "max_depth"

    def test_iot(self):
        assert product_alias("flood_event_20210604_iot_validation_parquet") == "iot_timeseries"

    def test_unknown_returns_id(self):
        assert product_alias("some_random_collection") == "some_random_collection"


class TestSelectEventAssets:
    def test_iot_prefers_parquet(self):
        assets = {
            "data": {"href": "./data.nc"},
            "iot_validation_parquet": {"href": "./iot.parquet"},
        }
        result = select_event_assets("iot_timeseries", assets)
        assert len(result) == 1
        assert result[0][0] == "data"
        assert result[0][1]["href"] == "./iot.parquet"

    def test_non_iot_returns_all(self):
        assets = {
            "data": {"href": "./a.nc"},
            "thumb": {"href": "./t.png"},
        }
        result = select_event_assets("rain_forcing", assets)
        assert len(result) == 2


class TestDatetimeHelpers:
    def test_parse_z_suffix(self):
        dt = parse_iso_datetime("2021-06-04T00:00:00Z")
        assert dt == datetime(2021, 6, 4, tzinfo=timezone.utc)

    def test_parse_none(self):
        assert parse_iso_datetime(None) is None

    def test_parse_empty(self):
        assert parse_iso_datetime("") is None

    def test_to_iso_utc_z(self):
        dt = datetime(2021, 6, 4, 12, 30, 0, tzinfo=timezone.utc)
        assert to_iso_utc_z(dt) == "2021-06-04T12:30:00Z"

    def test_to_iso_utc_z_none(self):
        assert to_iso_utc_z(None) is None


class TestBboxToPolygon:
    def test_basic(self):
        poly = bbox_to_polygon([120.0, 24.0, 122.0, 26.0])
        assert poly["type"] == "Polygon"
        coords = poly["coordinates"][0]
        assert len(coords) == 5
        assert coords[0] == coords[-1]


class TestResolveHref:
    def test_absolute_returned_as_is(self):
        assert resolve_href(Path("/a/b/c.json"), "/x/y/z.json") == Path("/x/y/z.json")

    def test_relative_resolved(self, tmp_path):
        base = tmp_path / "catalog" / "collection.json"
        base.parent.mkdir(parents=True)
        base.touch()
        result = resolve_href(base, "./items/item.json")
        assert result == (tmp_path / "catalog" / "items" / "item.json").resolve()


class TestAssetExt:
    def test_zarr(self):
        assert asset_ext(Path("data/foo.zarr")) == ".zarr"

    def test_nc(self):
        assert asset_ext(Path("data/foo.nc")) == ".nc"

    def test_parquet(self):
        assert asset_ext(Path("data/foo.parquet")) == ".parquet"

    def test_no_suffix(self):
        assert asset_ext(Path("data/foo")) == ""
