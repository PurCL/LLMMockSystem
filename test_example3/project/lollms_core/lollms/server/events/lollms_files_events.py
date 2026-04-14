"""
project: lollms
file: lollms_files_events.py 
author: ParisNeo
description: 
    Events related to socket io file events

"""

from fastapi import APIRouter, Request
from fastapi import HTTPException
from pydantic import BaseModel
import pkg_resources
from lollms.server.elf_server import LOLLMSElfServer
from fastapi.responses import FileResponse
from lollms.binding import BindingBuilder, InstallOption
from ascii_colors import ASCIIColors
from lollms.personality import MSG_TYPE, AIPersonality
from lollms.types import MSG_TYPE, SENDER_TYPES
from lollms.utilities import load_config, trace_exception, gc
from lollms.utilities import find_first_available_file_index, convert_language_name, run_async
from lollms_webui import LOLLMSWebUI
from pathlib import Path
from typing import List
import socketio
import threading
import os
from functools import partial
from lollms.databases.discussions_database import Discussion
from datetime import datetime

router = APIRouter()
lollmsElfServer = LOLLMSWebUI.get_instance()


# ----------------------------------- events -----------------------------------------
def add_events(sio:socketio):
    @sio.on('upload_file')
    def upload_file(sid, data):
        pass
        """
       ASCIIColors.yellow("Uploading file")
        file = data['file']
        filename = file.filename
        save_path = lollmsElfServer.lollms_paths.personal_uploads_path/filename  # Specify the desired folder path

        try:
            if not lollmsElfServer.personality.processor is None:
                file.save(save_path)
                lollmsElfServer.personality.processor.add_file(save_path, partial(lollmsElfServer.process_chunk, client_id = sid))
                # File saved successfully
                run_async(partial(sio.emit,'progress', {'status':True, 'progress': 100}))

            else:
                file.save(save_path)
                lollmsElfServer.personality.add_file(save_path, partial(lollmsElfServer.process_chunk, client_id = sid))
                # File saved successfully
                run_async(partial(sio.emit,'progress', {'status':True, 'progress': 100}))
        except Exception as e:
            # Error occurred while saving the file
            run_async(partial(sio.emit,'progress', {'status':False, 'error': str(e)}))
                    
        """
 