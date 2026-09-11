from pathlib import Path

from geotracker_studio.resources import resource_path


ROOT = Path(__file__).resolve().parents[1]


def test_brand_assets_exist():
    assert (ROOT / 'assets' / 'geotracker_studio.png').is_file()
    assert (ROOT / 'assets' / 'geotracker_studio.ico').is_file()
    assert (ROOT / 'assets' / 'geotracker_mark.svg').is_file()


def test_release_build_files_exist():
    assert (ROOT / 'GeoTrackerStudio.spec').is_file()
    assert (ROOT / 'Build_Windows.ps1').is_file()
    assert (ROOT / 'windows_version_info.txt').is_file()


def test_resource_path_source_mode():
    assert resource_path('assets/geotracker_studio.png').is_file()


def test_pyinstaller_uses_package_aware_launcher():
    launcher = ROOT / 'geotracker_studio_launcher.py'
    spec = (ROOT / 'GeoTrackerStudio.spec').read_text(encoding='utf-8')
    assert launcher.is_file()
    assert 'from geotracker_studio.app import main' in launcher.read_text(encoding='utf-8')
    assert "['geotracker_studio_launcher.py']" in spec
    assert "['geotracker_studio/app.py']" not in spec


def test_phase2h_visual_assets_exist():
    for name in [
        'nav_overview.svg', 'nav_map.svg', 'nav_graph.svg',
        'nav_waypoint.svg', 'nav_3d.svg', 'nav_export.svg',
    ]:
        assert (ROOT / 'assets' / name).is_file()


def test_installer_build_files_exist():
    assert (ROOT / 'installer' / 'GeoTrackerStudio.iss').is_file()
    assert (ROOT / 'Build_Installer.ps1').is_file()
    assert (ROOT / 'Build_Release.ps1').is_file()


def test_release_docs_exist():
    assert (ROOT / 'USER_GUIDE.md').is_file()
    assert (ROOT / 'RELEASE_CHECKLIST.md').is_file()


def test_release_polish_features_are_wired():
    source = (ROOT / 'geotracker_studio' / 'gui_main.py').read_text(encoding='utf-8')
    assert 'AboutDialog' in source
    assert "DEMO DATA" in source
    assert "Open session…" in source
    assert "nav_overview.svg" in source
