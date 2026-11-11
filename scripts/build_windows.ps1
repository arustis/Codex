param(
    [string]$PythonExe = "python",
    [string]$Compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT") { throw "Este build debe ejecutarse en Windows x64." }
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    & $PythonExe -m PyInstaller --noconfirm --clean --windowed --onedir `
        --name TarjetasYEtiquetas --distpath dist --workpath build/pyinstaller `
        --specpath build --hidden-import win32print --hidden-import hid `
        --hidden-import serial.tools.list_ports main.py
    if ($LASTEXITCODE -ne 0) { throw "Fallo PyInstaller (codigo $LASTEXITCODE)." }
    if (!(Test-Path $Compiler)) { throw "Instalar Inno Setup 6 o indicar -Compiler con la ruta a ISCC.exe." }
    $version = (& $PythonExe -c "from config import APP_VERSION; print(APP_VERSION)").Trim()
    if ($LASTEXITCODE -ne 0) { throw "No se pudo obtener la version." }
    & $Compiler "/DAppVersion=$version" installer/TarjetasYEtiquetas.iss
    if ($LASTEXITCODE -ne 0) { throw "Fallo Inno Setup (codigo $LASTEXITCODE)." }
    Write-Host "Instalador: dist/installer/TarjetasYEtiquetas-Setup-$version.exe"
} finally {
    Pop-Location
}
