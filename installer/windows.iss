#define AppName "Container Workbench"
#define AppVersion "0.1.0"
#define AppPublisher "Container Workbench"

[Setup]
AppId={{7D4AA871-8268-4FC3-B69B-44E81E3384DC}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\Container Workbench
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename=Container-Workbench-Setup
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\Container Workbench.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\Container Workbench\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Container Workbench.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Container Workbench.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "바탕 화면 바로 가기 만들기"; GroupDescription: "추가 아이콘:"; Flags: unchecked

[Run]
Filename: "{app}\Container Workbench.exe"; Description: "{#AppName} 실행"; Flags: postinstall nowait skipifsilent
