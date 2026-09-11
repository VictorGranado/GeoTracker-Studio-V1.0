# GeoTracker Studio v1.0 — Quick User Guide

## Start

Launch **GeoTracker Studio.exe** from the portable release folder, or install it using **GeoTracker Studio v1.0 Setup.exe**.

The application starts with a clearly marked **DEMO DATA** session so the interface can be explored before real GeoTracker logs are available.

## Open a GeoTracker session

Choose **File → Open session…**, press **Ctrl+O**, or use **Open session** in the sidebar.

Select a session folder containing the GeoTracker v1.0 data contract files:

```text
session_info.csv
samples.csv
waypoints.csv
events.csv
```

## Main pages

- **Overview** — trip summary, validation state, metadata, and recent samples.
- **2D Map** — GPS route, sensor overlays, OpenStreetMap basemap, markers, and synchronized sample inspection.
- **Data Graphs** — two interactive sensor graphs synchronized by `sample_id`.
- **Waypoints & Events** — recorded waypoint and event tables.
- **3D Route** — metric X/Y route with GPS altitude as Z, sensor overlays, vertical exaggeration, and optional map ground plane.
- **Export** — KML and GPX output with optional altitude, timestamps, waypoints, events, and start/end markers.

## Basemaps

OpenStreetMap is optional. Selecting it requires internet access on the first view of an area; viewed tiles are cached locally. GeoTracker Studio remains usable with **No basemap** selected.

Map data attribution remains visible in the application.

## Demo versus real data

The bundled fabricated session is marked **DEMO DATA** in the sidebar and Overview page. That badge disappears when a normal GeoTracker session is loaded.

## Export

Use **Export** to create KML for Google Earth/GIS software and GPX for compatible GPS/navigation tools. GPS outages are preserved as separate route segments rather than being falsely connected.

## Application data

On Windows, writable application data and cached map tiles are stored under:

```text
%LOCALAPPDATA%\GeoTrackerStudio\
```
