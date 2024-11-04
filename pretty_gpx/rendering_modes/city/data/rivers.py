#!/usr/bin/python3
"""Rivers."""
import os

import numpy as np

from pretty_gpx.common.data.overpass_processing import create_patch_collection_from_polygons
from pretty_gpx.common.data.overpass_processing import get_polygons_from_closed_ways
from pretty_gpx.common.data.overpass_processing import get_polygons_from_relations
from pretty_gpx.common.data.overpass_processing import get_rivers_polygons_from_lines
from pretty_gpx.common.data.overpass_processing import PolygonAlpha
from pretty_gpx.common.data.overpass_request import OverpassQuery
from pretty_gpx.common.gpx.gpx_bounds import GpxBounds
from pretty_gpx.common.gpx.gpx_data_cache_handler import GpxDataCacheHandler
from pretty_gpx.common.utils.logger import logger
from pretty_gpx.common.utils.pickle_io import read_pickle
from pretty_gpx.common.utils.pickle_io import write_pickle
from pretty_gpx.common.utils.profile import profile
from pretty_gpx.common.utils.profile import Profiling
from pretty_gpx.common.utils.utils import EARTH_RADIUS_M

RIVERS_CACHE = GpxDataCacheHandler(name='rivers', extension='.pkl')

RIVERS_WAYS_ARRAY_NAME = "rivers_ways"
RIVERS_RELATIONS_ARRAY_NAME = "rivers_relations"
RIVERS_LINE_WAYS_ARRAY_NAME = "rivers_line_ways"
STREAMS_LINE_WAYS_ARRAY_NAME = "stream_line_ways"

RIVER_LINE_WIDTH_M = 15
RIVER_LINE_WIDTH = np.rad2deg(RIVER_LINE_WIDTH_M/EARTH_RADIUS_M)

@profile
def prepare_download_city_rivers(query: OverpassQuery,
                                 bounds: GpxBounds) -> None:
    """Add the queries for city rivers inside the global OverpassQuery."""
    cache_pkl = RIVERS_CACHE.get_path(bounds)

    if os.path.isfile(cache_pkl):
        query.add_cached_result(RIVERS_CACHE.name, cache_file=cache_pkl)
    else:
        caracteristic_length = bounds.diagonal_m
        min_len = caracteristic_length*0.01
        natural_water_l = ["reservoir","canal","stream_pool","lagoon","oxbow","river","lake","pond"]
        join_character = '|'
        query.add_overpass_query(array_name=RIVERS_RELATIONS_ARRAY_NAME,
                                 query_elements = [ 'relation["natural"="water"]'
                                                   f'["water"~"({join_character.join(natural_water_l)})"]',
                                                    'relation["natural"="wetland"]["wetland" = "tidal"]',
                                                    'relation["natural"="bay"]'],
                                 bounds=bounds,
                                 include_way_nodes=True,
                                 include_relation_members_nodes=True,
                                 return_geometry=True) 
        query.add_overpass_query(array_name=RIVERS_WAYS_ARRAY_NAME,
                                 query_elements=['way["natural"="water"]["water"~'
                                                 f'"({join_character.join(natural_water_l)})"]',
                                                 f'way["natural"="water"][!"water"](if: length() > {min_len})',
                                                  'way["natural"="wetland"]["wetland" = "tidal"]',
                                                  'way["natural"="bay"]'],
                                 bounds=bounds,
                                 include_way_nodes=True,
                                 return_geometry=True)
        query.add_overpass_query(array_name=RIVERS_LINE_WAYS_ARRAY_NAME,
                                 query_elements=['way["waterway"~"(river|canal)"]'
                                                 '["tunnel"!~".*"]'],
                                 bounds=bounds,
                                 include_way_nodes=True,
                                 return_geometry=False) 
        if get_stream_visualization(caracteristic_length)[0] > 0:
            query.add_overpass_query(array_name=STREAMS_LINE_WAYS_ARRAY_NAME,
                                    query_elements=['way["waterway"~"(stream)"]'
                                                    '["tunnel"!~".*"]'],
                                    bounds=bounds,
                                    include_way_nodes=True,
                                    return_geometry=False)

