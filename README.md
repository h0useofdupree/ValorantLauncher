# Valorant Launcher for Flow Launcher

![GitHub Release](https://img.shields.io/github/v/release/h0useofdupree/ValorantLauncher?style=flat-square&label=version&color=ff4655)
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d4?style=flat-square&logo=windows)
![Python](https://img.shields.io/badge/python-3.8%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![PowerShell](https://img.shields.io/badge/powershell-5.1%20%7C%207%2B-5391fe?style=flat-square&logo=powershell&logoColor=white)
![Flow Launcher](https://img.shields.io/badge/Flow%20Launcher-Plugin-f88a36?style=flat-square)

A context-aware Flow Launcher plugin that automates the full lifecycle of a Valorant gaming session. It orchestrates network routing tools, recording software, in-game stat overlays, and conflicting OSD hooks on startup, and tears them all down cleanly with a single command when the session ends.

## Use Cases

Launching Valorant alongside third-party utilities normally involves manual startup ordering, intrusive desktop popups, and lingering background processes after quitting. This plugin solves several specific pain points:

- **Vanguard / OSD Conflict Prevention:** RivaTuner Statistics Server (`RTSS.exe`) and `RTSSHooksLoader64.exe` frequently clash with Riot Vanguard or cause frame-pacing issues. The plugin automatically suspends RTSS prior to launch and restores it upon teardown.
- **Selective Environment Booting:** Depending on whether you are playing competitive matches or hopping into the range, you can launch the full stack (ExitLag, Medal, Overwolf/Valorant Tracker, and Riot Client), skip overlays, or launch the bare game client.
- **Valorant Tracker Popup Suppression:** The free tier of Valorant Tracker (Overwolf) forces two desktop companion windows open—once when Overwolf starts, and again when Valorant boots. This plugin launches Overwolf silently into the system tray and uses native Win32 API calls to cloak and banish the desktop popup window while keeping the in-game `Alt+T` DirectX overlay functional.
- **Hardware-Adaptive Menus:** Options dynamically adapt to the host machine. If ExitLag, Medal, or RTSS are not installed on a system, those specific menu entries and teardown actions are automatically omitted.
- **Single-Click Teardown ("Full Nuke"):** Closing Valorant normally leaves `RiotClientServices`, `Overwolf`, `OverwolfBrowser`, `ExitLag`, and `Medal` running in the background. The teardown sequence terminates the entire tree and restarts RTSS. This also fixes problems when closing `Valorant.exe` via the in-game button, which often results in system lag.

## Prerequisites

- [Flow Launcher](https://www.flowlauncher.com/) (with Python environment initialized)
- [Git for Windows](https://git-scm.com/download/win) (required for installation and in-app self-updates)
- **Optional:** [BurntToast](https://github.com/Windos/BurntToast) PowerShell module for rich Windows 10/11 toast notifications (falls back to native `.NET` tray notifications if absent):

```pwsh
Install-Module -Name BurntToast -Scope CurrentUser
```

## Installation

1. Open PowerShell and navigate to your Flow Launcher `Plugins` directory:

```pwsh
cd "$env:APPDATA\FlowLauncher\Plugins"
```

2. Clone the repository into a `ValorantLauncher` folder:

```sh
git clone https://github.com/h0useofdupree/ValorantLauncher.git ValorantLauncher
```

3. Restart Flow Launcher (or run the `Reload Plugin Data` command inside Flow Launcher) to register the plugin.

## Usage

Open Flow Launcher and type the action keyword `vl`.

> [!TIP]
> You can change the default `vl` keyword anytime in the plugin settings.

### Context-Aware Main Menu

The main menu dynamically reorders itself based on whether `VALORANT-Win64-Shipping.exe` or `RiotClientServices.exe` is currently active in memory:

- **When Idle:**
  - `Launch Options...` (`vl launch`): Opens the launch mode selector.
  - `Close Options...` (`vl close`): Opens the manual teardown selector.
  - `Medal & Clips...` (`vl medal`): Appears if Medal is installed; opens the (initially) hidden Medal UI or opens your configured recordings folder in Windows Explorer.
  - `Update Plugin`: Pulls the latest release tag from GitHub. Displays an `Update Available!` banner when a newer remote tag is detected.

    > [!NOTE]
    > The plugin checks for updates automatically every 4 hours

- **When Session is Active:**
  - `Close Options... [VALORANT RUNNING]` floats to the first position.
  - `Quick Close (Full Nuke)` (or `Keep Medal`, depending on user settings) appears at the second position for immediate single-keystroke teardown.

### Submenus

- **`vl launch`**
  - **Launch with ExitLag:** Suspends RTSS, starts ExitLag asynchronously, boots Medal (`--hidden`) and Overwolf (`-overwolfsilent -silent`), and launches the Riot Client into the Valorant tab.
    > [!NOTE]
    > The command
    >
    > ```pwsh
    > RiotClientServices.exe --launch-product=valorant --launch-patchline=live
    > ```
    >
    > used to allow the plugin to directly initiate the launch of Valorant itself from the launcher, but this seems to have stopped working. I am working on either getting that to work again or find a simple alternative solution.
  - **Launch without ExitLag / Standard:** Same as above, omitting ExitLag.
  - **Launch (No Overlays):** Suspends RTSS, starts ExitLag (if installed), skips Medal and Overwolf, and starts Valorant.
  - **Launch Minimal (Game Only):** Starts only the Riot Client and suspends RTSS.
- **`vl close`**
  - **Close All (Full Nuke):** Force-stops Valorant, Riot Client, Overwolf, ExitLag, and Medal, then restarts RTSS.
  - **Close Game (Keep Medal):** Performs a full teardown while leaving Medal active so you can review or upload clips after a session.
- **`vl medal`**
  - **Open Medal Window:** Brings the hidden Medal client window to the foreground.
  - **Open Medal Clips Folder:** Parses `%APPDATA%\Medal\store\settings.json` to locate your active recording directory (or uses your custom path override) and opens it in Explorer.

## Configuration

The plugin integrates with Flow Launcher's native GUI settings via `SettingsTemplate.yaml`. Open **Flow Launcher Settings -> Plugins -> Valorant Launcher** to configure:

- **Preferred Launch Mode:** Pins your default launch configuration (`With ExitLag`, `Standard (No ExitLag)`, `No Overlays`, or `Minimal`) to the top of the `vl launch` submenu.
- **Preferred Close / Quick Teardown Mode:** Sets whether `Quick Close` and the primary close action default to `Full Nuke (Kill All)` or `Keep Medal Open`.
- **Suppress Valorant Tracker Startup Popup:** Enables silent Overwolf startup and Win32 window cloaking for the Valorant Tracker desktop window.
- **Auto-Teardown When Valorant Closes:** Keeps a lightweight background watcher alive that automatically triggers your teardown sequence the moment `VALORANT-Win64-Shipping.exe` exits.
- **Custom Medal Clips Folder:** Optional directory path override for the `Open Medal Clips Folder` command.

### Note for Tiling Window Manager Users (GlazeWM / Komorebi)

If you use a tiling window manager that automatically centers or forces floating windows to the foreground, add `Overwolf` and `Valorant Tracker` to your WM's `ignore` rules. This prevents the window manager from intercepting and rendering the raw WinForms container during the split-second before the plugin's Win32 hook cloaks it.

Most window managers should allow rules that specifiy process name and/or window title.

## How It Works (Architecture)

The plugin splits responsibilities across three layers to keep the Flow Launcher UI responsive (less than 1ms query execution) while handling long-running process management in the background.

### 1. Frontend & Query Engine (`main.py`)

- **Sub-Millisecond Process Detection (`ctypes`):** Spawning `tasklist.exe` or `powershell.exe` on every keystroke introduces noticeable UI lag. Instead, `main.py` calls the Windows kernel API `CreateToolhelp32Snapshot`, `Process32FirstW`, and `Process32NextW` directly via `ctypes` to walk the active process table in memory in under a millisecond.
- **Score-Enforced Ordering:** Flow Launcher normally reorders plugin results based on historical click frequency (`UserSelectedRecord.json`). To guarantee deterministic menu ordering as session states change, `main.py` assigns descending `Score` weights (`10000`, `9000`, `8000`...) to every returned item.
- **Non-Blocking Update Checks:** To check for remote GitHub updates without blocking the UI thread on network I/O, `main.py` reads a local `.update_cache.json` file. When the cache expires (every 4 hours), it spawns a detached background process running `git ls-remote --tags origin` to refresh the cache asynchronously.

### 2. Backend Orchestrator (`runner.ps1`)

- **Registry & Environment Discovery:** Rather than relying on hardcoded drive letters, `runner.ps1` resolves the Riot Client installation path dynamically from `HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live`, and checks standard 64-bit, 32-bit, and `LocalAppData` paths for companion tools.
- **Smart Overlay Polling:** Instead of using fixed `Start-Sleep` delays when booting Medal and Overwolf, the script polls the process table at `100ms` intervals (with a 3-second ceiling) and launches the Riot Client as soon as the overlay processes initialize.
- **Credential-Free HTTPS Self-Updater:** Because Flow Launcher executes `runner.ps1` in a hidden, non-interactive window (`CREATE_NO_WINDOW`), SSH remotes protected by passphrases or isolated SSH agents would fail during `git pull`. The `Update` action dynamically rewrites `git@github.com:` URLs to `[https://github.com/](https://github.com/)` via inline Git config flags (`-c url.[https://github.com/.insteadOf=git@github.com](https://github.com/.insteadOf=git@github.com):`) to pull public tags anonymously.

### 3. Win32 Window Cloaking (`Win32Window.cs`)

Simply killing or closing the Valorant Tracker desktop popup (`OverwolfBrowser.exe` / `Overwolf.exe`) can unload the in-game overlay hook, and calling `ShowWindow(hWnd, SW_HIDE)` alone fails because Overwolf calls `ShowWindow(SW_SHOW)` again once the internal Chromium view finishes loading.

To solve this, `runner.ps1` compiles `Win32Window.cs` at runtime via `Add-Type` and polls top-level process windows via `EnumWindows`:

1. As soon as Overwolf allocates the `WindowsForms10.Window` container or sets the window title to `Valorant Tracker`, `CloakAndHide()` modifies the window's extended styles (`SetWindowLong` with `WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE`).
2. `SetLayeredWindowAttributes` sets the window's alpha opacity to `0` (completely transparent), and `SetWindowPos` moves its coordinates off-screen to `(-32000, -32000)`.
3. Even when Overwolf subsequently forces the window visible, Windows renders a zero-opacity window off-screen that never flashes on the monitor, never appears in `Alt+Tab`, and never steals focus from the game.
