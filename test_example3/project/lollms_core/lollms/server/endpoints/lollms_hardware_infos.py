"""
project: lollms
file: lollms_hardware_infos.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes are specific to handling hardware information 

"""

from fastapi import APIRouter, Request
import pkg_resources
from lollms.server.elf_server import LOLLMSElfServer
from ascii_colors import ASCIIColors
from lollms.utilities import load_config
from pathlib import Path
from typing import List
import psutil
import subprocess

# ----------------------- Defining router and main class ------------------------------
router = APIRouter()
lollmsElfServer = LOLLMSElfServer.get_instance()

@router.get("/disk_usage")
def disk_usage():
    current_drive = Path.cwd().anchor
    drive_disk_usage = psutil.disk_usage(current_drive)
    try:
        models_folder_disk_usage = psutil.disk_usage(str(lollmsElfServer.lollms_paths.personal_models_path/f'{lollmsElfServer.config["binding_name"]}'))
        return {
            "total_space":drive_disk_usage.total,
            "available_space":drive_disk_usage.free,
            "usage":drive_disk_usage.used,
            "percent_usage":drive_disk_usage.percent,

            "binding_disk_total_space":models_folder_disk_usage.total,
            "binding_disk_available_space":models_folder_disk_usage.free,
            "binding_models_usage": models_folder_disk_usage.used,
            "binding_models_percent_usage": models_folder_disk_usage.percent,
            }
    except Exception as ex:
        return {
            "total_space":drive_disk_usage.total,
            "available_space":drive_disk_usage.free,
            "percent_usage":drive_disk_usage.percent,

            "binding_disk_total_space": None,
            "binding_disk_available_space": None,
            "binding_models_usage": None,
            "binding_models_percent_usage": None,
            }

@router.get("/ram_usage")
def ram_usage():
    """
    Returns the RAM usage in bytes.
    """
    ram = psutil.virtual_memory()
    return {
        "total_space":ram.total,
        "available_space":ram.free,

        "percent_usage":ram.percent,
        "ram_usage": ram.used
        }

@router.get("/vram_usage")
def vram_usage():
    try:
        output = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.total,memory.used,gpu_name', '--format=csv,nounits,noheader'])
        lines = output.decode().strip().split('\n')
        vram_info = [line.split(',') for line in lines]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
        "nb_gpus": 0
        }
    
    ram_usage = {
        "nb_gpus": len(vram_info)
    }
    
    if vram_info is not None:
        for i, gpu in enumerate(vram_info):
            ram_usage[f"gpu_{i}_total_vram"] = int(gpu[0])*1024*1024
            ram_usage[f"gpu_{i}_used_vram"] = int(gpu[1])*1024*1024
            ram_usage[f"gpu_{i}_model"] = gpu[2].strip()
    else:
        # Set all VRAM-related entries to None
        ram_usage["gpu_0_total_vram"] = None
        ram_usage["gpu_0_used_vram"] = None
        ram_usage["gpu_0_model"] = None
    
    return ram_usage