def get_stream_visualization(domain_diagonal: float) -> tuple[float, float]:
    """Returns stream visualization characteristics based on map zoom level.
    - For domain_diagonal > 10000m: No streams (width=0, alpha=0)
    - For domain_diagonal between 10000m and 2000m: Gradual appearance
    - For domain_diagonal < 2000m: Full visibility (max width and opacity)
    """
    # Constants for transition
    MAX_DISTANCE = 10000  # meters - no streams above this
    MIN_DISTANCE = 2000   # meters - full visibility below this
    MAX_WIDTH_M = 4      # maximum width in meters
    MIN_WIDTH_M = 2      # minimum width in meters when streams start appearing

    if domain_diagonal >= MAX_DISTANCE:
        return 0,0

    if domain_diagonal <= MIN_DISTANCE:
        width_deg = np.rad2deg(MAX_WIDTH_M/EARTH_RADIUS_M)
        return width_deg, 1.0

    # Calculate transition factor (0 to 1)
    factor = np.power((MAX_DISTANCE - domain_diagonal) / (MAX_DISTANCE - MIN_DISTANCE), 2)

    width_m = MIN_WIDTH_M + (MAX_WIDTH_M - MIN_WIDTH_M) * factor
    width_deg = np.rad2deg(width_m/EARTH_RADIUS_M)

    alpha = factor

    return width_deg, alpha

@profile
def process_city_rivers(query: OverpassQuery,
                        bounds: GpxBounds) -> list[PolygonAlpha]:
    """Process the overpass API result to get the rivers of a city."""
    if query.is_cached(RIVERS_CACHE.name):
        cache_file = query.get_cache_file(RIVERS_CACHE.name)
        rivers_result = read_pickle(cache_file)
    else:
        with Profiling.Scope("Process Rivers"):
            caracteristic_length = bounds.diagonal_m
            rivers_relation_results = query.get_query_result(RIVERS_RELATIONS_ARRAY_NAME)
            rivers_way_results = query.get_query_result(RIVERS_WAYS_ARRAY_NAME)
            rivers_line_results = query.get_query_result(RIVERS_LINE_WAYS_ARRAY_NAME)
            rivers_relations = get_polygons_from_relations(results=rivers_relation_results)
            rivers_ways = get_polygons_from_closed_ways(rivers_way_results.ways)
            rivers = rivers_relations + rivers_ways
            rivers_lines_polygons = get_rivers_polygons_from_lines(api_result=rivers_line_results,
                                                                   width=RIVER_LINE_WIDTH)
            rivers = rivers_lines_polygons + rivers
            rivers_patches = create_patch_collection_from_polygons(rivers)
            rivers_result: list[PolygonAlpha] = [PolygonAlpha(polygons=rivers_patches,
                                                                          alpha=1.0)]
            stream_linewidth, stream_alpha = get_stream_visualization(caracteristic_length)
            if stream_linewidth > 0:
                stream_line_results = query.get_query_result(STREAMS_LINE_WAYS_ARRAY_NAME)
                stream_line_polygons = get_rivers_polygons_from_lines(api_result=stream_line_results,
                                                                      width=stream_linewidth)
                streams_patches = create_patch_collection_from_polygons(stream_line_polygons)
                rivers_result.append(PolygonAlpha(polygons=streams_patches,
                                                        alpha=stream_alpha))
            logger.info(f"Found {len(rivers_relations)} polygons for rivers "
                        f"with relations and {len(rivers_ways)} with ways and"
                        f" {len(rivers_lines_polygons)} created with river main line")
        cache_pkl = RIVERS_CACHE.get_path(bounds)
        write_pickle(cache_pkl, rivers_result)
        query.add_cached_result(RIVERS_CACHE.name, cache_file=cache_pkl)
    return rivers_result