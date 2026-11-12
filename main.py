import sys
import os
import shutil
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

from flowlauncher import FlowLauncher


class ValorantPlugin(FlowLauncher):
    def __init__(self):
        # Auto-detect installed tools on current machine
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

            options = []
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

            options.append(
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
            )
            return options

        # -----------------------------------------
        # MAIN MENU
        # -----------------------------------------
        else:
            return [
                {
                    "Title": "Launch Options...",
                    "SubTitle": "Choose how to start Valorant",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "Flow.Launcher.ChangeQuery",
                        "parameters": ["vl launch ", True],
                        "dontHideAfterAction": True,
                    },
                },
                {
                    "Title": "Close Options...",
                    "SubTitle": "Clean up background apps and game clients",
                    "IcoPath": "icons/val-icon.png",
                    "JsonRPCAction": {
                        "method": "Flow.Launcher.ChangeQuery",
                        "parameters": ["vl close ", True],
                        "dontHideAfterAction": True,
                    },
                },
                {
                    "Title": "Update Plugin (Git Pull)",
                    "SubTitle": "Fetch the latest version from GitHub",
                    "IcoPath": "icons/update-icon.png",
                    "JsonRPCAction": {
                        "method": "execute_ps",
                        "parameters": ["-Action Update"],
                    },
                },
            ]

    def execute_ps(self, args):
        script_path = os.path.join(os.path.dirname(__file__), "Start-Valorant.ps1")

        # Use pwsh (PS7) if installed, otherwise fall back to powershell.exe
        ps_exe = "pwsh" if shutil.which("pwsh") else "powershell.exe"
        command = f'{ps_exe} -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}" {args}'
        subprocess.Popen(command, shell=False, creationflags=0x08000000)


if __name__ == "__main__":
    ValorantPlugin()
