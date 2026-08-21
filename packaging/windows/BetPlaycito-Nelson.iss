#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

#define AppName "BetPlaycito Nelson"
#define AppExeName "BetPlaycito-Nelson.exe"
#define AppPublisher "SirHegel"
#define AppURL "https://github.com/SirHegel/betplaycito-nelson"

[Setup]
AppId={{8A44D37C-39AB-4C7D-8C72-82630ABBF613}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\BetPlaycito Nelson
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist-native
OutputBaseFilename=BetPlaycito-Nelson-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\icons\betplaycito-nelson.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Instalador de {#AppName}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "..\..\dist-native\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
