[Setup]
AppName=RasFocus Pro Max
AppVersion=2.0.1
AppPublisher=RasFocus Inc.
DefaultDirName={autopf}\RasFocus
DisableProgramGroupPage=yes
OutputBaseFilename=RasFocus_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\RasFocus_Pro_Max.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\RasFocus"; Filename: "{app}\RasFocus_Pro_Max.exe"
Name: "{autodesktop}\RasFocus"; Filename: "{app}\RasFocus_Pro_Max.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RasFocus_Pro_Max.exe"; Description: "{cm:LaunchProgram,RasFocus}"; Flags: nowait postinstall skipifsilent
