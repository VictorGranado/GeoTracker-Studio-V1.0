# GeoTracker Studio v1.0

<p align="center">
  <img src="assets/geotracker_studio.png" alt="GeoTracker Studio logo" width="120">
</p>

<p align="center">
  <strong>Desktop visualization and analysis software for GeoTracker v1.0 field data.</strong>
</p>

<p align="center">
  Import GeoTracker sessions, reconstruct GPS routes, inspect synchronized sensor data,
  visualize routes in 2D and 3D, overlay OpenStreetMap imagery, and export to KML/GPX.
</p>

---

## Overview

**GeoTracker Studio** is the desktop companion application for **GeoTracker v1.0**, an ESP32-based field survey and mapping device.

GeoTracker v1.0 collects GPS, environmental, magnetic, and motion/orientation data in the field and stores each recording session on a MicroSD card. GeoTracker Studio imports those recorded sessions and turns the raw data into interactive maps, graphs, route visualizations, statistics, waypoints, events, and exportable geographic files.

The project is designed around a simple division of responsibility:

```text
GeoTracker v1.0
Collects and logs field data
        ↓
      CSV
        ↓
GeoTracker Studio
Visualizes, analyzes, and exports it
```

GeoTracker Studio is primarily a **post-mission analysis application**. It does not require cloud storage, user accounts, or a live connection to the GeoTracker device.

---

## Features

### Session import and validation

- Import complete GeoTracker recording folders
- Validate the GeoTracker v1.0 data schema
- Detect missing or invalid data
- Review session metadata and validation status
- Bundled fabricated demo session for exploring the UI before loading real data

### Overview dashboard

- Session duration
- Distance traveled
- Average and maximum speed
- GPS altitude range
- GPS sample statistics
- Temperature, humidity, and pressure summaries
- Waypoint and event counts
- Recent sample preview

### 2D route visualization

- Reconstruct recorded GPS routes
- Start and end markers
- Waypoint and event markers
- Pan, zoom, and fit-to-route controls
- Local meter-based projection for accurate local geometry
- Click/hover sample inspection
- GPS gaps preserved rather than falsely connected

### Sensor-colored route overlays

The route can be colored by recorded measurements such as:

- Temperature
- GPS altitude
- Speed
- Humidity
- Pressure
- Heading
- Magnetic field strength
- GPS quality / HDOP

### In-app OpenStreetMap basemap

- Optional OpenStreetMap layer beneath the 2D route
- Adjustable basemap opacity
- Local tile caching
- No map service required for core offline analysis
- Route and sensor overlays remain fully interactive above the map

### Interactive data graphs

Two synchronized graph panels can display:

- GPS altitude
- Speed
- Satellite count
- Temperature
- Humidity
- Pressure
- Pressure altitude
- Heading
- Magnetic field strength
- Pitch and roll
- Accelerometer X / Y / Z
- Gyroscope X / Y / Z

Horizontal axes can be switched between:

- Elapsed time
- Distance traveled
- Sample ID

### Synchronized inspection

GeoTracker Studio uses `sample_id` as the common link between all visualizations.

Selecting a point in one view updates the others:

```text
2D Map
   ↕
Data Graphs
   ↕
3D Route
   ↕
Selected sensor sample
```

This makes it possible to answer:

> What did GeoTracker measure, when did it happen, and where did it happen?

### 3D route viewer

- Local X/Y coordinates in meters
- GPS altitude as Z
- Vertical exaggeration: 1×, 2×, 5×, 10×
- Sensor-colored 3D route overlays
- Start, end, and waypoint markers
- Orbit, zoom, and pan controls
- Top and perspective camera views
- Optional OpenStreetMap ground plane
- Synchronized sample selection with the 2D map and graphs

### Waypoints and events

- Dedicated waypoint table
- Dedicated event table
- Session start/end events
- User-created waypoints
- GPS fix events
- Other GeoTracker-generated event types

### KML and GPX export

GeoTracker Studio can export:

