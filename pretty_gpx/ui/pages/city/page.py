#!/usr/bin/python3
"""City UI."""
import copy
import os
import tempfile
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import field

from natsort import index_natsorted
from nicegui import events
from nicegui import ui
from nicegui.elements.upload import Upload
from nicegui.run import SubprocessException
from pathvalidate import sanitize_filename

from pretty_gpx.common.layout.paper_size import PAPER_SIZES
from pretty_gpx.common.layout.paper_size import PaperSize
from pretty_gpx.common.utils.logger import logger
from pretty_gpx.common.utils.paths import RUNNING_DIR
from pretty_gpx.common.utils.profile import profile
from pretty_gpx.common.utils.profile import profile_parallel
from pretty_gpx.common.utils.profile import Profiling
from pretty_gpx.common.utils.utils import safe
from pretty_gpx.rendering_modes.city.city_poster_image_cache import CityPosterDrawingData
from pretty_gpx.rendering_modes.city.city_poster_image_cache import CityPosterImageCache
from pretty_gpx.rendering_modes.city.city_poster_image_cache import W_DISPLAY_PIX
from pretty_gpx.rendering_modes.city.data.augmented_gpx_data import CityAugmentedGpxData
from pretty_gpx.rendering_modes.city.drawing.theme_colors import DARK_COLOR_THEMES
from pretty_gpx.rendering_modes.city.drawing.theme_colors import LIGHT_COLOR_THEMES
from pretty_gpx.ui.utils.run import on_click_slow_action_in_other_thread
from pretty_gpx.ui.utils.run import run_cpu_bound
from pretty_gpx.ui.utils.run import UiWaitingModal
from pretty_gpx.ui.utils.shutdown import add_exit_button
from pretty_gpx.ui.utils.style import BOX_SHADOW_STYLE
from pretty_gpx.ui.utils.style import DARK_MODE_TEXT
from pretty_gpx.ui.utils.style import LIGHT_MODE_TEXT


@profile_parallel
def process_files(list_b: list[bytes] | list[str], new_paper_size: PaperSize) -> CityPosterImageCache:
    """Process the uploaded files and return the MountainPosterImageCaches."""
    return CityPosterImageCache.from_gpx(list_b, new_paper_size)


@profile_parallel
def change_paper_size(gpx_data: CityAugmentedGpxData, new_paper_size: PaperSize) -> CityPosterImageCache:
    """Return the MountainPosterImageCaches with the new paper size."""
    return CityPosterImageCache.from_gpx_data(gpx_data, new_paper_size)
 
 
