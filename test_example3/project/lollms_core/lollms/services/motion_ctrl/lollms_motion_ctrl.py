# Title LollmsMotionCtrl
# Licence: MIT
# Author : Paris Neo
# Adapted from the work of mix1009's sdwebuiapi
# check it out : https://github.com/mix1009/sdwebuiapi/tree/main
# Here is a copy of the LICENCE https://github.com/mix1009/sdwebuiapi/blob/main/LICENSE
# All rights are reserved

from pathlib import Path
import sys
from lollms.app import LollmsApplication
from lollms.paths import LollmsPaths
from lollms.config import TypedConfig, ConfigTemplate, BaseConfig
from lollms.utilities import get_conda_path, show_yes_no_dialog
import time
import io
import sys
import requests
import os
import base64
import subprocess
import time
import json
import platform
from dataclasses import dataclass
from PIL import Image, PngImagePlugin
from enum import Enum
from typing import List, Dict, Any

from ascii_colors import ASCIIColors, trace_exception
from lollms.paths import LollmsPaths
from lollms.utilities import git_pull
from lollms.utilities import url2host_port

import subprocess
import shutil




def verify_motion_ctrl(lollms_paths:LollmsPaths):
    # Clone repository
    root_dir = lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    motion_ctrl_folder = shared_folder / "auto_motion_ctrl"
    return motion_ctrl_folder.exists()
    
def install_motion_ctrl(lollms_app:LollmsApplication):
    if platform.system() == 'Windows':
        root_path = "/mnt/"+"".join(str(Path(__file__).parent).replace("\\","/").split(":"))
        if not os.path.exists('C:\\Windows\\System32\\wsl.exe'):
            if not show_yes_no_dialog("No WSL is detected on your system. Do you want me to install it for you? vLLM won't be abble to work without wsl."):
                return False
            subprocess.run(['wsl', '--install', 'Ubuntu'])
        subprocess.run(['wsl', 'bash', '-c', 'mkdir ~/motion_ctrl'])
        subprocess.run(['wsl', 'bash', '-c', 'cp {} ~/motion_ctrl'.format( root_path + '/install_motion_ctrl.sh')])
        subprocess.run(['wsl', 'bash', '-c', 'cp {} ~/motion_ctrl'.format( root_path + '/run_motion_ctrl.sh')])
        subprocess.run(['wsl', 'bash', '~/motion_ctrl/install_motion_ctrl.sh'])
    else:
        root_path = str(Path(__file__).parent)
        vllm_installer_path = root_path/'install_motion_ctrl.sh'
        vllm_run_path = root_path/'run_motion_ctrl.sh'
        vllm_path = Path.home()/"motion_ctrl"
        subprocess.run([f'mkdir {vllm_path}'])
        subprocess.run([f'cp {vllm_installer_path} {vllm_path}'])
        subprocess.run([f'cp {vllm_run_path} {vllm_path}'])
        subprocess.run(['bash', f'{vllm_path}/install_motion_ctrl.sh'])
    root_dir = lollms_app.lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    vllm_folder = shared_folder / "motion_ctrl"
    vllm_folder.mkdir(exist_ok=True, parents=True)
    return True


def get_motion_ctrl(lollms_paths:LollmsPaths):
    root_dir = lollms_paths.personal_path
    shared_folder = root_dir/"shared"
    motion_ctrl_folder = shared_folder / "auto_motion_ctrl"
    motion_ctrl_script_path = motion_ctrl_folder / "lollms_motion_ctrl.py"
    git_pull(motion_ctrl_folder)
    
    if motion_ctrl_script_path.exists():
        ASCIIColors.success("lollms_motion_ctrl found.")
        ASCIIColors.success("Loading source file...",end="")
        # use importlib to load the module from the file path
        from lollms.services.motion_ctrl.lollms_motion_ctrl import LollmsMotionCtrl
        ASCIIColors.success("ok")
        return LollmsMotionCtrl


