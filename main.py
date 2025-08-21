# to get data on phone go to settings > location > location services > timeline > export timeline data

import os
import json
import yaml
import logging
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box, mapping
from shapely.ops import unary_union
from glob import glob
from enum import StrEnum
import folium

def random_color():
    """Generate a random color in hex format."""
    import random
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# ------------------- CONFIGURATION -------------------

# Load config from YAML
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

BUFFER_SIZE = config.get("buffer_size", 1000)
SIMPLIFY_TOLERANCE_METERS = config.get("simplify_tolerance_meters", 900)
FOG_OPACITY = config.get("fog_opacity", 0.5)

# ------------------- LOGGING SETUP -------------------

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting script...")

# ------------------- ENUM AND COLORS -------------------

# Dynamically get folder names in 'data'
people_names = [name for name in os.listdir("data") if os.path.isdir(os.path.join("data", name))]
extra_members = ["ALL", "INTERSCECTION"]
People = StrEnum('People', people_names + extra_members)

# Assign colors to each person
base_colors = ["#36007d", "#7a1600"]
colors = {}
for i, person in enumerate(People):
    if i < len(base_colors):
        colors[person] = base_colors[i]
    else:
        colors[person] = random_color()
colors[People.INTERSCECTION] = "#006117"  # Fixed color for intersection

# Ensure all people have a color
for person in People:
    if person not in colors:
        colors[person] = random_color()

logger.info(f"Colors assigned: {colors}")

# ------------------- LOAD JSON DATA -------------------

json_paths = {person: glob(f"data/{person}/*.json") for person in People}
logger.debug(f"JSON paths: {json_paths}")

js = {person: [] for person in People}
for person in People:
    logger.info(f"Loading JSON for {person}...")
    for json_path in json_paths[person]:
        with open(json_path, "r", encoding="utf-8") as f:
            js[person].append(json.load(f))
    logger.info(f"Loaded {len(js[person]):,} files for {person}")

# ------------------- EXTRACT POINTS -------------------

points_strings = {person: [] for person in People}
for person in People:
    logger.info(f"Extracting points for {person}...")
    for j in js[person]:
        # Extract points from semanticSegments
        if "semanticSegments" in j:
            for segment in j["semanticSegments"]:
                path = segment.get("timelinePath", None)
                if path is None:
                    continue
                for point in segment["timelinePath"]:
                    points_strings[person].append(point["point"])
        # Extract points from rawSignals
        if "rawSignals" in j:
            for signal in j["rawSignals"]:
                if "position" in signal:
                    points_strings[person].append(signal["position"]["LatLng"])
    logger.info(f"Extracted {len(points_strings[person]):,} points for {person}")

# ------------------- CREATE AREAS -------------------

areas = dict()
for person in People:
    if person in [People.ALL, People.INTERSCECTION]:
        continue
    logger.info(f"Processing areas for {person}...")
    # Parse and round points, drop duplicates
    points = [[float(x) for x in p.replace("°", "").split(",")] for p in points_strings[person]]
    rounded_points = [[round(lat, 4), round(lon, 4)] for lat, lon in points]
    df = pd.DataFrame(rounded_points, columns=["lat", "lon"])
    df = df.drop_duplicates()
    logger.info(f"{person}: {len(df):,} unique points after rounding and deduplication.")

    # Create GeoDataFrame and buffer in meters (projected CRS)
    geometry = [Point(row["lon"], row["lat"]) for _, row in df.iterrows()]
    gdf = gpd.GeoDataFrame(geometry=geometry, crs="EPSG:4326")
    gdf_3857 = gdf.to_crs("EPSG:3857")
    buffers = gdf_3857.buffer(BUFFER_SIZE)
    area_3857 = unary_union(buffers).simplify(SIMPLIFY_TOLERANCE_METERS, preserve_topology=True)
    # Convert back to EPSG:4326 for folium
    area_4326 = gpd.GeoSeries([area_3857], crs="EPSG:3857").to_crs("EPSG:4326").iloc[0]
    areas[person] = area_4326
    logger.info(f"{person}: Area geometry created and simplified.")

# ------------------- COMBINE AREAS -------------------

# Union all individual areas for ALL
areas[People.ALL] = unary_union([areas[p] for p in People if p not in [People.ALL, People.INTERSCECTION]])

# Intersection of all individual areas for INTERSCECTION
intersction_keys = [p for p in People if p not in [People.ALL, People.INTERSCECTION]]
areas[People.INTERSCECTION] = areas[intersction_keys[0]]
for person in intersction_keys[1:]:
    areas[People.INTERSCECTION] = areas[People.INTERSCECTION].intersection(areas[person])
logger.info("Combined ALL and INTERSCECTION areas.")

# Remove intersection from individual areas
for person in People:
    if person in [People.ALL, People.INTERSCECTION]:
        continue
    areas[person] = areas[person].difference(areas[People.INTERSCECTION])
    logger.info(f"{person}: Area difference applied.")

# ------------------- CREATE FOLIUM MAP -------------------

# Get the center of the ALL area for the map
center = [areas[People.ALL].centroid.y, areas[People.ALL].centroid.x]
logger.info(f"Map center: {center}")

# Create the base folium map (greyscale)
m = folium.Map(location=center, zoom_start=8, tiles="CartoDB positron")
logger.info("Folium map created.")

# Create the fog polygon (subtracting the clear areas)
bounds = [-180, -90, 180, 90]  # use whole world bounds
area = box(*bounds).buffer(0.01)  # Slightly larger than bounds
clear_area = unary_union(areas[People.ALL])
fog = area.difference(clear_area)
logger.info("Fog polygon created.")

# Add the fog polygon to the map
folium.GeoJson(
    mapping(fog),
    style_function=lambda x: {
        'fillColor': 'black',
        'color': 'black',
        'weight': 1,
        'fillOpacity': FOG_OPACITY
    }
).add_to(m)
logger.info("Fog polygon added to map.")

# Shade areas for each person
for person in People:
    if person in [People.ALL]:
        continue
    folium.GeoJson(
        mapping(areas[person]),
        style_function=lambda x, color=colors[person]: {
            'fillColor': color,
            'color': color,
            'weight': 1,
            'fillOpacity': 0.5
        },
        name=person.name
    ).add_to(m)
    logger.info(f"Added area for {person} to map.")

# ------------------- ADD LEGEND -------------------

legend_html = '''
    <div style="position: fixed;
                bottom: 50px;
                left: 50px;
                background-color: white;
                border: 2px solid black;
                z-index: 9999;
                font-size: 14px;
                padding: 10px;">
        <strong>Legend</strong><br>
        '''
for person in People:
    if person == People.ALL:
        continue
    elif person == People.INTERSCECTION:
        legend_html += f'<i style="background: {colors[person]}; width: 20px; height: 20px; display: inline-block;"></i> Both<br>'
    else:
        legend_html += f'<i style="background: {colors[person]}; width: 20px; height: 20px; display: inline-block;"></i> {person.title()}<br>'
legend_html += '''
    </div>
'''
m.get_root().html.add_child(folium.Element(legend_html))
logger.info("Legend added.")

# ------------------- SAVE MAP -------------------

m.save("map.html")
logger.info("Map saved to map.html")