def city_page() -> None:
    """City Page."""
    class UiManagerCity:
        """Manage the UI elements and the Poster cache."""

        _cache: CityPosterImageCache | None = field(default=None)

        def get_cache(self) -> CityPosterImageCache | None:
            """Get the current cache."""
            return copy.deepcopy(self._cache)


        async def _on_upload(self, contents: list[bytes] | list[str], msg: str) -> None:
            """Pocess the files asynchronously to update the Poster cache."""
            with UiWaitingModal(msg):
                try:
                    self._cache = await run_cpu_bound(process_files,
                                                      contents, PAPER_SIZES[safe(paper_size_mode_toggle.value)])
                except SubprocessException as e:
                    logger.error(f"Error while {msg}: {e}")
                    logger.warning("Skip processing uploaded files")
                    ui.notify(f'Error while {msg}:\n{e.original_message}',
                            type='negative', multi_line=True, timeout=0, close_button='OK')
                    return

            await on_click_update()()

        async def on_multi_upload(self, e: events.MultiUploadEventArguments) -> None:
            """Sort the uploaded files by name and process them to update the Poster cache."""
            sorted_indices = index_natsorted(e.names)
            names = [e.names[i] for i in sorted_indices]
            contents = [e.contents[i].read() for i in sorted_indices]
            assert isinstance(e.sender, Upload)
            e.sender.reset()

            if len(contents) == 1:
                msg = f"Processing {names[0]}"
            else:
                msg = f'Processing {len(names)} tracks ({", ".join(names)})'

            await self._on_upload(contents, msg)

        async def on_click_load_example(self) -> None:
            """Load the example GPX file."""
            contents = [os.path.join(RUNNING_DIR, "route_4_chateaux.gpx")]
            await self._on_upload(contents, "Generate an example poster")

        async def on_paper_size_change(self) -> None:
            """Change the paper size and update the poster."""
            new_paper_size_name = str(safe(paper_size_mode_toggle.value))
            with UiWaitingModal(f"Creating {new_paper_size_name} Poster"):
                self._cache = await run_cpu_bound(change_paper_size, safe(self.get_cache()).gpx_data,
                                                   PAPER_SIZES[new_paper_size_name])
            await on_click_update()()


    ui_manager = UiManagerCity()


    with ui.row().style("height: 100vh; width: 100%; justify-content: center; align-items: center; gap: 20px;"):
        with ui.card().classes(f'w-[{W_DISPLAY_PIX}px]').style(f'{BOX_SHADOW_STYLE};'):
            with ui.pyplot(close=False) as plot_city:
                ax_city = plot_city.fig.add_subplot()
                ax_city.axis('off')

        with ui.column(align_items="center"):
            ui.chat_message(
                ['Welcome 😀\nCreate a custom poster from\n'
                'your cycling/running GPX file! 🚵 🥾',
                'For multi-files runs/cycling events, upload\n'
                'all consecutive GPX tracks together.\n'
                '(Make sure filenames are in alphabetical order)',
                'Customize your poster below and download\n'
                'the High-Resolution SVG file when ready.\n']
            ).props('bg-color=blue-2')

            ui.upload(label="Drag & drop your GPX file(s) here and press upload",
                    multiple=True,
                    on_multi_upload=ui_manager.on_multi_upload
                    ).props('accept=.gpx'
                            ).on('rejected', lambda: ui.notify('Please provide a GPX file')
                                ).classes('max-w-full')

            with ui.card():
                paper_size_mode_toggle = ui.toggle(list(PAPER_SIZES.keys()), value=list(PAPER_SIZES.keys())[0],
                                                   on_change=ui_manager.on_paper_size_change)

            # Update options
            with ui.card():
                def _update(c: CityPosterImageCache) -> CityPosterDrawingData:
                    """Asynchronously update the MountainPosterDrawingData with the current settings."""
                    dark_mode = bool(safe(dark_mode_switch.value))

                    color_themes = (DARK_COLOR_THEMES if dark_mode else LIGHT_COLOR_THEMES)
                    p_cache, drawing_data = c.update_drawing_data(theme_colors=color_themes[safe(theme_toggle.value)],
                                                                  title_txt=title_button.value,
                                                                  uphill_m=uphill_button.value,
                                                                  duration_s=duration_s_button.value,
                                                                  dist_km=dist_km_button.value)
                    
                    ui_manager._cache = p_cache
                    return drawing_data

                def _update_done_callback(c: CityPosterImageCache,
                                          poster_drawing_data: CityPosterDrawingData) -> None:
                    """Synchronously update the plot with the CityPosterDrawingData.
                    
                    (Matplotlib must run in the main thread).
                    """
                    with Profiling.Scope("Pyplot Context"), plot_city:
                        c.draw(plot_city.fig, ax_city, poster_drawing_data)
                    ui.update(plot_city)


                @profile_parallel
                def update() -> CityPosterDrawingData:
                    """Update the MountainPosterDrawingData with the current settings, at the high resolution."""
                    return _update(safe(ui_manager.get_cache()))

                @profile
                def update_done_callback(poster_drawing_data: CityPosterDrawingData) -> None:
                    """Update the plot with the low resolution MountainPosterDrawingData."""
                    _update_done_callback(safe(ui_manager.get_cache()), poster_drawing_data)

                def on_click_update() -> Callable[[], Awaitable[None]]:
                    """Return an async function that updates the poster with the current settings."""
                    return on_click_slow_action_in_other_thread('Updating', update, update_done_callback)

                with ui.input(label='Title', value="Title").on('keydown.enter', on_click_update()) as title_button:
                    ui.tooltip("Press Enter to update title")

                ui.label("To remove a field, enter a zero or negative value")

                with ui.input(label='D+ (m)', value="").on('keydown.enter', on_click_update()) as uphill_button:
                    ui.tooltip("Press Enter to override elevation from GPX")

                with ui.input(label='Distance (km)', value="").on('keydown.enter', on_click_update()) as dist_km_button:
                    ui.tooltip("Press Enter to override distance from GPX")
                
                with ui.input(label='Time (enter in seconds)', value="").on('keydown.enter',
                                                                            on_click_update()) as duration_s_button:
                    ui.tooltip("Press Enter to override distance from GPX")

                def on_dark_mode_switch_change(e: events.ValueChangeEventArguments) -> None:
                    """Switch between dark and light mode."""
                    dark_mode = e.value
                    dark_mode_switch.text = DARK_MODE_TEXT if dark_mode else LIGHT_MODE_TEXT
                    theme_toggle.options = list(DARK_COLOR_THEMES.keys()) if dark_mode else list(
                        LIGHT_COLOR_THEMES.keys())
                    theme_toggle.value = theme_toggle.options[0]
                    theme_toggle.update()

                dark_mode_switch = ui.switch(DARK_MODE_TEXT, value=True,
                                            on_change=on_dark_mode_switch_change)

                theme_toggle = ui.toggle(list(DARK_COLOR_THEMES.keys()), value=list(DARK_COLOR_THEMES.keys())[0],
                                        on_change=on_click_update())

                @profile_parallel
                def download() -> bytes:
                    """Save the high resolution poster as SVG and return the bytes."""
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        with Profiling.Scope("Matplotlib Save SVG"):
                            tmp_svg = os.path.join(tmp_dir, "tmp.svg")
                            plot_city.fig.savefig(tmp_svg, dpi=400)
                        with open(tmp_svg, "rb") as svg_file:
                            return svg_file.read()

                def download_done_callback(svg_bytes: bytes) -> None:
                    """Download the SVG file."""
                    ui.download(svg_bytes, f'poster_{sanitize_filename(str(title_button.value).replace(" ", "_"))}.svg')
                    logger.info("Poster Downloaded")

                async def on_click_download() -> None:
                    """Asynchronously render the high resolution poster and download it as SVG."""
                    dpi = 400
                    await on_click_slow_action_in_other_thread(f'Exporting SVG ({dpi} dpi)',
                                                               download, download_done_callback)()

                ui.button('Download', on_click=on_click_download)
                ui.button('Load example', on_click=ui_manager.on_click_load_example)                

    add_exit_button()