- Route tracks
- Waypoints
- Start/end locations
- Geolocated events
- GPS altitude
- UTC timestamps

Supported formats:

- **KML** — Google Earth and compatible GIS software
- **GPX 1.1** — GPS/navigation and mapping software

GPS outages are preserved as separate route segments.

---

## Screenshots

### Overview
<img src="Screenshot 2026-09-11 011932.png">

### 2D Route + OpenStreetMap
<img src="Screenshot 2026-09-11 011957.png">

### Data Graphs
<img src="Screenshot 2026-09-11 012011.png">

### 3D Route
<img src="Screenshot 2026-09-11 012047.png">

### KML / GPX Export
<img src="Screenshot 2026-09-11 012109.png">

---

## GeoTracker data model

A GeoTracker recording is stored as one session folder:

```text
session/
├── session_info.csv
├── samples.csv
├── waypoints.csv
└── events.csv
```

### `session_info.csv`

Stores metadata such as:

- schema version
- session ID
- device name
- firmware version
- UTC start time
- logging interval
- coordinate system
- unit system

### `samples.csv`

Contains synchronized measurements from:

**NEO-M8N GPS**
- UTC timestamp
- latitude / longitude
- GPS altitude
- speed
- course
- satellites
- fix state
- HDOP / PDOP / VDOP

**BME280**
- temperature
- humidity
- atmospheric pressure
- estimated pressure altitude

**BMM150**
- magnetic X / Y / Z
- field magnitude
- heading

**MPU-6050**
- acceleration X / Y / Z
- gyroscope X / Y / Z
- pitch
- roll

### `waypoints.csv`

Stores user-created geographic waypoints and links them back to the source sample.

### `events.csv`

Stores session and device events such as:

- `SESSION_START`
- `SESSION_END`
- `GPS_FIX_ACQUIRED`
- `GPS_FIX_LOST`
- `WAYPOINT_CREATED`
- user-defined marks and device events

---

## Installation

### Windows installer

The recommended way to install GeoTracker Studio is with:

```text
GeoTracker Studio v1.0 Setup.exe
```

The installer creates:

- a Start Menu entry
- an optional desktop shortcut
- the GeoTracker Studio application entry in Windows Installed Apps

No Python installation is required for the packaged release.

### Portable Windows build

A portable build can also be generated with PyInstaller:

```text
dist/
└── GeoTracker Studio v1.0/
    ├── GeoTracker Studio.exe
    └── _internal/
```

Keep the executable and `_internal` folder together.

---

## Using GeoTracker Studio

1. Launch **GeoTracker Studio**.
2. Explore the bundled **DEMO DATA** session or open a real GeoTracker session.
3. Select **File → Open session…** or press `Ctrl+O`.
4. Choose a folder containing:

```text
session_info.csv
samples.csv
waypoints.csv
events.csv
```

5. Use the sidebar to move between:
   - Overview
   - 2D Map
   - Data Graphs
   - Waypoints & Events
   - 3D Route
   - Export

OpenStreetMap is optional. The first map load for a new area requires internet access; previously viewed map tiles are cached locally.

On Windows, writable application data and cached tiles are stored under:

```text
%LOCALAPPDATA%\GeoTrackerStudio\
```

---

## Running from source

### Requirements

- Python 3.11 recommended
- Windows 10/11 is the primary tested platform

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the automated tests:

```powershell
python -m pytest -q
```

Launch GeoTracker Studio:

```powershell
python -m geotracker_studio.app
```

For development on Windows, a virtual environment is recommended.

Example:

```powershell
python -m venv C:\gtvenv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
C:\gtvenv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m geotracker_studio.app
```

---

## Building the Windows release

### Portable application

With the development environment active:

```powershell
.\Build_Windows.ps1
```

Output:

```text
dist\GeoTracker Studio v1.0\GeoTracker Studio.exe
```

The build process uses PyInstaller in **onedir** mode for reliable Qt, OpenGL, pandas, and visualization-library packaging.

