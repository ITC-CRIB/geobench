@echo off

:: Default values (empty, Python will use its defaults)
set "CORES="
set "N="

:: Parse command line arguments
:parse_args
if "%~1"=="" goto end_parse

if /i "%~1"=="-c" (
    set "CORES=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--cores" (
    set "CORES=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-n" (
    set "N=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--num" (
    set "N=%~2"
    shift
    shift
    goto parse_args
)

echo Unknown argument: %~1
shift
goto parse_args
:end_parse

:: Build python command
set "CMD=python count_primes.py"

if not "%CORES%"=="" set "CMD=%CMD% --cores %CORES%"
if not "%N%"=="" set "CMD=%CMD% --n %N%"

:: Run python command
echo Running: %CMD%
%CMD%

