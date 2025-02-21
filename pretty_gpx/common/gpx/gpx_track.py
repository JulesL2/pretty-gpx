#!/usr/bin/python3
"""Gpx Track."""
from dataclasses import dataclass
from dataclasses import field

import matplotlib.pyplot as plt
import numpy as np
from gpxpy.gpx import GPXTrackPoint
from shapely.geometry import LineString
from shapely.geometry import Point as ShapelyPoint

from pretty_gpx.common.gpx.gpx_bounds import GpxBounds
from pretty_gpx.common.gpx.gpx_distance import get_distance_m
from pretty_gpx.common.gpx.gpx_distance import latlon_aspect_ratio
from pretty_gpx.common.gpx.gpx_distance import LocalProjectionXY
from pretty_gpx.common.gpx.gpx_io import load_gpxpy
from pretty_gpx.common.utils.asserts import assert_close
from pretty_gpx.common.utils.asserts import assert_same_len
from pretty_gpx.common.utils.logger import logger
from pretty_gpx.common.utils.utils import safe

DEBUG_TRACK = False


@dataclass
class GpxTrack:
    """GPX Track."""
    list_lon: list[float] = field(default_factory=list)
    list_lat: list[float] = field(default_factory=list)
    list_ele_m: list[float] = field(default_factory=list)
    list_cumul_dist_km: list[float] = field(default_factory=list)

    uphill_m: float = 0.0
    duration_s: float | None = None

    def __post_init__(self) -> None:
        assert_same_len((self.list_lon, self.list_lat, self.list_ele_m, self.list_cumul_dist_km))

    def __len__(self) -> int:
        return len(self.list_lon)

    @property
    def dist_km(self) -> float:
        """Get total distance in km."""
        return self.list_cumul_dist_km[-1]

    def get_bounds(self) -> GpxBounds:
        """Get the bounds of the track."""
        return GpxBounds.from_list(list_lon=self.list_lon,
                                   list_lat=self.list_lat)

    @staticmethod
    def load(gpx_path: str | bytes) -> 'GpxTrack':
        """Load GPX file and return GpxTrack along with total distance (in km) and d+ (in m)."""
        gpx = load_gpxpy(gpx_path)

        gpx_track = GpxTrack()
        for track in gpx.tracks:
            for segment in track.segments:
                append_track_to_gpx_track(gpx_track, segment.points)

        if len(gpx_track.list_lon) == 0:
            raise ValueError("No track found in GPX file (or elevation is missing)")

        if DEBUG_TRACK:
            plt.plot(gpx_track.list_lon, gpx_track.list_lat)
            plt.xlabel('Longitude (in °)')
            plt.ylabel('Latitude (in °)')
            plt.figure()
            plt.plot(gpx_track.list_ele_m)
            plt.ylabel('Elevation (in m)')
            plt.show()

        assert_close(gpx_track.list_cumul_dist_km[-1], gpx.length_3d()*1e-3, eps=1e-3,
                     msg="Total distance must be coherent with `gpx.length_3d()` from gpxpy")

        gpx_track.uphill_m = gpx.get_uphill_downhill().uphill

        gpx_track.duration_s = gpx.get_duration()

        logger.info(f"Loaded GPX track with {len(gpx_track.list_lon)} points: "
                    + f"Distance={gpx_track.list_cumul_dist_km[-1]:.1f}km, "
                    + f"Uphill={gpx_track.uphill_m:.0f}m "
                    + "and "
                    + ("Duration=???" if gpx_track.duration_s is None else f"Duration={gpx_track.duration_s:.0f}s"))

        return gpx_track

    def is_closed(self, ths_m: float) -> bool:
        """Estimate if the track is closed."""
        distance_m = get_distance_m(lonlat_1=(self.list_lon[0], self.list_lat[0]),
                                    lonlat_2=(self.list_lon[-1], self.list_lat[-1]))
        return distance_m < ths_m

    def plot(self, style: str = ".:") -> None:
        """Plot the track."""
        plt.plot(self.list_lon, self.list_lat, style)
        plt.xlabel('Longitude (in °)')
        plt.ylabel('Latitude (in °)')
        plt.gca().set_aspect(latlon_aspect_ratio(lat=self.list_lat[0]))

    def get_distances_m(self, *, targets_lon_lat: list[tuple[float, float]]) -> list[float]:
        """Get the distances in meters between the track and a list of lon/lat points."""
        # N.B. Since the GpxTrack might be sparse, espcially along linear segments, it's more accurate to convert it
        # to a Shapely LineString and compute the distances to the points using Shapely.
        gpx_lonlat = np.stack([self.list_lon, self.list_lat], axis=-1)
        local_xy = LocalProjectionXY.fit(lon_lat=gpx_lonlat)

        gpx_xy = local_xy.transform(lon_lat=gpx_lonlat)
        targets_xy = local_xy.transform(lon_lat=np.array(targets_lon_lat, dtype=float))

        gpx_xy_shapely = LineString(gpx_xy)

        return [ShapelyPoint(target).distance(gpx_xy_shapely) for target in targets_xy]

    def get_overpass_lonlat_str(self) -> str:
        """Get the concatenation of points in text to send it to overpass."""
        return ','.join(f"{lat:.5f},{lon:.5f}" for lat, lon in zip(self.list_lat, self.list_lon))


def append_track_to_gpx_track(gpx_track: GpxTrack, track_points: list[GPXTrackPoint]) -> None:
    """"Append track points to a GpxTrack. Update cumulative distance like in gpxpy with GPX.length_3d().

    Warning: uphill_m and duration_s are not updated in this function.

    Args:
        gpx_track: GpxTrack to update
        track_points: List of GPXTrackPoint to append (segment.points)
    """
    has_started = len(gpx_track.list_lon) > 0

    if has_started:
        prev_cumul_dist_km = gpx_track.list_cumul_dist_km[-1]
    else:
        prev_cumul_dist_km = 0.0

    prev_point: GPXTrackPoint | None = None
    for point in track_points:
        if point.elevation is None:
            if not has_started:
                continue  # Skip first point if no elevation
            point.elevation = gpx_track.list_ele_m[-1]

        gpx_track.list_lon.append(point.longitude)
        gpx_track.list_lat.append(point.latitude)
        gpx_track.list_ele_m.append(point.elevation)

        if prev_point is not None:
            prev_cumul_dist_km += safe(prev_point.distance_3d(point)) * 1e-3

        gpx_track.list_cumul_dist_km.append(prev_cumul_dist_km)

        prev_point = point
