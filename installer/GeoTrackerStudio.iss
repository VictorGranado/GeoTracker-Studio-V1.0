#define MyAppName "GeoTracker Studio"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "GeoTracker"
#define MyAppExeName "GeoTracker Studio.exe"

[Setup]
AppId={{B60F34F8-6EA8-4CC0-98C9-B3854B883150}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\GeoTracker Studio
DefaultGroupName=GeoTracker Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=GeoTracker Studio v1.0.1 Setup
SetupIconFile=..\assets\geotracker_studio.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\GeoTracker Studio v1.0.1\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GeoTracker Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\GeoTracker Studio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch GeoTracker Studio"; Flags: nowait postinstall skipifsilent
