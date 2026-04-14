"""
project: lollms
file: lollms_rag_events.py 
author: ParisNeo
description: 
    Events related to socket io model events

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
from lollms.utilities import load_config, trace_exception, gc, terminate_thread, run_async
from pathlib import Path
from typing import List
import socketio
from datetime import datetime
from functools import partial
import shutil
import threading
import os
from tqdm import tqdm

lollmsElfServer = LOLLMSElfServer.get_instance()


# ----------------------------------- events -----------------------------------------
def add_events(sio:socketio):
    @sio.on('upgrade_vectorization')
    def upgrade_vectorization():
        if lollmsElfServer.config.data_vectorization_activate and lollmsElfServer.config.activate_skills_lib:
            try:
                run_async(partial(sio.emit,'show_progress'))
                lollmsElfServer.sio.sleep(0)
                ASCIIColors.yellow("0- Detected discussion vectorization request")
                folder = lollmsElfServer.lollms_paths.personal_discussions_path/"vectorized_dbs"
                folder.mkdir(parents=True, exist_ok=True)
                lollmsElfServer.build_long_term_skills_memory()
                
                ASCIIColors.yellow("1- Exporting discussions")
                discussions = lollmsElfServer.db.export_all_as_markdown_list_for_vectorization()
                ASCIIColors.yellow("2- Adding discussions to vectorizer")
                index = 0
                nb_discussions = len(discussions)
                for (title,discussion) in tqdm(discussions):
                    run_async(partial(sio.emit,'update_progress',{'value':int(100*(index/nb_discussions))}))
                    lollmsElfServer.sio.sleep(0)
                    index += 1
                    if discussion!='':
                        skill = lollmsElfServer.learn_from_discussion(title, discussion)
                        lollmsElfServer.long_term_memory.add_document(title, skill, chunk_size=lollmsElfServer.config.data_vectorization_chunk_size, overlap_size=lollmsElfServer.config.data_vectorization_overlap_size, force_vectorize=False, add_as_a_bloc=False)
                ASCIIColors.yellow("3- Indexing database")
                lollmsElfServer.long_term_memory.index()
                ASCIIColors.yellow("4- Saving database")
                lollmsElfServer.long_term_memory.save_to_json()
                
                if lollmsElfServer.config.data_vectorization_visualize_on_vectorization:
                    lollmsElfServer.long_term_memory.show_document(show_interactive_form=True)
                ASCIIColors.yellow("Ready")
            except Exception as ex:
                ASCIIColors.error(f"Couldn't vectorize database:{ex}")
        run_async(partial(sio.emit,'hide_progress'))     
        lollmsElfServer.sio.sleep(0)