[Setup]
AppName=Extractor de Seguidores de Instagram
AppVersion=1.0
DefaultDirName={autopf}\DataExtractor
DefaultGroupName=DataExtractor
OutputBaseFilename=Setup_DataExtractor
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\DataExtractor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Extractor de Seguidores"; Filename: "{app}\DataExtractor.exe"
Name: "{autodesktop}\Extractor de Seguidores"; Filename: "{app}\DataExtractor.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Iconos adicionales:"

[Run]
Filename: "{app}\DataExtractor.exe"; Description: "Lanzar Extractor de Seguidores ahora"; Flags: nowait postinstall skipifsilent
