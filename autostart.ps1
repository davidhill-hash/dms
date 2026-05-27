param([ValidateSet('enable','disable')][string]$Action = 'enable')

$ErrorActionPreference = 'Stop'
$startup = [Environment]::GetFolderPath('Startup')
$link    = Join-Path $startup 'Bolt.lnk'

if ($Action -eq 'disable') {
    if (Test-Path $link) {
        Remove-Item $link
        Write-Host 'Bolt will no longer start automatically.'
    } else {
        Write-Host 'Bolt autostart was not enabled.'
    }
    return
}

# locate pythonw.exe (preferred: no console window)
$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) {
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($py) { $pyw = Join-Path (Split-Path $py) 'pythonw.exe' }
}
if (-not $pyw -or -not (Test-Path $pyw)) {
    Write-Host 'Could not find pythonw.exe. Please install Python from python.org first.'
    exit 1
}

$target = Join-Path $PSScriptRoot 'bolt.pyw'

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($link)
$sc.TargetPath       = $pyw
$sc.Arguments        = '"' + $target + '"'
$sc.WorkingDirectory = $PSScriptRoot
$sc.IconLocation     = $pyw
$sc.Save()

Write-Host 'Done! Bolt will now start automatically when you log in.'
Write-Host 'Starting him now...'
Start-Process -FilePath $pyw -ArgumentList ('"' + $target + '"') -WorkingDirectory $PSScriptRoot
