#!/usr/bin/python3
"""City Points of Interest."""
import os
import re
from dataclasses import dataclass
from dataclasses import field

import matplotlib.pyplot as plt
import numpy as np

from pretty_gpx.common.drawing.utils.scatter_point import ScatterPoint
from pretty_gpx.common.drawing.utils.scatter_point import ScatterPointCategory
from pretty_gpx.common.gpx.gpx_bounds import GpxBounds
from pretty_gpx.common.gpx.gpx_distance import get_pairwise_distance_m
from pretty_gpx.common.gpx.gpx_distance import ListLonLat
from pretty_gpx.common.gpx.gpx_track import GpxTrack
from pretty_gpx.common.request.gpx_data_cache_handler import GpxDataCacheHandler
from pretty_gpx.common.request.osm_name import get_shortest_name
from pretty_gpx.common.request.overpass_processing import get_polygons_from_relation
from pretty_gpx.common.request.overpass_processing import get_way_coordinates
from pretty_gpx.common.request.overpass_request import OverpassQuery
from pretty_gpx.common.utils.pickle_io import read_pickle
from pretty_gpx.common.utils.pickle_io import write_pickle
from pretty_gpx.common.utils.profile import profile
from pretty_gpx.common.utils.profile import Profiling
from pretty_gpx.common.utils.utils import safe

CITY_POINTS_OF_INTEREST_CACHE = GpxDataCacheHandler(name='city_pois', extension='.pkl')

CITY_POINTS_OF_INTEREST_WAYS_ARRAY_NAME = "city_pois_ways"
CITY_POINTS_OF_INTEREST_RELATIONS_ARRAY_NAME = "city_pois_relations"


@dataclass
class CandidateCityPoi:
    """Candidate City Point of Interest Data."""
    category: ScatterPointCategory
    name: str
    importance: int
    poly_lonlat: ListLonLat
    center_lonlat: tuple[float, float] = field(init=False)  # Prevent initialization

    def __post_init__(self) -> None:
        avg = np.mean(self.poly_lonlat, axis=0)
        self.center_lonlat = (float(avg[0]), float(avg[1]))


@profile
def prepare_download_city_pois(query: OverpassQuery, gpx_track: GpxTrack) -> None:
    """Add the queries for city pois inside the global OverpassQuery."""
    cache_pkl = CITY_POINTS_OF_INTEREST_CACHE.get_path(gpx_track)

    if os.path.isfile(cache_pkl):
        query.add_cached_result(CITY_POINTS_OF_INTEREST_CACHE.name, cache_file=cache_pkl)
        return

    for element_type, array_name in [("way", CITY_POINTS_OF_INTEREST_WAYS_ARRAY_NAME),
                                     ("relation", CITY_POINTS_OF_INTEREST_RELATIONS_ARRAY_NAME)]:
        query.add_overpass_query(
            array_name=array_name,
            query_elements=[
                f'{element_type}["wikipedia"]["name"]["man_made"!="bridge"][!"bridge"]["tourism"~"attraction|museum"]',
            ],
            include_tags=True,
            include_way_nodes=True,
            include_relation_members_nodes=True,
            return_geometry=True,
            bounds=gpx_track.get_bounds(),
            add_relative_margin=0.05)


@profile
def process_city_pois(query: OverpassQuery, gpx_track: GpxTrack) -> list[ScatterPoint]:
    """Process the overpass API result to get the Points of Interest of a city."""
    if query.is_cached(CITY_POINTS_OF_INTEREST_CACHE.name):
        cache_file = query.get_cache_file(CITY_POINTS_OF_INTEREST_CACHE.name)
        return read_pickle(cache_file)

    with Profiling.Scope("Process Points of Interest"):
        res_ways = query.get_query_result(CITY_POINTS_OF_INTEREST_WAYS_ARRAY_NAME)

        # Get Candidate City Pois
        candidates: list[CandidateCityPoi] = []

        for way in res_ways.ways:
            importance = __get_importance_score(way.tags)
            if importance is not None:
                lon_lat = get_way_coordinates(way)
                if len(lon_lat) > 0:
                    candidates.append(CandidateCityPoi(category=ScatterPointCategory.CITY_POI_DEFAULT,
                                                       name=safe(get_shortest_name(way)),
                                                       importance=importance,
                                                       poly_lonlat=lon_lat))

        res_relations = query.get_query_result(CITY_POINTS_OF_INTEREST_RELATIONS_ARRAY_NAME)
        for rel in res_relations.relations:
            importance = __get_importance_score(rel.tags)
            if importance is not None:
                lon_lat = [(lon, lat)
                           for poly in get_polygons_from_relation(rel)
                           for lon, lat in zip(*poly.exterior.xy)]
                if len(lon_lat) > 0:
                    candidates.append(CandidateCityPoi(category=ScatterPointCategory.CITY_POI_DEFAULT,
                                                       name=safe(get_shortest_name(rel)),
                                                       importance=importance,
                                                       poly_lonlat=lon_lat))

        # Keep only the ones close to the GPX track
        candidates = __filter_close_gpx(candidates, gpx_track)

        # Apply Non-Maximum Suppression
        candidates = __nms_city_pois(candidates, gpx_track.get_bounds())

        # Take the n best
        candidates = __take_n_best(candidates, 6)

        # Convert to ScatterPoint
        city_pois = [ScatterPoint(name=city_poi.name,
                                  lat=city_poi.center_lonlat[1],
                                  lon=city_poi.center_lonlat[0],
                                  category=city_poi.category)
                     for city_poi in candidates]

    cache_pkl = CITY_POINTS_OF_INTEREST_CACHE.get_path(gpx_track)
    write_pickle(cache_pkl, city_pois)
    query.add_cached_result(CITY_POINTS_OF_INTEREST_CACHE.name, cache_file=cache_pkl)
    return city_pois


