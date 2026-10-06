import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import subprocess
from flowlauncher import FlowLauncher


class ValorantPlugin(FlowLauncher):
    def query(self, query):
        return [
            {
                "Title": "Launch Valorant (Standard)",
                "SubTitle": "Starts game, Medal, and Overwolf tracker",
                "IcoPath": "icon.png",
                "JsonRPCAction": {"method": "launch_env", "parameters": [""]},
            },
            {
                "Title": "Launch Valorant (With VPN)",
                "SubTitle": "Auto-connects to Frankfurt VPN at main menu",
                "IcoPath": "icon.png",
                "JsonRPCAction": {"method": "launch_env", "parameters": ["-WithVPN"]},
            },
            {
                "Title": "Launch Valorant (No Overlays)",
                "SubTitle": "Starts game only, skips background apps",
                "IcoPath": "icon.png",
                "JsonRPCAction": {
                    "method": "launch_env",
                    "parameters": ["-SkipOverlays"],
                },
            },
        ]

    def launch_env(self, args):
        script_path = r"C:\Users\jojor\bin\Start-Valorant.ps1"
        # -NoProfile ensures Oh-My-Posh and PSReadLine don't crash the headless run
        command = f'pwsh -NoProfile -WindowStyle Hidden -File "{script_path}" {args}'

        # 0x08000000 is the Windows CREATE_NO_WINDOW flag.
        # It fully detaches the background process so Flow Launcher doesn't hang.
        subprocess.Popen(command, shell=False, creationflags=0x08000000)


if __name__ == "__main__":
    ValorantPlugin()
