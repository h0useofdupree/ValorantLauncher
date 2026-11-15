import sys
import os
import json
import time
import ctypes
from ctypes import wintypes
import shutil
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

from flowlauncher import FlowLauncher

CREATE_NO_WINDOW = 0x08000000
TH32CS_SNAPPROCESS = 0x00000002
UPDATE_CHECK_INTERVAL = 14400  # 4 hours


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class ValorantPlugin(FlowLauncher):
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)

        self.version = "Unknown"
        self.plugin_name = "ValorantLauncher"
        try:
            with open(
                os.path.join(self.base_dir, "plugin.json"), "r", encoding="utf-8-sig"
            ) as f:
                meta = json.load(f)
                self.version = meta.get("Version", "Unknown")
                self.plugin_name = meta.get("Name", "ValorantLauncher")
        except Exception as e:
            pass

        self.settings = self.load_settings()

        prog_64 = os.environ.get("ProgramW6432", r"C:\Program Files")
        prog_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")

        exitlag_paths = [
            os.path.join(prog_64, "ExitLag", "ExitLag.exe"),
            os.path.join(prog_x86, "ExitLag", "ExitLag.exe"),
            os.path.join(local_app, "ExitLag", "ExitLag.exe"),
        ]
        self.has_exitlag = any(os.path.exists(p) for p in exitlag_paths)

        self.has_rtss = os.path.exists(
            os.path.join(prog_x86, "RivaTuner Statistics Server", "RTSS.exe")
        )
        self.has_medal = os.path.exists(os.path.join(local_app, "Medal", "Medal.exe"))

        super().__init__()

    def load_settings(self):
        """Read Flow Launcher's native Settings.json for this plugin."""
        defaults = {
            "default_launch_mode": "With ExitLag",
            "default_close_mode": "Full Nuke (Kill All)",
            "suppress_tracker_window": True,
            "auto_teardown_on_exit": False,
            "custom_clips_path": "",
        }

        appdata = os.environ.get("APPDATA", "")
        candidates = [
            os.path.join(
                appdata,
                "FlowLauncher",
                "Settings",
                "Plugins",
                self.plugin_name,
                "Settings.json",
            ),
            os.path.join(
                appdata,
                "FlowLauncher",
                "Settings",
                "Plugins",
                "ValorantLauncher",
                "Settings.json",
            ),
            os.path.abspath(
                os.path.join(
                    self.base_dir,
                    "..",
                    "..",
                    "Settings",
                    "Plugins",
                    self.plugin_name,
                    "Settings.json",
                )
            ),
        ]

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        user_cfg = json.load(f)
                        defaults.update(user_cfg)
                    break
                except Exception as e:
                    pass
        return defaults

    def _ranked(self, items):
        """Force Flow Launcher to respect exact list order over usage history."""
        for i, item in enumerate(items):
            item["Score"] = 10000 - (i * 1000)
        return items

    def get_session_state(self):
        """Sub-millisecond Win32 kernel snapshot to check running Riot/Valorant processes."""
        val_running = False
        riot_running = False

        kernel32 = ctypes.windll.kernel32
        h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h_snap == -1:
            return val_running, riot_running

        try:
            pe = PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            if kernel32.Process32FirstW(h_snap, ctypes.byref(pe)):
                while True:
                    exe = pe.szExeFile.lower()
                    if exe == "valorant-win64-shipping.exe":
                        val_running = True
                        break  # Highest priority state found, no need to scan further
                    elif exe == "riotclientservices.exe":
                        riot_running = True
                    if not kernel32.Process32NextW(h_snap, ctypes.byref(pe)):
                        break
        finally:
            kernel32.CloseHandle(h_snap)

        return val_running, riot_running

    def _parse_ver(self, v_str):
        try:
            return tuple(int(x) for x in v_str.lstrip("v").split("."))
        except Exception:
            return (0, 0, 0)

    def get_remote_update_status(self):
        """Non-blocking cached check for newer GitHub tags."""
        cache_file = os.path.join(self.base_dir, ".update_cache.json")
        now = time.time()
        latest_remote = None
        needs_refresh = True

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    latest_remote = data.get("latest")
                    if now - data.get("timestamp", 0) < UPDATE_CHECK_INTERVAL:
                        needs_refresh = False
            except Exception:
                pass

        if needs_refresh:
            bg_code = (
                "import subprocess, re, json, time; "
                "out = subprocess.check_output(['git', '-c', 'url.https://github.com/.insteadOf=git@github.com:', 'ls-remote', '--tags', '--refs', 'origin'], text=True, creationflags=0x08000000);"
                "tags = re.findall(r'refs/tags/v?(\\d+\\.\\d+\\.\\d+)', out); "
                "latest = max(tags, key=lambda s: [int(x) for x in s.split('.')]) if tags else ''; "
                f"open({repr(cache_file)}, 'w').write(json.dumps({{'timestamp': time.time(), 'latest': latest}}))"
            )

            try:
                subprocess.Popen(
                    [sys.executable, "-c", bg_code],
                    cwd=self.base_dir,
                    creationflags=CREATE_NO_WINDOW,
                )
            except Exception:
                pass

        if latest_remote and self._parse_ver(latest_remote) > self._parse_ver(
            self.version
        ):
            return latest_remote
        return None

    def _build_launch_flags(self, base_flags):
        flags = base_flags
        if self.settings.get("suppress_tracker_window", True):
            flags += " -SuppressTracker"
        if self.settings.get("auto_teardown_on_exit", False):
            flags += " -AutoTeardown"
            if self.settings.get("default_close_mode") == "Keep Medal Open":
                flags += " -KeepMedal"
        return flags

    def query(self, param=""):
        q = param.strip().lower()

        # -----------------------------------------
        # SUBMENU: LAUNCH OPTIONS
        # -----------------------------------------
        if q.startswith("launch"):
            options = []
            rtss_note = ", suspends RTSS" if self.has_rtss else ""
            pref_launch = self.settings.get("default_launch_mode", "With ExitLag")

            if self.has_exitlag:
                opt_exitlag = {
                    "key": "With ExitLag",
                    "Title": "Launch with ExitLag",
                    "SubTitle": f"Starts ExitLag, Overlays, and Valorant{rtss_note}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": [
                            self._build_launch_flags("-Action Launch -WithExitLag")
                        ],
                    },
                }
                opt_std = {
                    "key": "Standard (No ExitLag)",
                    "Title": "Launch without ExitLag",
                    "SubTitle": f"Starts Overlays and Valorant only{rtss_note}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": [self._build_launch_flags("-Action Launch")],
                    },
                }
                options.extend([opt_exitlag, opt_std])
            else:
                options.append(
                    {
                        "key": "Standard (No ExitLag)",
                        "Title": "Launch Valorant (Standard)",
                        "SubTitle": f"Starts Overlays and Valorant{rtss_note}",
                        "IcoPath": "icons/val-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": [self._build_launch_flags("-Action Launch")],
                        },
                    }
                )

            no_overlay_params = "-Action Launch -SkipOverlays" + (
                " -WithExitLag" if self.has_exitlag else ""
            )
            no_overlay_sub = (
                "Starts ExitLag & Valorant, skips overlays"
                if self.has_exitlag
                else "Starts Valorant only, skips overlays"
            )

            options.append(
                {
                    "key": "No Overlays",
                    "Title": "Launch (No Overlays)",
                    "SubTitle": f"{no_overlay_sub}{rtss_note}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": [self._build_launch_flags(no_overlay_params)],
                    },
                }
            )

            if self.has_exitlag:
                options.append(
                    {
                        "key": "Minimal (Game Only)",
                        "Title": "Launch Minimal (Game Only)",
                        "SubTitle": f"Starts Riot Client only, skips ExitLag & overlays{rtss_note}",
                        "IcoPath": "icons/val-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": [
                                self._build_launch_flags("-Action Launch -SkipOverlays")
                            ],
                        },
                    }
                )

            options.sort(key=lambda x: 0 if x.get("key") == pref_launch else 1)
            for opt in options:
                opt.pop("key", None)

            return self._ranked(options)

        # -----------------------------------------
        # SUBMENU: CLOSE OPTIONS
        # -----------------------------------------
        elif q.startswith("close"):
            apps_killed = ["Valorant", "Riot Client", "Overwolf"]
            if self.has_exitlag:
                apps_killed.append("ExitLag")
            kill_str = ", ".join(apps_killed)
            rtss_restart = " (restarts RTSS)" if self.has_rtss else ""
            keep_medal_pref = (
                self.settings.get("default_close_mode") == "Keep Medal Open"
            )

            nuke_item = {
                "Title": "Close All (Full Nuke)",
                "SubTitle": f"Kills {kill_str}"
                + (", and Medal" if self.has_medal else "")
                + rtss_restart,
                "IcoPath": "icons/val-icon.png",
                "JsonRPCAction": {
                    "method": "execute_ps",
                    "parameters": ["-Action Close"],
                },
            }

            options = [nuke_item]
            if self.has_medal:
                keep_item = {
                    "Title": "Close Game (Keep Medal)",
                    "SubTitle": f"Kills {kill_str}{rtss_restart}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": ["-Action Close -KeepMedal"],
                    },
                }
                options = (
                    [keep_item, nuke_item]
                    if keep_medal_pref
                    else [nuke_item, keep_item]
                )

            return self._ranked(options)

        # -----------------------------------------
        # SUBMENU: MEDAL & CLIPS
        # -----------------------------------------
        elif q.startswith("medal"):
            custom_clips = (self.settings.get("custom_clips_path") or "").strip()
            clips_arg = "-Action OpenClips"
            if custom_clips:
                clips_arg += f' -CustomClipsPath "{custom_clips}"'

            return self._ranked(
                [
                    {
                        "Title": "Open Medal Window",
                        "SubTitle": "Brings the hidden Medal client UI to the foreground",
                        "IcoPath": "icons/medal-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": ["-Action OpenMedal"],
                        },
                    },
                    {
                        "Title": "Open Medal Clips Folder",
                        "SubTitle": (
                            f"Opens {custom_clips}"
                            if custom_clips
                            else "Opens your configured Medal clip directory in Explorer"
                        ),
                        "IcoPath": "icons/folder-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": [clips_arg],
                        },
                    },
                ]
            )

        # -----------------------------------------
        # MAIN MENU
        # -----------------------------------------
        else:
            val_running, riot_running = self.get_session_state()
            session_active = val_running or riot_running
            newer_ver = self.get_remote_update_status()

            launch_item = {
                "Title": "Launch Options..."
                + (" (Session Active)" if session_active else ""),
                "SubTitle": "Choose how to start Valorant",
                "IcoPath": "icons/val-icon.png",
                "JsonRPCAction": {
                    "method": "Flow.Launcher.ChangeQuery",
                    "parameters": ["vl launch ", True],
                    "dontHideAfterAction": True,
                },
            }

            status_badge = (
                " [VALORANT RUNNING]"
                if val_running
                else (" [RIOT CLIENT OPEN]" if riot_running else "")
            )
            close_item = {
                "Title": f"Close Options...{status_badge}",
                "SubTitle": "Clean up background apps and game clients",
                "IcoPath": "icons/val-icon.png",
                "JsonRPCAction": {
                    "method": "Flow.Launcher.ChangeQuery",
                    "parameters": ["vl close ", True],
                    "dontHideAfterAction": True,
                },
            }

            medal_item = {
                "Title": "Medal & Clips...",
                "SubTitle": "Open your Medal recording folder or bring up the Medal UI",
                "IcoPath": "icons/medal-icon.png",
                "JsonRPCAction": {
                    "method": "Flow.Launcher.ChangeQuery",
                    "parameters": ["vl medal ", True],
                    "dontHideAfterAction": True,
                },
            }

            if newer_ver:
                update_title = f"Update Available! (v{self.version} -> v{newer_ver})"
                update_sub = "Click to pull the newest release from GitHub"
            else:
                update_title = f"Update Plugin (v{self.version})"
                update_sub = "Fetch the latest version from GitHub via git pull"

            update_item = {
                "Title": update_title,
                "SubTitle": update_sub,
                "IcoPath": "icons/update-icon.png",
                "JsonRPCAction": {
                    "method": "execute_ps",
                    "parameters": ["-Action Update"],
                },
            }

            menu = []
            if session_active:
                keep_medal_pref = (
                    self.settings.get("default_close_mode") == "Keep Medal Open"
                    and self.has_medal
                )
                apps_killed = ["Valorant", "Riot Client", "Overwolf"]
                if self.has_exitlag:
                    apps_killed.append("ExitLag")
                if self.has_medal and not keep_medal_pref:
                    apps_killed.append("Medal")
                kill_str = ", ".join(apps_killed)
                rtss_restart = " (restarts RTSS)" if self.has_rtss else ""

                quick_title = (
                    "Quick Close (Keep Medal)"
                    if keep_medal_pref
                    else "Quick Close (Full Nuke)"
                )
                quick_param = (
                    "-Action Close -KeepMedal" if keep_medal_pref else "-Action Close"
                )

                quick_close_item = {
                    "Title": quick_title,
                    "SubTitle": f"One-click teardown: Kills {kill_str}{rtss_restart}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": [quick_param],
                    },
                }
                menu.extend([close_item, quick_close_item, launch_item])
            else:
                menu.extend([launch_item, close_item])

            if self.has_medal:
                menu.append(medal_item)

            menu.append(update_item)
            return self._ranked(menu)

    def execute_ps(self, args):
        script_path = os.path.join(os.path.dirname(__file__), "runner.ps1")

        ps_exe = "pwsh" if shutil.which("pwsh") else "powershell.exe"
        command = f'{ps_exe} -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}" {args}'
        subprocess.Popen(command, shell=False, creationflags=CREATE_NO_WINDOW)


if __name__ == "__main__":
    ValorantPlugin()