IMPORTANCE_BASIC_TAG_PATTERN = re.compile(
    r"^(" + "|".join([
        "heritage",
        "source",
        "contact",
        "architect",
        "opening_hours",
        "historic",
        "phone",
        "email",
        "website",
        "importance",
        "image",
        "wikimedia_commons"
    ]) + r")"
)


IMPORTANCE_NAME_TAG_PATTERN = re.compile(
    r"^(" + "|".join([
        "name:",
        "alt_name",
        "short_name",
    ]) + r")"
)


def __get_importance_score(tags: dict[str, str]) -> int | None:
    """Returns an importance score based on specific tags and their occurrences."""
    # Count occurrences of relevant tags
    count = 0
    for key in tags:
        if IMPORTANCE_BASIC_TAG_PATTERN.match(key):
            count += 1
        elif IMPORTANCE_NAME_TAG_PATTERN.match(key):
            count += 2

    if tags.get("building") == "cathedral":
        count += 5
    elif tags.get("amenity") == "theatre":
        count += 5
    elif tags.get("building") == "palace":
        count += 10
    elif tags.get("building") == "castle":
        count += 3

    return count if count >= 5 else None


def __filter_close_gpx(city_pois: list[CandidateCityPoi], gpx: GpxTrack) -> list[CandidateCityPoi]:
    """Filter the city pois that are close to the gpx track."""
    filtered_city_pois: list[CandidateCityPoi] = []

    for city_poi in city_pois:
        min_distance = np.min(gpx.get_distances_m(targets_lon_lat=city_poi.poly_lonlat))

        if city_poi.importance > 70:
            ths_m = 800
        elif city_poi.importance > 30:
            ths_m = 500
        else:
            ths_m = 150

        if min_distance < ths_m:
            filtered_city_pois.append(city_poi)

    return filtered_city_pois


def __nms_city_pois(city_pois: list[CandidateCityPoi], bounds: GpxBounds) -> list[CandidateCityPoi]:
    """Apply a Non-Maximum Suppression on the city pois."""
    if len(city_pois) == 0:
        return []

    ths = 0.02 * bounds.diagonal_m

    city_pois = sorted(city_pois, key=lambda x: x.importance, reverse=True)

    dist_matrix = get_pairwise_distance_m(lonlat_1=np.array([poi.center_lonlat for poi in city_pois]))
    keep = np.zeros(len(city_pois), dtype=bool)
    for i in range(len(city_pois)):
        if i != 0 and np.min(dist_matrix[i][keep]) < ths:
            continue

        keep[i] = True

    return [city_poi for city_poi, keep_it in zip(city_pois, keep) if keep_it]


def __take_n_best(city_pois: list[CandidateCityPoi], n: int) -> list[CandidateCityPoi]:
    """Take the n best city pois."""
    city_pois = sorted(city_pois, key=lambda x: x.importance, reverse=True)
    return city_pois[:n]


def __debug(city_pois: list[CandidateCityPoi] | list[ScatterPoint], gpx: GpxTrack) -> None:
    plt.figure()
    gpx.plot()

    for city_poi in city_pois:
        if isinstance(city_poi, ScatterPoint):
            plt.plot(city_poi.lon, city_poi.lat, 'o')
            plt.text(city_poi.lon, city_poi.lat, safe(city_poi.name))
        else:
            plt.plot(*zip(*city_poi.poly_lonlat), '.')
            plt.plot(*city_poi.center_lonlat, 'ok')
            plt.text(*city_poi.center_lonlat, f"{city_poi.name} ({city_poi.importance})")
