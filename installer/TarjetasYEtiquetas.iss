#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

[Setup]
AppId={{814CDB65-483D-4415-9082-A3D33450C005}
AppName=Tarjetas y Etiquetas
AppVersion={#AppVersion}
AppPublisher=Tarjetas y Etiquetas
DefaultDirName={autopf}\Tarjetas y Etiquetas
DefaultGroupName=Tarjetas y Etiquetas
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=TarjetasYEtiquetas-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\TarjetasYEtiquetas.exe
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; Flags: checkedonce

[Files]
Source: "..\dist\TarjetasYEtiquetas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Tarjetas y Etiquetas"; Filename: "{app}\TarjetasYEtiquetas.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Tarjetas y Etiquetas"; Filename: "{app}\TarjetasYEtiquetas.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\TarjetasYEtiquetas.exe"; Description: "Abrir Tarjetas y Etiquetas"; Flags: nowait postinstall skipifsilent runasoriginaluser
