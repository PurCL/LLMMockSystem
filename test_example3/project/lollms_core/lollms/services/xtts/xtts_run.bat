@echo off
set MINICONDA_DIR=%cd%\installer_files\miniconda3
set INSTALL_ENV_DIR=%cd%\installer_files\xtts
:: Check if portable Conda is installed
IF EXIST ".\installer_files\miniconda3\Scripts\activate.bat" (
    echo "Using portable Conda installation."
    @rem activate miniconda
    call "%MINICONDA_DIR%\Scripts\activate.bat" || ( echo Miniconda hook not found. && goto end )
    @rem activate installer env
    call conda activate "%INSTALL_ENV_DIR%" || ( echo. && echo Conda environment activation failed. && goto end )

    call .\installer_files\miniconda3\Scripts\activate.bat xtts
    call .\installer_files\miniconda3\python.exe -m xtts_api_server -o %1 -sf %2
    exit /b
) else (
    echo "No portable Conda found. Checking for system-wide Conda installation."
    where conda >nul 2>&1
    if %errorlevel% == 0 (
        echo "Using system-wide Conda installation."
        call conda activate xtts
        python -m xtts_api_server -o %1 -sf %2
        exit /b
    ) else (
        echo "No Conda installation found. Please install Conda."
        exit /b 1
    )
)
exit /b
