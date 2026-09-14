# GeoTracker Studio v1.0.1 — Release Checklist

- [ ] `python -m pytest -q` passes.
- [ ] Source build launches with `python -m geotracker_studio.app`.
- [ ] `Build_Windows.ps1` produces `dist\GeoTracker Studio v1.0.1\GeoTracker Studio.exe`.
- [ ] Packaged executable launches without a console or import errors.
- [ ] Demo data is visibly marked as DEMO DATA.
- [ ] File → Open session and Ctrl+O work.
- [ ] About dialog opens from Help.
- [ ] 2D map and OpenStreetMap overlay render.
- [ ] Data graphs synchronize selections.
- [ ] 3D route and basemap plane render.
- [ ] KML and GPX exports open in external tools.
- [ ] `Build_Installer.ps1` creates `GeoTracker Studio v1.0.1 Setup.exe` when Inno Setup 6 is available.
- [ ] Installer installs, launches, and uninstalls successfully.
