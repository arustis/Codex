# Prueba del instalador en un runner Windows: instala, verifica acceso directo y abre la GUI.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$installer = @(Get-ChildItem "$projectRoot/dist/installer/*-Setup-*.exe")
if ($installer.Count -ne 1) { throw "Se esperaba un instalador, se encontraron $($installer.Count)." }
$installDir = Join-Path $env:RUNNER_TEMP "Tarjetas-y-Etiquetas-smoke"
$install = Start-Process -FilePath $installer[0].FullName -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=`"$installDir`""
) -PassThru -Wait
if ($install.ExitCode -ne 0) { throw "Fallo de instalacion: $($install.ExitCode)." }
$exe = Join-Path $installDir "TarjetasYEtiquetas.exe"
if (!(Test-Path $exe)) { throw "No se instalo el ejecutable." }
$shortcutPath = Join-Path ([Environment]::GetFolderPath("CommonDesktopDirectory")) "Tarjetas y Etiquetas.lnk"
if (!(Test-Path $shortcutPath)) { throw "No se creo el acceso directo del escritorio." }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
if ($shortcut.TargetPath -ne $exe) { throw "El acceso directo no apunta al ejecutable instalado." }
# Probar desde una carpeta ajena para detectar dependencias de rutas del proyecto.
$app = Start-Process -FilePath $shortcut.TargetPath -ArgumentList "--self-test" `
    -WorkingDirectory $env:RUNNER_TEMP -PassThru
if (!$app.WaitForExit(60000)) {
    $app.Kill()
    throw "La prueba del ejecutable supero 60 segundos."
}
if ($app.ExitCode -ne 0) { throw "Fallo del ejecutable instalado: $($app.ExitCode)." }
Write-Host "Instalacion, acceso directo y GUI congelada verificados."
