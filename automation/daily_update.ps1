param([switch]$NoPreview)

$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$siteRoot = Split-Path -Parent $PSScriptRoot
$parentRoot = Split-Path -Parent $siteRoot
$logPath = Join-Path $siteRoot 'update-log.txt'
$imagePath = Join-Path $siteRoot 'public\image'
$keyPath = Join-Path $siteRoot '.private\API KEY.txt'

Set-Location -LiteralPath $siteRoot
Set-Content -LiteralPath $logPath -Value ("LGK update started: " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -Encoding UTF8

function Get-Workbook {
    param([string]$Directory)
    return Get-ChildItem -LiteralPath $Directory -Filter '*.xlsx' -File -ErrorAction SilentlyContinue |
        Where-Object { -not $_.Name.StartsWith('~$') } |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
}

function Invoke-Checked {
    param([scriptblock]$Action, [string]$FailureMessage)
    & $Action 2>&1 | Tee-Object -FilePath $logPath -Append | ForEach-Object { Write-Host $_ }
    $commandExitCode = $LASTEXITCODE
    if ($commandExitCode -ne 0) {
        throw "$FailureMessage (exit code $commandExitCode)"
    }
}

try {
    Write-Host '========================================'
    Write-Host '  RPA finished: dedupe - tag - build'
    Write-Host '========================================'
    Write-Host ''

    $currentWorkbook = Get-Workbook -Directory $siteRoot
    $legacyWorkbook = Get-Workbook -Directory $parentRoot
    if ($legacyWorkbook -and (-not $currentWorkbook -or $legacyWorkbook.LastWriteTimeUtc -gt $currentWorkbook.LastWriteTimeUtc)) {
        if (-not $currentWorkbook) {
            throw 'The workbook is missing from lgk. Restore it before updating.'
        }
        Write-Host 'A newer workbook was found in the parent folder. Copying it into lgk...'
        try {
            Copy-Item -LiteralPath $legacyWorkbook.FullName -Destination $currentWorkbook.FullName -Force
            $currentWorkbook = Get-Item -LiteralPath $currentWorkbook.FullName
        } catch {
            throw 'Cannot read the newer workbook. Close Excel, wait for the RPA write to finish, and try again.'
        }
    }

    if (-not $currentWorkbook) { throw 'The workbook is missing from the lgk folder.' }
    if (-not (Test-Path -LiteralPath $imagePath)) { throw 'The public/image folder is missing.' }
    if (-not (Test-Path -LiteralPath $keyPath)) { throw 'The .private/API KEY.txt file is missing.' }

    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        Invoke-Checked { & $pythonLauncher.Source -3 (Join-Path $PSScriptRoot 'update_website.py') } 'Image processing failed'
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) { throw 'Python 3 was not found.' }
        Invoke-Checked { & $python.Source (Join-Path $PSScriptRoot 'update_website.py') } 'Image processing failed'
    }

    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) { throw 'Node.js and npm were not found. Install Node.js 22.' }
    if (-not (Test-Path -LiteralPath (Join-Path $siteRoot 'node_modules'))) {
        Write-Host 'First run: installing website dependencies...'
        Invoke-Checked { & $npm.Source ci } 'Dependency installation failed'
    }

    Write-Host 'Creating responsive images and building the website...'
    Invoke-Checked { & $npm.Source run build } 'Website build failed'
    Invoke-Checked { & $npm.Source run check } 'Website integrity check failed'

    Write-Host ''
    Write-Host '[DONE] Images, tags, responsive assets, and website build are current.' -ForegroundColor Green
    Write-Host "Log: $logPath"
    if (-not $NoPreview) {
        $previewUrl = 'http://127.0.0.1:5178/'
        $previewIsRunning = $false
        try {
            $previewResponse = Invoke-WebRequest -Uri $previewUrl -UseBasicParsing -TimeoutSec 1
            $previewIsRunning = $previewResponse.StatusCode -eq 200
        } catch {}
        if ($previewIsRunning) {
            Write-Host 'The preview is already running. Opening it in the browser.'
            Start-Process $previewUrl
        } else {
            Write-Host 'Starting the local preview in a separate window.'
            Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', 'npm run dev -- --open --port 5178 --strictPort' -WorkingDirectory $siteRoot
        }
    }
} catch {
    Write-Host ''
    Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Log: $logPath"
    Add-Content -LiteralPath $logPath -Value ("FAILED: " + $_.Exception.Message)
    if (-not $NoPreview) { Read-Host 'Press Enter to close this window' | Out-Null }
    exit 1
}
