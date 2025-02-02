#!/usr/bin/python3
"""Roads."""
import os
from enum import auto
from enum import Enum
from dataclasses import dataclass

from tqdm import tqdm

from pretty_gpx.common.gpx.gpx_bounds import GpxBounds
from pretty_gpx.common.gpx.gpx_distance import ListLonLat
from pretty_gpx.common.request.gpx_data_cache_handler import GpxDataCacheHandler
from pretty_gpx.common.request.overpass_processing import get_ways_coordinates_from_results
from pretty_gpx.common.request.overpass_request import OverpassQuery
from pretty_gpx.common.utils.logger import logger
from pretty_gpx.common.utils.pickle_io import read_pickle
from pretty_gpx.common.utils.pickle_io import write_pickle
from pretty_gpx.common.utils.profile import profile
from pretty_gpx.common.utils.profile import Profiling

ROADS_CACHE = GpxDataCacheHandler(name='roads', extension='.pkl')


class CityRoadType(Enum):
    """City Road Type."""
    HIGHWAY = auto()
    SECONDARY_ROAD = auto()
    STREET = auto()
    ACCESS_ROAD = auto()



ROAD_PRECISION_LEVEL = {
    "Low":0,
    "Medium":1,
    "High":2,
    "Very High": 3
}

@dataclass(frozen=True)
class RoadTypeData:
    """Data for each type of city road."""
    tags: list[str]
    priority: int
    query_name: str

# Dictionary of RoadTypeData for each CityRoadType, ordered by priority
ROAD_TYPE_DATA: dict[CityRoadType, RoadTypeData] = {
    CityRoadType.HIGHWAY: RoadTypeData(tags=["motorway", "trunk", "primary"], priority=0, query_name="highway"),
    CityRoadType.SECONDARY_ROAD: RoadTypeData(tags=["tertiary", "secondary"], priority=1, query_name="secondary_roads"),
    CityRoadType.STREET: RoadTypeData(tags=["residential", "living_street"], priority=2, query_name="street"),
    CityRoadType.ACCESS_ROAD: RoadTypeData(tags=["unclassified", "service"], priority=3, query_name="access_roads")
}

# Automatically check that ROAD_TYPE_DATA is sorted by priority
assert list(ROAD_TYPE_DATA.keys()) == sorted(ROAD_TYPE_DATA.keys(),
                                             key=lambda road_type: ROAD_TYPE_DATA[road_type].priority)


def get_city_roads_with_priority_better_than(x: int) -> list[CityRoadType]:
    """Returns a list of CityRoadType with a priority better than the given x."""
    # Filter ROAD_TYPE_DATA to get only those with priority less than x
    return [road_type for road_type, data in ROAD_TYPE_DATA.items() if data.priority <= x]


@profile
def prepare_download_city_roads(query: OverpassQuery,
                                bounds: GpxBounds,
                                road_precision: str) -> list[CityRoadType]:
    """Download roads map from OpenStreetMap.

    Args:
        query: OverpassQuery class that merge all queries into a single one
        bounds: GPX bounds

    Returns:
        List of roads (sequence of lon, lat coordinates) for each road type
    """
    cache_pkl = ROADS_CACHE.get_path(bounds)

    assert road_precision in ROAD_PRECISION_LEVEL.keys()

    logger.info(f"Road precision : {road_precision}")
    roads_to_plot: list[CityRoadType] = get_city_roads_with_priority_better_than(ROAD_PRECISION_LEVEL[road_precision])
    logger.info(f"Length of the roads : {len(roads_to_plot)}")

    if os.path.isfile(cache_pkl):
        cityroads_cache: dict[CityRoadType, list[ListLonLat]] = read_pickle(file_path=cache_pkl)
        roads_types_cache = list(cityroads_cache.keys())
        query.add_cached_result(ROADS_CACHE.name, cache_file=cache_pkl)

        if all(key in roads_types_cache for key in roads_to_plot):
            logger.debug("Roads needed already downloaded")
            roads_to_plot = []
        else:
            logger.debug("Downloading additionnal roads")
            roads_to_plot = [key for key in roads_to_plot if key not in roads_types_cache]

    if len(roads_to_plot) > 0:
        for city_road_type in tqdm(roads_to_plot):
            highway_tags_str = "|".join(ROAD_TYPE_DATA[city_road_type].tags)
            query_name = ROAD_TYPE_DATA[city_road_type].query_name
            query.add_overpass_query(query_name,
                                     [f"way['highway'~'({highway_tags_str})']"],
                                     bounds,
                                     include_way_nodes=True,
                                     add_relative_margin=None)
    return roads_to_plot


@profile
def process_city_roads(query: OverpassQuery,
                       bounds: GpxBounds,
                       city_roads_downloaded: list[CityRoadType],
                       road_precision: str) -> dict[CityRoadType,list[ListLonLat]]:
    """Query the overpass API to get the roads of a city."""
    roads_to_plot: list[CityRoadType] = get_city_roads_with_priority_better_than(ROAD_PRECISION_LEVEL[road_precision])

    if len(city_roads_downloaded) > 0:
        # We need to process some downloaded road types.
        if query.is_cached(ROADS_CACHE.name):
            cache_file = query.get_cache_file(ROADS_CACHE.name)
            roads = read_pickle(cache_file)
        else:
            roads = dict()
        with Profiling.Scope("Process City Roads"):
            for city_road_type in city_roads_downloaded:
                query_name = ROAD_TYPE_DATA[city_road_type].query_name
                result = query.get_query_result(query_name)
                roads[city_road_type] = get_ways_coordinates_from_results(result)
        cache_pkl = ROADS_CACHE.get_path(bounds)
        write_pickle(cache_pkl, roads)
        query.add_cached_result(ROADS_CACHE.name, cache_file=cache_pkl)
        roads_to_return = {road_type: roads[road_type] for road_type in roads_to_plot}
        return roads_to_return

    elif query.is_cached(ROADS_CACHE.name):
        cache_file = query.get_cache_file(ROADS_CACHE.name)
        roads = read_pickle(cache_file)
        roads_to_return = {road_type: roads[road_type] for road_type in roads_to_plot}
        return roads_to_return

    else:
        raise FileNotFoundError("Query is supposed to be cached but it is not.")
