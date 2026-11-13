import sys
import os
import json
import ctypes
from ctypes import wintypes
import shutil
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

from flowlauncher import FlowLauncher

CREATE_NO_WINDOW = 0x08000000
TH32CS_SNAPPROCESS = 0x00000002


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
        base_dir = os.path.dirname(__file__)

        try:
            with open(
                os.path.join(base_dir, "plugin.json"), "r", encoding="utf-8-sig"
            ) as f:
                self.version = json.load(f).get("Version", "Unknown")
        except Exception:
            self.version = "Unknown"

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

    def query(self, param=""):
        q = param.strip().lower()

        # -----------------------------------------
        # SUBMENU: LAUNCH OPTIONS
        # -----------------------------------------
        if q.startswith("launch"):
            options = []
            rtss_note = ", suspends RTSS" if self.has_rtss else ""

            if self.has_exitlag:
                options.extend(
                    [
                        {
                            "Title": "Launch with ExitLag",
                            "SubTitle": f"Starts ExitLag, Overlays, and Valorant{rtss_note}",
                            "IcoPath": "icons/val-icon.png",
                            "JsonRPCAction": {
                                "method": "execute_ps",
                                "parameters": ["-Action Launch -WithExitLag"],
                            },
                        },
                        {
                            "Title": "Launch without ExitLag",
                            "SubTitle": f"Starts Overlays and Valorant only{rtss_note}",
                            "IcoPath": "icons/val-icon.png",
                            "JsonRPCAction": {
                                "method": "execute_ps",
                                "parameters": ["-Action Launch"],
                            },
                        },
                    ]
                )
            else:
                options.append(
                    {
                        "Title": "Launch Valorant (Standard)",
                        "SubTitle": f"Starts Overlays and Valorant{rtss_note}",
                        "IcoPath": "icons/val-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": ["-Action Launch"],
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
                    "Title": "Launch (No Overlays)",
                    "SubTitle": f"{no_overlay_sub}{rtss_note}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": [no_overlay_params],
                    },
                }
            )

            if self.has_exitlag:
                options.append(
                    {
                        "Title": "Launch Minimal (Game Only)",
                        "SubTitle": f"Starts Riot Client only, skips ExitLag & overlays{rtss_note}",
                        "IcoPath": "icons/val-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": ["-Action Launch -SkipOverlays"],
                        },
                    }
                )

            return options

        # -----------------------------------------
        # SUBMENU: CLOSE OPTIONS
        # -----------------------------------------
        elif q.startswith("close"):
            apps_killed = ["Valorant", "Riot Client", "Overwolf"]
            if self.has_exitlag:
                apps_killed.append("ExitLag")
            kill_str = ", ".join(apps_killed)
            rtss_restart = " (restarts RTSS)" if self.has_rtss else ""

            options = [
                {
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
            ]

            if self.has_medal:
                options.append(
                    {
                        "Title": "Close Game (Keep Medal)",
                        "SubTitle": f"Kills {kill_str}{rtss_restart}",
                        "IcoPath": "icons/val-icon.png",
                        "JsonRPCAction": {
                            "method": "execute_ps",
                            "parameters": ["-Action Close -KeepMedal"],
                        },
                    }
                )

            return options

        # -----------------------------------------
        # MAIN MENU (Context-Aware)
        # -----------------------------------------
        else:
            val_running, riot_running = self.get_session_state()
            session_active = val_running or riot_running

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

            update_item = {
                "Title": f"Update Plugin (v{self.version})",
                "SubTitle": "Fetch the latest version from GitHub via git pull",
                "IcoPath": "icons/update-icon.png",
                "JsonRPCAction": {
                    "method": "execute_ps",
                    "parameters": ["-Action Update"],
                },
            }

            if session_active:
                apps_killed = ["Valorant", "Riot Client", "Overwolf"]
                if self.has_exitlag:
                    apps_killed.append("ExitLag")
                if self.has_medal:
                    apps_killed.append("Medal")
                kill_str = ", ".join(apps_killed)
                rtss_restart = " (restarts RTSS)" if self.has_rtss else ""

                quick_close_item = {
                    "Title": "Quick Close (Full Nuke)",
                    "SubTitle": f"One-click teardown: Kills {kill_str}{rtss_restart}",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": ["-Action Close"],
                    },
                }
                return [close_item, quick_close_item, launch_item, update_item]

            return [launch_item, close_item, update_item]

    def execute_ps(self, args):
        script_path = os.path.join(os.path.dirname(__file__), "runner.ps1")

        # Use pwsh (PS7) if installed, otherwise fall back to powershell.exe
        ps_exe = "pwsh" if shutil.which("pwsh") else "powershell.exe"
        command = f'{ps_exe} -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}" {args}'
        subprocess.Popen(command, shell=False, creationflags=CREATE_NO_WINDOW)


if __name__ == "__main__":
    ValorantPlugin()