### Installer

GeoTracker Studio uses **Inno Setup 6** for the Windows installer.

After building the portable application:

```powershell
.\Build_Installer.ps1
```

or compile directly with the Inno Setup compiler:

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" ".\installer\GeoTrackerStudio.iss"
```

Output:

```text
installer_output\GeoTracker Studio v1.0 Setup.exe
```

---

## Technology stack

- **Python 3**
- **PySide6 / Qt** — desktop interface
- **pandas** — CSV parsing and session data model
- **pyqtgraph** — interactive 2D plotting
- **PyOpenGL / pyqtgraph.opengl** — 3D route visualization
- **OpenStreetMap** — optional geographic basemap imagery
- **PyInstaller** — Windows application packaging
- **Inno Setup 6** — Windows installer
- Python standard library XML tools — KML / GPX generation

---

## Project structure

```text
GeoTracker-Studio/
├── geotracker_studio/
│   ├── app.py
│   ├── parser.py
│   ├── models.py
│   ├── schema.py
│   ├── validation.py
│   ├── statistics.py
│   ├── export.py
│   ├── demo_data.py
│   └── ...
│
├── assets/
│   └── geotracker_studio.png
│
├── installer/
│   └── GeoTrackerStudio.iss
│
├── tests/
│
├── GeoTrackerStudio.spec
├── Build_Windows.ps1
├── Build_Installer.ps1
├── requirements.txt
├── USER_GUIDE.md
├── RELEASE_CHECKLIST.md
└── README.md
```

---

## Project relationship

GeoTracker Studio is part of the broader GeoTracker ecosystem:

```text
┌────────────────────────────┐
│      GeoTracker v1.0       │
│                            │
│  ESP32-WROOM-DA            │
│  NEO-M8N GPS               │
│  BME280                    │
│  BMM150                    │
│  MPU-6050                  │
│  MicroSD                   │
│                            │
│  Field acquisition         │
└──────────────┬─────────────┘
               │
               │ CSV session
               ▼
┌────────────────────────────┐
│   GeoTracker Studio v1.0   │
│                            │
│  Session validation        │
│  2D / 3D visualization    │
│  Sensor analysis           │
│  OpenStreetMap             │
│  Waypoints / Events        │
│  KML / GPX export          │
│                            │
│  Post-mission analysis     │
└────────────────────────────┘
```

---

## Current status

GeoTracker Studio v1.0 has been validated as a packaged Windows application.

Verified functionality includes:

- Windows installer
- Start Menu and desktop launch
- branded application icon
- console-free packaged launch
- demo session
- session import
- 2D route visualization
- sensor overlays
- synchronized graphs
- 3D route visualization
- OpenStreetMap layers
- KML / GPX export
- About dialog
- uninstall registration

The remaining field-validation step is testing the complete workflow against real GeoTracker v1.0 MicroSD recordings and refining the parser/visualizations for real-world GPS and sensor behavior.

---

## Planned improvements

Possible future additions include:

- real GeoTracker field-session validation and tuning
- terrain/DEM-based 3D surface mode
- offline map packages
- session comparison
- additional survey overlays
- custom event annotations
- live serial/Wi-Fi telemetry
- automatic GeoTracker device detection

These are future enhancements and are not required for the v1.0 post-processing workflow.

---

## OpenStreetMap attribution

GeoTracker Studio uses optional map imagery from **OpenStreetMap**.

Map data © OpenStreetMap contributors.

OpenStreetMap imagery is only requested when the user explicitly enables the basemap. GeoTracker Studio caches previously viewed tiles and does not implement bulk map prefetching.

---

## License

This project is licensed under the **MIT License**.

See [`LICENSE`](LICENSE) for the full license text.

---

## Author

**Victor STafussi Granado**

Computer Engineering / Embedded Systems

GeoTracker Studio was developed as the desktop visualization and analysis companion for the GeoTracker v1.0 embedded field-mapping platform.
