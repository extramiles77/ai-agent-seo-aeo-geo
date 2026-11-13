@echo off
rem Windows entry point for Ai Agent SEO's bundled Python tools, for harnesses
rem whose shell is cmd.exe or PowerShell (Codex, Cursor, Copilot, Windsurf).
rem Bash-based harnesses keep using the sibling "claude-seo" launcher.
rem From PowerShell call it as:  & "<path>\claude-seo.cmd" run <script.py> ...
setlocal
set "RUNTIME=%~dp0runtime.py"
if defined CLAUDE_SEO_PYTHON goto override
where py >nul 2>nul
if %ERRORLEVEL%==0 goto pylauncher
python "%RUNTIME%" %*
exit /b %ERRORLEVEL%
:pylauncher
py -3 "%RUNTIME%" %*
exit /b %ERRORLEVEL%
:override
"%CLAUDE_SEO_PYTHON%" "%RUNTIME%" %*
exit /b %ERRORLEVEL%
