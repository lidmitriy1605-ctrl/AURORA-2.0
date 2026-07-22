$ErrorActionPreference = 'Stop'

Write-Host 'AURORA 2.0 - local MVP' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Examples:'
Write-Host "  .\tools\aurora.ps1 note-add dmitry dmitry 'My first note'"
Write-Host "  .\tools\aurora.ps1 task-add dmitry dmitry 'Review task'"
Write-Host '  .\tools\aurora.ps1 task-list dmitry dmitry'
Write-Host '  .\tools\aurora.ps1 --help'
Write-Host ''
Write-Host 'Data is stored locally in data\aurora.json.' -ForegroundColor Yellow
