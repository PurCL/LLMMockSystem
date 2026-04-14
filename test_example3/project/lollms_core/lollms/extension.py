# File : extension.py
# Author : ParisNeo
# Description :
# This is the main class to be imported by the extension
# it gives your code access to the model, the callback functions, the model conditionning etc
from ascii_colors import ASCIIColors

from lollms.config import InstallOption, TypedConfig, BaseConfig, ConfigTemplate
from lollms.paths import LollmsPaths
from enum import Enum
from pathlib import Path
import importlib


__author__ = "parisneo"
__github__ = "https://github.com/ParisNeo/lollms-webui"
__copyright__ = "Copyright 2023, "
__license__ = "Apache 2.0"


class EXTENSION_TYPE(Enum):
    EXTENSION_TYPE_STAND_ALONE = 0 # An extension that has access to the current personality and model but has an independant 


class LOLLMSExtension():
    def __init__(self, 
                    name:str, 
                    script_path:str|Path, 
                    config:TypedConfig, 
                    app,
                    installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY) -> None:
        self.name = name
        self.app = app
        self.config = config
        self.script_path = script_path
        self.category = str(script_path).replace("\\","/").split("/")[-2]
        self.extension_folder_name = str(script_path).replace("\\","/").split("/")[-1]
        self.card =  self.script_path /"card.yaml"
        
        self.configuration_path = app.lollms_paths.personal_configuration_path/"extensions"/f"{name}"
        self.configuration_path.mkdir(parents=True, exist_ok=True)
        self.configuration_path= self.configuration_path/"config.yaml"

        self.installation_option = installation_option
        # Installation
        if (not self.configuration_path.exists() or self.installation_option==InstallOption.FORCE_INSTALL) and self.installation_option!=InstallOption.NEVER_INSTALL:
            self.install()
            self.config.save(self.configuration_path)


    def build_extension(self):
        return self

    def install(self):
        """
        Installation procedure (to be implemented)
        """
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
        ASCIIColors.red(f"Installing {self.name}")
        ASCIIColors.blue("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")


    def pre_gen(self, previous_prompt:str, prompt:str):
        return previous_prompt, prompt

    def in_gen(self, chunk:str)->str:
        return chunk

    def post_gen(self, ai_output:str):
        pass


    def get_ui():
        """
        Get user interface of the extension
        """
        return "<p>This is a ui extension template</p>"
    


class ExtensionBuilder:
    def build_extension(
                        self, 
                        extension_path:str, 
                        lollms_paths:LollmsPaths,
                        app,
                        installation_option:InstallOption=InstallOption.INSTALL_IF_NECESSARY
                    )->LOLLMSExtension:

        extension, script_path = self.getExtension(extension_path, lollms_paths, app)
        return extension(app = app, installation_option = installation_option)
    
    def getExtension(
                        self, 
                        extension_path:str, 
                        lollms_paths:LollmsPaths,
                        app
                    )->LOLLMSExtension:
        
        extension_path = lollms_paths.extensions_zoo_path / extension_path

        # define the full absolute path to the module
        absolute_path = extension_path.resolve()
        # infer the module name from the file path
        module_name = extension_path.stem
        # use importlib to load the module from the file path
        loader = importlib.machinery.SourceFileLoader(module_name, str(absolute_path / "__init__.py"))
        extension_module = loader.load_module()
        extension:LOLLMSExtension = getattr(extension_module, extension_module.extension_name)
        return extension, absolute_path