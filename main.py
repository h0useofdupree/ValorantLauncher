import sys
import os
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

from flowlauncher import FlowLauncher

class ValorantPlugin(FlowLauncher):
    def query(self, param=""):
        q = param.strip().lower()
        
        # -----------------------------------------
        # SUBMENU: LAUNCH OPTIONS
        # -----------------------------------------
        if q.startswith("launch"):
            return [
                {
                    "Title": "Launch with ExitLag",
                    "SubTitle": "Starts ExitLag, Overlays, and Valorant",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {"method": "execute_ps", "parameters": ["-Action Launch -WithExitLag"]}
                },
                {
                    "Title": "Launch without ExitLag",
                    "SubTitle": "Starts Overlays and Valorant only",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {"method": "execute_ps", "parameters": ["-Action Launch"]}
                },
                {
                    "Title": "Launch (No Overlays)",
                    "SubTitle": "Starts ExitLag and Valorant, skips background apps",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {"method": "execute_ps", "parameters": ["-Action Launch -WithExitLag -SkipOverlays"]}
                },
                {
                    "Title": "Launch Minimal (Game Only)",
                    "SubTitle": "Kills RTSS and starts Riot Client only",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {"method": "execute_ps", "parameters": ["-Action Launch -SkipOverlays"]}
                }
            ]
            
        # -----------------------------------------
        # SUBMENU: CLOSE OPTIONS
        # -----------------------------------------
        elif q.startswith("close"):
            return [
                {
                    "Title": "Close All (Full Nuke)",
                    "SubTitle": "Kills everything including Medal",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {"method": "execute_ps", "parameters": ["-Action Close"]}
                },
                {
                    "Title": "Close Game (Keep Medal)",
                    "SubTitle": "Kills Valorant, Riot Client, Overwolf, and ExitLag",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {"method": "execute_ps", "parameters": ["-Action Close -KeepMedal"]}
                }
            ]
            
        # -----------------------------------------
        # MAIN MENU
        # -----------------------------------------
        else:
            return [
                {
                    "Title": "Launch Options...",
                    "SubTitle": "Choose how to start Valorant",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {
                        "method": "Flow.Launcher.ChangeQuery",
                        "parameters": ["vl launch ", True],
                        "dontHideAfterAction": True
                    }
                },
                {
                    "Title": "Close Options...",
                    "SubTitle": "Clean up background apps and game clients",
                    "IcoPath": "icon.png",
                    "JsonRPCAction": {
                        "method": "Flow.Launcher.ChangeQuery",
                        "parameters": ["vl close ", True],
                        "dontHideAfterAction": True
                    }
                }
            ]

    def execute_ps(self, args):
        script_path = os.path.join(os.path.dirname(__file__), "Start-Valorant.ps1")
        command = f'pwsh -NoProfile -WindowStyle Hidden -File "{script_path}" {args}'
        subprocess.Popen(command, shell=False, creationflags=0x08000000)

if __name__ == "__main__":
    ValorantPlugin()