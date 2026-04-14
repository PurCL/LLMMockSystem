"""
project: lollms_webui
file: lollms_skills_library.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that allow user to interact with the skills library.

"""
from fastapi import APIRouter, Request
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from lollms.types import MSG_TYPE
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception
from lollms.security import sanitize_path
from ascii_colors import ASCIIColors
from lollms.databases.discussions_database import DiscussionsDB, Discussion
from typing import List

from safe_store.text_vectorizer import TextVectorizer, VectorizationMethod, VisualizationMethod
import tqdm
from pathlib import Path
# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer:LOLLMSWebUI = LOLLMSWebUI.get_instance()

class DiscussionInfos(BaseModel):
    client_id: str

@router.get("/add_discussion_to_skills_library")
def add_discussion_to_skills_library(discussionInfos:DiscussionInfos):
    client = lollmsElfServer.session.get_client(discussionInfos.client_id)
    lollmsElfServer.add_discussion_tto_skills_library(client)    
