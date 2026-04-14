@echo off
set MINICONDA_DIR=%cd%\installer_files\miniconda3
set INSTALL_ENV_DIR=%cd%\installer_files\xtts

:: Check if portable Conda is installed
IF EXIST "%MINICONDA_DIR%\Scripts\activate.bat" (
    echo "Using portable Conda installation."
    echo "%MINICONDA_DIR%"
    @rem create the installer env

    if exist "%INSTALL_ENV_DIR%" (
        echo "found"
        rmdir "%INSTALL_ENV_DIR%" /s /q
    )
    echo Packages to install: %PACKAGES_TO_INSTALL%
    call conda create --no-shortcuts -y -k -p "%INSTALL_ENV_DIR%" || ( echo. && echo Conda environment creation failed. && goto end )

    @rem activate miniconda
    call "%MINICONDA_DIR%\Scripts\activate.bat" || ( echo Miniconda hook not found. && goto end )
    call "%MINICONDA_DIR%\Scripts\pip.exe" install xtts-api-server

) else (
    echo "No portable Conda found. Checking for system-wide Conda installation."
    where conda >nul 2>&1
    if %errorlevel% == 0 (
        echo "Using system-wide Conda installation."
        call conda deactivate
        call conda info --envs | findstr /B /C:"xtts" >nul 2>&1
        if %errorlevel% == 0 (
            echo "Conda environment 'xtts' already exists. Deleting it."
            call conda env remove --name xtts --yes
        )
        call conda create --name xtts --yes
        call conda activate xtts
        call pip install xtts-api-server
        
    ) else (
        echo "No Conda installation found. Please install Conda."
        exit /b 1
    )
)
echo "Done"
exit /b
