#!/usr/bin/python3
"""City Drawing Style/Size Config."""
import os
from dataclasses import dataclass

import numpy as np
from matplotlib.path import Path

from pretty_gpx.common.drawing.plt_marker import marker_from_svg
from pretty_gpx.common.layout.paper_size import PAPER_SIZES
from pretty_gpx.common.layout.paper_size import PaperSize
from pretty_gpx.common.utils.paths import ICONS_DIR
from pretty_gpx.common.utils.utils import mm_to_point
from pretty_gpx.rendering_modes.city.data.roads import CityRoadType

# Diagonal of the case used to set the reference value
REF_DIAGONAL_DISTANCE_M: float = 39298
REF_PAPER_SIZE: PaperSize = PAPER_SIZES["A4"]


@dataclass(kw_only=True)
class CityDrawingStyleConfig:
    """City Drawing Style Config."""
    start_marker: str | Path = "o"
    end_marker: str | Path = "s"
    bridge_marker: str | Path = marker_from_svg(os.path.join(ICONS_DIR, "bridge.svg"))


@dataclass(kw_only=True)
class CityDrawingSizeConfig:
    """City Drawing Size Config."""
    paper_size: PaperSize

    caracteristic_distance: float

    linewidth_priority: dict[CityRoadType, float]
    linewidth_track: float

    bridge_markersize: float

    text_fontsize: float
    text_arrow_linewidth: float

    @staticmethod
    def default(paper_size: PaperSize, diagonal_distance_m: float) -> 'CityDrawingSizeConfig':
        """Default City Drawing Size Config."""
        # Convert default A4 parameters to paper size
        ref_diag_mm = np.linalg.norm([REF_PAPER_SIZE.w_mm, REF_PAPER_SIZE.h_mm])
        new_diag_mm = np.linalg.norm([paper_size.w_mm, paper_size.h_mm])
        scale_paper = float(new_diag_mm/ref_diag_mm)
        scale_bounds = float(REF_DIAGONAL_DISTANCE_M/diagonal_distance_m)
        scale = scale_paper*scale_bounds

        linewidth_priority = {
            CityRoadType.HIGHWAY: 1.0*scale,
            CityRoadType.SECONDARY_ROAD: 0.5*scale,
            CityRoadType.STREET: 0.25*scale,
            CityRoadType.ACCESS_ROAD: 0.1*scale
        }

        bridge_markersize = mm_to_point(7.0) * scale

        # Set a maximum track linewidth to avoid masking data
        max_track_linewidth = (linewidth_priority[CityRoadType.SECONDARY_ROAD] +
                               linewidth_priority[CityRoadType.SECONDARY_ROAD])/2.0
        linewidth_track = min(2.0 * scale, max_track_linewidth)

        return CityDrawingSizeConfig(text_fontsize=mm_to_point(3.0) * scale,
                                     text_arrow_linewidth=mm_to_point(0.3) * scale,
                                     paper_size=paper_size,
                                     caracteristic_distance=diagonal_distance_m,
                                     linewidth_priority=linewidth_priority,
                                     linewidth_track=linewidth_track,
                                     bridge_markersize=bridge_markersize)
