# Fog of War

This project generates an interactive "fog of war" map using location history data exported from your phone. The map visually displays areas you (and optionally others) have visited, clearing the "fog" around those locations and leaving the rest of the world obscured.

## What the Code Produces

- **An interactive HTML map** (`map.html`) showing:
  - Cleared areas (visited) for each person, color-coded.
  - Overlapping (intersection) areas where multiple people have visited.
  - A "fog" (dark overlay) covering all other areas.
  - A legend explaining the color coding.
- The map can be opened in any web browser.

## How to Get the Data

1. **Export Your Location History from Your Phone:**
   - On Android:  
     - Go to **Settings** > **Location** > **Location Services** > **Google Location History** > **Manage Timeline**.
     - In the Timeline, look for an option to **Export** or **Download** your location data (usually as JSON files).
   - On iOS:  
     - Use the Google Maps Timeline (if enabled) or other location tracking apps that allow export.
   - You should end up with one or more `.json` files containing your location history.

2. **Organize the Data:**
   - Create a folder named `data` in the project directory.
   - Inside `data`, create a subfolder for each person (e.g., `JED`, `BECKY`).
   - Place each person's exported `.json` files in their respective folder:
     ```
     data/
       JED/
         history1.json
         history2.json
       BECKY/
         becky_history.json
     ```

3. **Configure the Project:**
   - Edit `config.yaml` to set buffer size, simplify tolerance, and fog opacity as desired:
     ```yaml
     buffer_size: 1000  # Buffer radius in meters around each point
     simplify_tolerance_meters: 900  # Simplification tolerance in meters
     fog_opacity: 0.5  # Opacity of the fog overlay (0 = transparent, 1 = opaque)
     ```

## How to Run

1. **Install Requirements:**
   - Ensure you have Python 3.7+ installed.
   - Install the required Python packages using `pip`:
     ```bash
     pip install -r requirements.txt
     ```

2. **Prepare the Data:**
   - Place all `.json` files in the appropriate `data` subfolders as described in the "How to Get the Data" section.

3. **Run the Processing Script:**
   - Execute the `main.py` script to process the location data and generate the map:
     ```bash
     python main.py
     ```
   - This will create the `map.html` file and any necessary intermediate files.

4. **View the Map:**
   - Open `map.html` in a web browser to view the interactive fog of war map.
   - Use the controls on the map to adjust the view, zoom in/out, and toggle layers as needed.

## Customization Options

- You can customize the map appearance and behavior by modifying the `config.yaml` settings and the `main.py` script.
- For advanced customization, edit the HTML/CSS/JavaScript in `map.html` directly.