$InstallDir = "$HOME\AppData\Local\gitx"
$BinPath = "$InstallDir\gitx.py"
$Url = "https://parisius.github.io/gitx/gitx.py"

Write-Host "▸ Installing gitx into $InstallDir"

if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

Write-Host "▸ Downloading gitx.py..."
Invoke-WebRequest -Uri $Url -OutFile $BinPath -UseBasicParsing

Write-Host "`n✔ gitx installed at: $BinPath"

$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentPath -notlike "*$InstallDir*") {
    $NewPath = "$CurrentPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Host "`n▸ Added gitx to PATH."
}

Write-Host ""
Write-Host "Run: gitx help"
Write-Host "Done!"