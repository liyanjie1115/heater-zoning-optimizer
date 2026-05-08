#define MyAppName "Heater Zoning Optimizer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Heater Zoning Optimizer"
#define MyAppExeName "heater-zoning-optimizer.exe"
#define MyAppAssocName MyAppName + " Desktop"
#define MyReleaseDir "..\release\heater-zoning-optimizer-v1.0.0-windows"
#define MyOutputDir "..\release\installer"
#define MyIconFile "..\build_assets\app_icon.ico"

[Setup]
AppId={{0A5B3C8B-59A2-40D7-9F42-0F3C55D2A011}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile={#MyReleaseDir}\README.txt
OutputDir={#MyOutputDir}
OutputBaseFilename=heater-zoning-optimizer-setup-v1.0.0
SetupIconFile={#MyIconFile}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl,{#SourcePath}\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional tasks:"; Flags: unchecked

[Files]
Source: "{#MyReleaseDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