class Service:
    has_controlnet = False
    def __init__(
                    self, 
                    app:LollmsApplication, 
                    base_url=None,
                    share=False,
                    wait_for_service=True,
                    max_retries=5
                    ):
        if base_url=="" or base_url=="http://127.0.0.1:7861":
            base_url = None
        # Get the current directory
        lollms_paths = app.lollms_paths
        self.app = app
        root_dir = lollms_paths.personal_path
        
        # Store the path to the script
        if base_url is None:
            self.base_url = "http://127.0.0.1:7860"
            if not verify_motion_ctrl(lollms_paths):
                install_motion_ctrl(app.lollms_paths)
        else:
            self.base_url = base_url

        self.auto_motion_ctrl_url = self.base_url+"/sdapi/v1"
        shared_folder = root_dir/"shared"
        self.motion_ctrl_folder = shared_folder / "motion_ctrl"
        self.output_dir = root_dir / "outputs/motion_ctrl"
        self.output_dir.mkdir(parents=True, exist_ok=True)

       
        ASCIIColors.red("                                                                                ")
        ASCIIColors.red("_       _ _                                 _   _                   _        _  ")
        ASCIIColors.red("| |     | | |                               | | (_)                 | |      | |")
        ASCIIColors.red("| | ___ | | |_ __ ___  ___   _ __ ___   ___ | |_ _  ___  _ __    ___| |_ _ __| |")
        ASCIIColors.red("| |/ _ \| | | '_ ` _ \/ __| | '_ ` _ \ / _ \| __| |/ _ \| '_ \  / __| __| '__| |")
        ASCIIColors.red("| | (_) | | | | | | | \__ \ | | | | | | (_) | |_| | (_) | | | || (__| |_| |  | |")
        ASCIIColors.red("|_|\___/|_|_|_| |_| |_|___/ |_| |_| |_|\___/ \__|_|\___/|_| |_| \___|\__|_|  |_|")
        ASCIIColors.red("                        ______                              ______              ")
        ASCIIColors.red("                       |______|                            |______|             ")

        ASCIIColors.red(" Forked from TencentARC's MotionCtrl api")
        ASCIIColors.red(" Integration in lollms by ParisNeo")
        motion_ctrl_folder = shared_folder / "auto_motion_ctrl"
        env_name = "MotionCtrl"

        if not self.wait_for_service(1,False):
            ASCIIColors.info("Loading lollms_motion_ctrl")
            os.environ['motion_ctrl_WEBUI_RESTARTING'] = '1' # To forbid sd webui from showing on the browser automatically

            # Get the current operating system
            os_name = platform.system()
            conda_path = get_conda_path()
            import conda.cli
            env_name = "MotionCtrl"
            # Replace 'your_env_name' with the name of the environment you created
            activate_env_command = f"conda activate {env_name} && "
            pip_install_command = ""
            _, host, port = url2host_port(base_url)
            # run motion_ctrl
            if platform.system() == 'Windows':
                #subprocess.Popen(['wsl', 'ls', '$HOME'])
                subprocess.Popen(['wsl', 'bash', '$HOME/run_motion_ctrl.sh',  host, str(port)])
            else:
                subprocess.Popen(['bash', f'{Path.home()}/run_motion_ctrl.sh', host, str(port)])



        # Wait until the service is available at http://127.0.0.1:7860/
        if wait_for_service:
            self.wait_for_service(max_retries=max_retries)
        else:
            ASCIIColors.warning("We are not waiting for the MotionCtrl service to be up.\nThis means that you may need to wait a bit before you can use it.")

        self.session = requests.Session()

    def wait_for_service(self, max_retries = 50, show_warning=True):
        url = f"{self.base_url}"
        # Adjust this value as needed
        retries = 0

        while retries < max_retries or max_retries<0:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    print("Service is available.")
                    if self.app is not None:
                        self.app.success("Motion ctrl is now available.")
                    return True
            except requests.exceptions.RequestException:
                pass

            retries += 1
            time.sleep(1)
        if show_warning:
            print("Service did not become available within the given time.")
            if self.app is not None:
                self.app.error("SD Service did not become available within the given time.")
        return False