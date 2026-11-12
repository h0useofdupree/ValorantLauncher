param (
  [string]$Action = "Launch",
  [switch]$WithExitLag,
  [switch]$SkipOverlays,
  [switch]$KeepMedal
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
function Send-Status {
  param(
    [string]$Message, 
    [string]$Color = "White"
  )
  # 1. Print to the terminal (for manual runs)
  Write-Host $Message -ForegroundColor $Color
    
  # 2. Fire the graphical Windows notification
  try {
    New-BurntToastNotification -Text "Valorant Launcher", $Message -ErrorAction SilentlyContinue
  }
  catch {}
}

# =============================================================================
# TEARDOWN SEQUENCE
# =============================================================================
if ($Action -eq "Close") {
  Send-Status -Message "Initiating Teardown Sequence..." -Color Cyan
    
  Write-Host "Closing Valorant and Riot Client..." -ForegroundColor Yellow
  Stop-Process -Name "VALORANT-Win64-Shipping" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "RiotClientServices" -Force -ErrorAction SilentlyContinue
    
  Write-Host "Closing Overwolf and ExitLag..." -ForegroundColor Yellow
  Stop-Process -Name "Overwolf" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "OverwolfLauncher" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "ExitLag" -Force -ErrorAction SilentlyContinue
    
  if (-not $KeepMedal) {
    Write-Host "Closing Medal..." -ForegroundColor Yellow
    Stop-Process -Name "Medal" -Force -ErrorAction SilentlyContinue
  }
  else {
    Write-Host "Keeping Medal running..." -ForegroundColor DarkGray
  }
  
  Write-Host "Restarting RTSS..." -ForegroundColor Green
  # Verify this path matches your installation directory
  Start-Process -FilePath "C:\Program Files (x86)\RivaTuner Statistics Server\RTSS.exe" -ErrorAction SilentlyContinue
    
  Send-Status -Message "Teardown Complete. Background apps closed." -Color Green
  exit 
}

# =============================================================================
# LAUNCH SEQUENCE
# =============================================================================
if ($Action -eq "Launch") {
  Send-Status -Message "Initializing Valorant Environment..." -Color Cyan
  
  # 1. Terminating RTSS to prevent conflicts
  Write-Host "Suspending RTSS to prevent Vanguard conflicts..." -ForegroundColor Yellow
  Stop-Process -Name "RTSS" -Force -ErrorAction SilentlyContinue
  Stop-Process -Name "RTSSHooksLoader64" -Force -ErrorAction SilentlyContinue

  # 2. Boot ExitLag
  if ($WithExitLag) {
    if (-not (Get-Process -Name "ExitLag" -ErrorAction SilentlyContinue)) {
      Write-Host "Starting ExitLag..." -ForegroundColor Green
      Start-Process -FilePath "C:\Program Files\ExitLag\ExitLag.exe"
      Start-Sleep -Seconds 3
    }
    else {
      Write-Host "ExitLag is already running." -ForegroundColor DarkGray
    }
  }

  # 3. Launch background overlays
  if (-not $SkipOverlays) {
    Write-Host "Starting Medal & Overwolf's Valorant Tracker..." -ForegroundColor Green
    Start-Process -FilePath "$env:LOCALAPPDATA\Medal\Medal.exe" -ArgumentList "--hidden"
    Start-Process -FilePath "${env:ProgramFiles(x86)}\Overwolf\OverwolfLauncher.exe" -ArgumentList "-launchapp ipmlnnogholfmdmenfijjifldcpjoecappfccceh -from-desktop"
    Start-Sleep -Seconds 3
  }
  else {
    Write-Host "Skipping background overlays..." -ForegroundColor DarkGray
  }

  # 4. Clean up hanging Riot Client
  Stop-Process -Name "RiotClientServices" -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1

  # 5. Launch Riot Client
  Send-Status -Message "Launching Riot Client. Click 'Play' when ready." -Color Yellow
  Start-Process -FilePath "C:\Riot Games\Riot Client\RiotClientServices.exe" -ArgumentList "--launch-product=valorant --launch-patchline=live" -WorkingDirectory "C:\Riot Games\Riot Client"
}