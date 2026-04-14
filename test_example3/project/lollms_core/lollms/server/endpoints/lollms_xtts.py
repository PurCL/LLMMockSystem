"""
project: lollms_webui
file: lollms_xtts.py 
author: ParisNeo
description: 
    This module contains a set of FastAPI routes that provide information about the Lord of Large Language and Multimodal Systems (LoLLMs) Web UI
    application. These routes allow users to 

"""
from fastapi import APIRouter, Request
from lollms_webui import LOLLMSWebUI
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from lollms.types import MSG_TYPE
from lollms.main_config import BaseConfig
from lollms.utilities import detect_antiprompt, remove_text_from_string, trace_exception, find_first_available_file_index, add_period, PackageManager
from pathlib import Path
from ascii_colors import ASCIIColors
import os
import platform

# ----------------------- Defining router and main class ------------------------------

router = APIRouter()
lollmsElfServer:LOLLMSWebUI = LOLLMSWebUI.get_instance()


# ----------------------- voice ------------------------------

@router.get("/list_voices")
def list_voices():
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    ASCIIColors.yellow("Listing voices")
    voices=["main_voice"]
    voices_dir:Path=lollmsElfServer.lollms_paths.custom_voices_path
    voices += [v.stem for v in voices_dir.iterdir() if v.suffix==".wav"]
    return {"voices":voices}

@router.post("/set_voice")
async def set_voice(request: Request):
    """
    Changes current voice

    :param request: The HTTP request object.
    :return: A JSON response with the status of the operation.
    """
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    try:
        data = (await request.json())
        lollmsElfServer.config.current_voice=data["voice"]
        if lollmsElfServer.config.auto_save:
            lollmsElfServer.config.save_config()
        return {"status":True}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}


class LollmsText2AudioRequest(BaseModel):
    text: str
    voice: str = None
    fn:str = None

@router.post("/text2Audio")
async def text2Audio(request: LollmsText2AudioRequest):
    """
    Executes Python code and returns the output.

    :param request: The HTTP request object.
    :return: A JSON response with the status of the operation.
    """
    if lollmsElfServer.config.headless_server_mode:
        return {"status":False,"error":"Code execution is blocked when in headless mode for obvious security reasons!"}

    if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
        return {"status":False,"error":"Code execution is blocked when the server is exposed outside for very obvious reasons!"}

    try:
        # Get the JSON data from the POST request.
        try:
            from lollms.services.xtts.lollms_xtts import LollmsXTTS
            if lollmsElfServer.tts is None:
                lollmsElfServer.tts = LollmsXTTS(
                    lollmsElfServer, 
                    voice_samples_path=Path(__file__).parent/"voices", 
                    xtts_base_url= lollmsElfServer.config.xtts_base_url
                )
        except:
            return {"url": None}
            
        voice=lollmsElfServer.config.current_voice if request.voice is None else request.voice
        index = find_first_available_file_index(lollmsElfServer.tts.output_folder, "voice_sample_",".wav")
        output_fn=f"voice_sample_{index}.wav" if request.fn is None else request.fn
        if voice is None:
            voice = "main_voice"
        lollmsElfServer.info("Starting to build voice")
        try:
            from lollms.services.xtts.lollms_xtts import LollmsXTTS
            if lollmsElfServer.tts is None:
                lollmsElfServer.tts = LollmsXTTS(lollmsElfServer, voice_samples_path=Path(__file__).parent/"voices", xtts_base_url= lollmsElfServer.config.xtts_base_url)
            language = lollmsElfServer.config.current_language# convert_language_name()
            if voice!="main_voice":
                voices_folder = lollmsElfServer.lollms_paths.custom_voices_path
            else:
                voices_folder = Path(__file__).parent.parent.parent/"services/xtts/voices"
            lollmsElfServer.tts.set_speaker_folder(voices_folder)
            url = f"audio/{output_fn}"
            preprocessed_text= add_period(request.text)

            lollmsElfServer.tts.tts_to_file(preprocessed_text, f"{voice}.wav", f"{output_fn}", language=language)
            lollmsElfServer.info(f"Voice file ready at {url}")
            return {"url": url}
        except:
            return {"url": None}
    except Exception as ex:
        trace_exception(ex)
        lollmsElfServer.error(ex)
        return {"status":False,"error":str(ex)}
    
@router.get("/install_xtts")
def install_xtts():
    try:
        if lollmsElfServer.config.headless_server_mode:
            return {"status":False,"error":"Service installation is blocked when in headless mode for obvious security reasons!"}

        if lollmsElfServer.config.host!="localhost" and lollmsElfServer.config.host!="127.0.0.1":
            return {"status":False,"error":"Service installation is blocked when the server is exposed outside for very obvious reasons!"}
        
        from lollms.services.xtts.lollms_xtts import install_xtts
        lollmsElfServer.ShowBlockingMessage("Installing xTTS api server\nPlease stand by")
        install_xtts(lollmsElfServer)
        lollmsElfServer.HideBlockingMessage()
        return {"status":True}
    except Exception as ex:
        lollmsElfServer.HideBlockingMessage()
        return {"status":False, 'error':str(ex)}