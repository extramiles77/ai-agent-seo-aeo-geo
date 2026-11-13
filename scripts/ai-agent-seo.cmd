@echo off
rem Windows entry point for AI Agent SEO's bundled Python tools, for harnesses
rem whose shell is cmd.exe or PowerShell (Codex, Cursor, Copilot, Windsurf).
rem Bash-based harnesses keep using the sibling "ai-agent-seo" launcher.
rem From PowerShell call it as:  & "<path>\ai-agent-seo.cmd" run <script.py> ...
setlocal
set "RUNTIME=%~dp0runtime.py"
rem CLAUDE_SEO_PYTHON is the name used before the AI Agent SEO rename.
if not defined AI_AGENT_SEO_PYTHON if defined CLAUDE_SEO_PYTHON set "AI_AGENT_SEO_PYTHON=%CLAUDE_SEO_PYTHON%"
if defined AI_AGENT_SEO_PYTHON goto override
where py >nul 2>nul
if %ERRORLEVEL%==0 goto pylauncher
python "%RUNTIME%" %*
exit /b %ERRORLEVEL%
:pylauncher
py -3 "%RUNTIME%" %*
exit /b %ERRORLEVEL%
:override
"%AI_AGENT_SEO_PYTHON%" "%RUNTIME%" %*
exit /b %ERRORLEVEL%
