param (
  [string]$Action = "Launch",
  [switch]$WithExitLag,
  [switch]$SkipOverlays,
  [switch]$KeepMedal

)

# =============================================================================
# DYNAMIC PATH RESOLUTION (Works across C:\, D:\, Win10 & Win11)
# =============================================================================
# 1. Auto-detect Riot Client from Windows Registry, fallback to C:\Riot Games
$RiotReg = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live" -ErrorAction SilentlyContinue
if ($RiotReg -and $RiotReg.UninstallString) {
  if ($RiotReg.UninstallString -match '"([^"]+RiotClientServices\.exe)"') {
    $RiotClientExe = $Matches[1]
    $RiotClientDir = Split-Path $RiotClientExe -Parent
  }
}
if (-not $RiotClientExe -or -not (Test-Path $RiotClientExe)) {
  $RiotClientDir = "C:\Riot Games\Riot Client"
  $RiotClientExe = "$RiotClientDir\RiotClientServices.exe"
}

$MedalExe = "$env:LOCALAPPDATA\Medal\Medal.exe"
$OverwolfExe = "${env:ProgramFiles(x86)}\Overwolf\OverwolfLauncher.exe"
$RtssExe = "${env:ProgramFiles(x86)}\RivaTuner Statistics Server\RTSS.exe"

$ExitLagCandidates = @(
  "$env:ProgramW6432\ExitLag\ExitLag.exe",
  "${env:ProgramFiles(x86)}\ExitLag\ExitLag.exe",
  "$env:LOCALAPPDATA\ExitLag\ExitLag.exe"
)
$ExitLagExe = $ExitLagCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

# Retain whether RTSS was running before we killed it, or if it's installed
$HasRtss = Test-Path $RtssExe

# =============================================================================
# NOTIFICATION ENGINE (BurntToast with Native Win10/11 Fallback)
# =============================================================================
function Send-Status {
  param([string]$Message, [string]$Color = "White")
  Write-Host $Message -ForegroundColor $Color

  if (Get-Module -ListAvailable -Name BurntToast) {
    try {
      Import-Module BurntToast -ErrorAction Stop
      New-BurntToastNotification -Text "Valorant Launcher", $Message -AppLogo "$PSScriptRoot\icons\val-icon.png" -ErrorAction Stop
      return
    }
    catch {
      Write-Host "BurntToast failed: $_" -ForegroundColor DarkGray
    }
  }

  # Native zero-dependency fallback for notifications
  try {
    Add-Type -AssemblyName System.Windows.Forms
    $balloon = New-Object System.Windows.Forms.NotifyIcon
    $balloon.Icon = [System.Drawing.SystemIcons]::Information
    $balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
    $balloon.BalloonTipTitle = "Valorant Launcher"
    $balloon.BalloonTipText = $Message
    $balloon.Visible = $true
    $balloon.ShowBalloonTip(3000)
    Start-Sleep -Milliseconds 500
    $balloon.Dispose()
  }
  catch {}
}

# =============================================================================
# MEDAL & CLIPS UTILITIES
# =============================================================================
if ($Action -eq "OpenMedal") {
  if (Test-Path $MedalExe) {
    Start-Process -FilePath $MedalExe
  }
  exit
}

