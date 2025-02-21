# 🚴‍♂️ pretty-gpx 🏞️

# Description

Transform your running, cycling or hiking adventures into stunning, ready-to-print posters with this app! Designed specifically for mountain routes, it takes your GPX file and effortlessly generates a custom poster that beautifully showcases your journey. Built on the powerful [NiceGUI](https://nicegui.io/) framework, the app offers an intuitive web interface that makes the entire process seamless.

Two modes are available : a city mode drawing the gpx data with the street maps in the background and a mountain mode drawing the gpx data on an elevation map. You can switch between both of them in the GUI.

# Demo

Here's a demo GIF to give you a glimpse of a user interacting with the webapp and exploring its features.

![](./doc/demo.gif)

# Installation

### Option 1: Install Locally

Make sure you have Python version 3.11 or higher installed.

Install the dependencies.

```
pip3 install -r .devcontainer/requirements.txt
```

In ubuntu, install the packages.
```
sudo xargs -a .devcontainer/packages.txt apt-get install -y
```

**Remark:** You can set the directory path in the PYTHONPATH environment variable so that the imports of other files from the repository are working properly.

* On Linux

You can add a line in the .bashrc file :
```
nano ~/.bashrc
```
And add this line at the bottom of the file where /path/to/add is pretty_gpx repository path.
```
export PYTHONPATH=$PYTHONPATH:/path/to/add
```
If you always run the code from the repository folder instead of /path/to/add you can use:
```
export PYTHONPATH=$PYTHONPATH:$PWD
```

* In a conda environment

In a conda environment enter (do not forget to edit the /path/to/add):

```
conda env config vars set PYTHONPATH=$PYTHONPATH:/path/to/add
```

After a restart of the environment :

```
conda deactivate
conda activate your_env_name
```

You can check that the environment variable has been successfully updated:

```
conda env config vars list
```

You should see the updated PYTHONPATH value.

### Option 2: Open in VS Code with Dev Containers

If you are using Visual Studio Code, you can take advantage of the Dev Containers feature:
- Install the Remote - Containers extension in VS Code.
- Open this project folder in VS Code.
- When prompted, select Reopen in Container.

This will open the project in a fully configured container environment based on the `.devcontainer` configuration, allowing you to work without manually setting up dependencies.

### Run

Finally, run the webapp.
```
python3 pretty_gpx/main.py
```


# Features

This app features two modes:

- The city mode
- The mountain mode

## Mountain mode

This app is the perfect companion for cycling or hiking enthusiasts tackling routes with significant elevation gain.

### 🌄 Hillshading

Add depth and realism to your map with hillshading effects that emphasize the natural ruggedness of mountainous landscapes. Adjust the sun's orientation to create the perfect lighting.

This feature leverages terrain elevation data from the [Global Copernicus Digital Elevation Model at 30 meter resolution](https://registry.opendata.aws/copernicus-dem/), ensuring high-quality elevation details for accurate and visually striking results.

### 🏔️ Mountain Passes & Elevation Profile

Easily spot mountain passes and saddles along your track, with accurate elevation information. The elevation profile, displayed below the track, mirrors these key landmarks with matching icons, giving you a clear and intuitive overview of your journey's vertical challenges.

This feature utilizes [OpenStreetMap data](https://www.openstreetmap.org) via the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) for precise and up-to-date information.

### 🏕️ Multi-Day Trip Support

Planning a multi-day adventure? Upload all your consecutive daily GPX tracks in one go — just ensure the filenames are in alphabetical order. The app will automatically identify and display known huts or campsites at each stop between the tracks.

### 🎨 Customization Options

Personalize your poster with options to update the track title, adjust sun orientation, and select from various color themes, making the map truly your own.

### 📥 Easy Download

Once you’ve fine-tuned your poster, simply hit the Download button to save your customized map.

### 📝 Text annotations

Placing text annotations for mountain passes, huts, or other landmarks can be challenging, as they may overlap with each other or obscure the GPX track. To ensure precise placement and a clean layout, we rely on [textalloc](https://github.com/ckjellson/textalloc), a robust tool that automatically optimizes text to prevent overlap.

### ⛶ Poster Size

When you change the poster size, the corresponding latitude and longitude area also changes. This requires a fresh request for new elevation data, as the previous data no longer covers the updated area.

In addition to the elevation data, resizing the poster also impacts the available space around your track. This change in layout may affect the positioning of text annotations such as labels for mountain passes or huts.

Because resizing involves both requesting new elevation data and reoptimizing the text annotations, the process takes longer than simpler adjustments like changing the color theme.

## City mode

The city mode is perfect for activities done in an urban environment. It will draw roads, rivers and forest/land in the background and the GPX track above it.

This feature utilizes [OpenStreetMap data](https://www.openstreetmap.org) via the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) to gather road, rivers, lakes and other area with water as well as forests and agricultural plots.

### 📝 Activity stats

The distance, elevation gain and time of the activity plotted is written on the poster by default. If you want to remove one of these fields, just enter a 0 or negative value.
If you want to override the time, you will need to enter the time **in seconds** that you want to have written on the poster.

### Bridges detection

The system automatically identifies bridges crossed by your path. It does this by approximating each bridge as a rectangular area and using two criteria:

- **Intersection Length**: If the length of the path's intersection with the rectangular area exceeds 70% of the bridge's length, the bridge is considered crossed.
- **Angle Threshold**: The angle between the path and the bridge's axis must be below a certain threshold to ensure that only bridges directly crossed are detected, avoiding false positives.


### ⛶ Poster Size

You have the same options as the mountain mode for the paper sizes. It is possible to find the most suitable format for your activity.

### 📥 Easy Download

Once you’ve fine-tuned your poster, simply hit the Download button to save your customized map.

# Explore new color themes

The project currently offers 4 dark and 4 light color themes, but you are encouraged to create and experiment with new ones!

In dark mode, hillshading modulates the background between black and the theme's background color. To achieve visually appealing results, the darkest color in your triplet should be assigned as the background. Ideally, it should be dark enough to maintain the readability of overlaid elements, yet distinct enough from pure black to enhance the hillshading effect.

In light mode, the approach is similar but uses white as the base, with the lightest color taking the role of the background.

The script below takes a list of color triplets as input and generates posters for both light and dark modes, helping you identify aesthetic themes. The background color is automatically selected based on brightness, while the other two colors are permuted, resulting in 4 unique posters per color triplet.

```
python3 pretty_gpx/explore_color_themes.py
```


# Simplify a GPX file

If your GPX file is quite heavy, e.g. 20Mo, you can run the following script to make it lighter.

```
python3 pretty_gpx/simplify_gpx.py --input <GPX_FILE>
```

# Examples

To give you a better idea of what this app can create, here are some example posters generated from real GPX tracks (See the `examples` folder).


## Mountain mode


<table>
  <tr>
    <td><img src="doc/posters/mountain/marmotte.svg" style="max-width: 100%; height: auto;"/></td>
    <td><img src="doc/posters/mountain/diagonale-des-fous.svg" style="max-width: 100%; height: auto;"/></td>
  </tr>
  <tr>
    <td><img src="doc/posters/mountain/hawaii.svg" style="max-width: 100%; height: auto;"/></td>
    <td><img src="doc/posters/mountain/couillole.svg" style="max-width: 100%; height: auto;"/></td>
  </tr>
  <tr>
    <td><img src="doc/posters/mountain/peyresourde.svg" style="max-width: 100%; height: auto;"/></td>
    <td><img src="doc/posters/mountain/vanoise_3days.svg" style="max-width: 100%; height: auto;"/></td>
  </tr>
</table>

## City mode


<table>
  <tr>
    <td><img src="doc/posters/city/marathon_pour_tous.svg" style="max-width: 100%; height: auto;"/></td>
    <td><img src="doc/posters/city/deauville.svg" style="max-width: 100%; height: auto;"/></td>
  </tr>
  <tr>
    <td><img src="doc/posters/city/paris_versailles.svg" style="max-width: 100%; height: auto;"/></td>
    <td><img src="doc/posters/city/route_des_4_chateaux.svg" style="max-width: 100%; height: auto;"/></td>
  </tr>
  <tr>
    <td><img src="doc/posters/city/london_marathon.svg" style="max-width: 100%; height: auto;"/></td>
    <td><img src="doc/posters/city/chicago_marathon.svg" style="max-width: 100%; height: auto;"/></td>
  </tr>
</table>

# Contributing

Contributions are welcome!

When creating a Pull Request (PR), please prefix your PR title with one of the following tags to automatically apply the appropriate label:

- **feat**: Introduce a new feature
- **fix**: Fix a bug or issue
- **docs**: Improve or add documentation
- **test**: Add or modify tests
- **ci**: Update continuous integration/configuration
- **refactor**: Refactor code without changing functionality
- **perf**: Improve performance
- **revert**: Revert a previous change

### Example PR Titles:

- `feat: Add wonderful new feature`
- `fix: Correct image aspect ratio issue`

Thank you for contributing!

# License

This project is licensed under the non-commercial [CC BY-NC-SA 4.0 License](LICENSE).
