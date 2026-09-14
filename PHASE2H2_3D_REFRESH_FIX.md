# GeoTracker Studio Phase 2H2 — 3D Refresh Fix

This patch fixes a real-session import refresh issue where the Overview and 2D Map could update, but later pages such as Waypoints & Events and 3D Route could keep showing the bundled demo session.

Changes:

- Session page updates are now isolated, so one page cannot stop the rest of the UI from refreshing.
- The selected sample controller is cleared before page refresh.
- The sidebar session label is updated immediately after a session is parsed.
- The 3D Route page clears old OpenGL route items, waypoint markers, grid, axis, selected sample marker, and basemap before binding a new session.
- Opening the 3D Route page forces it to bind to the current in-memory session, which prevents stale demo data from remaining visible.

Recommended validation:

1. Run the patched source or rebuild the installer.
2. Open `GeoTracker_Studio_ImportReady_v6_exact_schema/SESSION_07_2026-09-12_163417_16019m`.
3. Check that Overview shows 87 samples and about 16019 m.
4. Check that 2D Map shows 87 valid GPS points.
5. Check that 3D Route shows 87 GPS/altitude points and the large real route footprint, not the 293-point demo route.
