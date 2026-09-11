# GeoTracker Studio v1.0 — Phase 2H Final Release Polish

This release candidate builds on the verified packaged Phase 2G.1 application and adds the final usability and distribution layer.

## New in Phase 2H

- Clearly marked **DEMO DATA** state in the Overview page and sidebar.
- Demo-data banner with one-click access to open a real session.
- Consistent vector icons for every sidebar workspace page.
- Standard **File** and **Help** menus.
- **Ctrl+O** session-open shortcut.
- Branded **About GeoTracker Studio** dialog with version and map attribution.
- Windows installer definition for **Inno Setup 6**.
- `Build_Installer.ps1` and one-command `Build_Release.ps1` release scripts.
- Quick user guide and release checklist.

## Build the portable Windows application

```powershell
C:\gtvenv\Scripts\Activate.ps1
.\Build_Windows.ps1
```

Portable output:

```text
dist\GeoTracker Studio v1.0\GeoTracker Studio.exe
```

## Build the installer

After the portable application has been built, install **Inno Setup 6** and run:

```powershell
.\Build_Installer.ps1
```

Installer output:

```text
installer_output\GeoTracker Studio v1.0 Setup.exe
```

Or run `Build_Release.ps1` to perform both stages in sequence.

See `USER_GUIDE.md` and `RELEASE_CHECKLIST.md` for end-user and release-validation instructions.

---

# GeoTracker Studio v1.0 — Phase 2G Release Candidate

This build refines the visual identity and prepares GeoTracker Studio for a normal Windows distribution.

## Visual identity

- New GeoTracker route/pin application mark.
- Refined sidebar wordmark with `Geo` accent and `Tracker` neutral text.
- Separate STUDIO label and version badge.
- Windows/window icon assets in `assets/`.
- Cleaner sidebar section hierarchy and spacing.

## Release packaging

The application is configured for a **PyInstaller onedir build**. The release build keeps Qt, OpenGL, pandas and visualization dependencies beside the executable for reliability.

### Build on Windows

With the GeoTracker virtual environment active, either double-click:

```text
Build_Windows.bat
```

or run:

```powershell
.\Build_Windows.ps1
```

The script installs the build dependency, runs the complete test suite, and only packages the application if tests pass.

Output:

```text
dist/
└── GeoTracker Studio v1.0/
    ├── GeoTracker Studio.exe
    └── _internal/
```

The packaged app stores writable demo data and map cache under the user's local application-data directory rather than modifying the installation folder.

## Source launch

```powershell
python -m geotracker_studio.app
```


---

# GeoTracker Studio — Phase 2F.1 In-App Basemaps

Phase 2F adds **georeferenced map layers directly inside GeoTracker Studio** while preserving all Phase 2E functionality: 2D/3D visualization, synchronized sample selection, sensor overlays, and KML/GPX export.

## New in Phase 2F

### 2D Map basemap
The **2D Map** page now includes a **Map layer** selector:

- No basemap
- OpenStreetMap

When OpenStreetMap is selected, Studio downloads only the small set of raster tiles required to cover the currently loaded route, composites them into one georeferenced map image, and places that image beneath the existing route and sensor overlays.

The existing local-meter projection is preserved, so:

- route shape remains metrically correct for local field sessions;
- sensor-colored route overlays remain available;
- start/end, waypoints, and events stay synchronized;
- hover/click sample inspection continues to work;
- map opacity can be adjusted independently.

### 3D Route basemap
The **3D Route** page has the same map-layer selector.

OpenStreetMap is rendered as a **georeferenced ground image plane** beneath the 3D GPS/altitude path. The route still uses GPS altitude for Z and retains:

- vertical exaggeration;
- sensor-colored overlays;
- start/end and waypoint markers;
- camera orbit/zoom/pan;
- top/perspective views;
- synchronized sample selection.

This is a map-under-3D-route view, not yet a terrain-elevation mesh. A future terrain mode can drape the same map imagery over DEM/elevation data.

## Tile behavior

The OpenStreetMap integration is intentionally conservative:

- one zoom level is selected for the currently viewed session;
- at most 16 tiles are requested for the route mosaic;
- previously viewed tiles are cached locally and reused;
- no city/region prefetch or offline-download feature is implemented;
- a GeoTracker Studio-specific HTTP User-Agent is sent;
- OpenStreetMap attribution stays visible in the application.

Typical Windows cache location:

```text
%LOCALAPPDATA%\GeoTrackerStudio\tile_cache\
```

The first map load requires an internet connection. If map tiles cannot be loaded, the normal GeoTracker route visualization remains usable.

## Phase 2E features retained

The **Export** page still provides:

- KML export;
- GPX 1.1 export;
- optional altitude/timestamps;
- optional waypoints/events/start/end markers;
- preservation of GPS gaps as separate track segments.

## Run

Use the same virtual environment as the previous phases:

```powershell
C:\gtvenv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python -m geotracker_studio.app
```

Phase 2F adds **no new Python dependency**. Basemap networking uses Python's standard library and image rendering uses the existing PySide6/pyqtgraph stack.

Expected automated-test result:

```text
25 passed
```

## Recommended validation

1. Launch GeoTracker Studio.
2. Open **2D Map**.
3. Change **Map layer** from `No basemap` to `OpenStreetMap`.
4. Confirm roads/buildings appear beneath the fabricated route.
5. Adjust **Map opacity**.
6. Switch sensor route overlays and verify they remain aligned to the map.
7. Open **3D Route**.
8. Select `OpenStreetMap` there as well.
9. Confirm the map appears as the ground plane under the elevated route.
10. Test 1×, 5×, and 10× vertical scales plus Top/Perspective views.
11. Switch back to 2D; the same tiles should load from the local cache.

## Project status

```text
Overview                    complete
2D route analysis           complete
2D sensor overlays          complete
Data Graphs                 complete
2D ↔ Graph synchronization  complete
3D Route                    complete
3D ↔ 2D ↔ Graph sync        complete
KML / GPX export            complete
2D in-app basemap           complete
3D in-app basemap plane     complete

Release polish / packaging  next
Real GeoTracker validation  later integration step
Optional terrain DEM mode   future enhancement
```


## Phase 2F.1 layout patch

- Split 2D/3D map controls into responsive rows.
- Prevent option boxes from colliding at normal window widths.
- Added compact widths for map, route-overlay, and vertical-scale selectors.
- Preserves all Phase 2F basemap functionality.

## Phase 2G.1 packaging fix

The Windows build now uses `geotracker_studio_launcher.py` as the PyInstaller
entry point. The launcher imports `geotracker_studio.app` as a package, which
preserves Python package context and prevents the Windows executable error:

`ImportError: attempted relative import with no known parent package`

The build script also removes old `build/` and `dist/` directories before
creating a new release, so a stale executable cannot be mistaken for the
patched build.