if ($Action -eq "OpenClips") {
  $clipsDir = $null
  $medalSettings = "$env:APPDATA\Medal\store\settings.json"

  if (Test-Path $medalSettings) {
    try {
      $cfg = Get-Content $medalSettings -Raw | ConvertFrom-Json
      if ($cfg.recorder.clipFolder -and (Test-Path $cfg.recorder.clipFolder)) {
        $clipsDir = $cfg.recorder.clipFolder + "\clips\Valorant"
      }
    }
    catch {}
  }

  if (-not $clipsDir) {
    $fallbacks = @(
      "C:\Medal\Clips",
      "D:\Medal\Clips",
      "$HOME\Videos\Medal",
      "$HOME\Videos"
    )
    $clipsDir = $fallbacks | Where-Object { Test-Path $_ } | Select-Object -First 1
  }

  if ($clipsDir) {
    Start-Process "explorer.exe" -ArgumentList "`"$clipsDir`""
  }
  else {
    Send-Status -Message "Could not locate Medal clips directory." -Color Red
  }
  exit
}

# =============================================================================
# SELF-UPDATE SEQUENCE (GIT PULL)
# =============================================================================
if ($Action -eq "Update") {
  Set-Location $PSScriptRoot
  $oldVer = (Get-Content "$PSScriptRoot\plugin.json" -Raw | ConvertFrom-Json).Version

  $gitOutput = git -c "url.https://github.com/.insteadOf=git@github.com:" pull --tags 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0) {
    $newVer = (Get-Content "$PSScriptRoot\plugin.json" -Raw | ConvertFrom-Json).Version

    # Clear cached update check file for immediate UI refresh
    Remove-Item "$PSScriptRoot\.update_cache.json" -Force -ErrorAction SilentlyContinue

    if ($oldVer -ne $newVer) {
      Send-Status -Message "Updated from v$oldVer to v$newVer!" -Color Green
    }
    else {
      Send-Status -Message "Already up to date (v$newVer)." -Color Cyan
    }
  }
  else {
    Send-Status -Message "Git update failed: $gitOutput" -Color Red
  }
  exit
}

# =============================================================================
# TEARDOWN SEQUENCE
# =============================================================================
if ($Action -eq "Close") {
  Send-Status -Message "Initiating Teardown Sequence..." -Color Cyan

  Stop-Process -Name "VALORANT-Win64-Shipping" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "RiotClientServices" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "Overwolf" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "OverwolfLauncher" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "ExitLag" -Force -ErrorAction SilentlyContinue

  if (-not $KeepMedal) {
    Stop-Process -Name "Medal" -Force -ErrorAction SilentlyContinue
  }

  if ($HasRtss -and -not (Get-Process -Name "RTSS" -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $RtssExe -ErrorAction SilentlyContinue
  }

  Send-Status -Message "Teardown Complete. Background apps closed." -Color Green
  exit
}

# =============================================================================
# LAUNCH SEQUENCE
# =============================================================================
if ($Action -eq "Launch") {
  Send-Status -Message "Initializing Valorant Environment..." -Color Cyan

  # 1. Suspend RTSS if installed/running
  if ($HasRtss) {
    Stop-Process -Name "RTSS" -Force -ErrorAction SilentlyContinue
    Stop-Process -Name "RTSSHooksLoader64" -Force -ErrorAction SilentlyContinue
  }

  # 2. Boot ExitLag (if requested & installed)
  if ($WithExitLag -and (Test-Path $ExitLagExe)) {
    if (-not (Get-Process -Name "ExitLag" -ErrorAction SilentlyContinue)) {
      Start-Process -FilePath $ExitLagExe
    }
  }

  # 3. Launch background overlays
  if (-not $SkipOverlays) {
    $waitTargets = @()

    if ((Test-Path $MedalExe) -and -not (Get-Process -Name "Medal" -ErrorAction SilentlyContinue)) {
      Start-Process -FilePath $MedalExe -ArgumentList "--hidden"
      $waitTargets += "Medal"
    }
    if ((Test-Path $OverwolfExe) -and -not (Get-Process -Name "Overwolf" -ErrorAction SilentlyContinue)) {
      Start-Process -FilePath $OverwolfExe -ArgumentList "-launchapp ipmlnnogholfmdmenfijjifldcpjoecappfccceh -from-desktop"
      $waitTargets += "Overwolf"
    }

    if ($waitTargets.Count -gt 0) {
      $elapsed = 0
      while ($elapsed -lt 3000) {
        $allReady = $true
        foreach ($proc in $waitTargets) {
          if (-not (Get-Process -Name $proc -ErrorAction SilentlyContinue)) {
            $allReady = $false
            break
          }
        }
        if ($allReady) { break }
        Start-Sleep -Milliseconds 100
        $elapsed += 100
      }
    }
  }

  # 4. Clean up & Launch Riot Client
  if (Get-Process -Name "RiotClientServices" -ErrorAction SilentlyContinue) {
    Stop-Process -Name "RiotClientServices" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
  }

  if (Test-Path $RiotClientExe) {
    Send-Status -Message "Launching Riot Client. Click 'Play' when ready." -Color Yellow
    Start-Process -FilePath $RiotClientExe -ArgumentList "--launch-product=valorant --launch-patchline=live" -WorkingDirectory $RiotClientDir
  }
  else {
    Send-Status -Message "Error: Riot Client not found at $RiotClientExe" -Color Red
  }
}
