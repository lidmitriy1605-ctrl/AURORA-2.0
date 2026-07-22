$ErrorActionPreference = 'Stop'

Write-Host 'AURORA 2.0 — локальный MVP' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Примеры:'
Write-Host "  .\tools\aurora.ps1 note-add dmitry dmitry 'Моя первая заметка'"
Write-Host "  .\tools\aurora.ps1 task-add dmitry dmitry 'Проверить задачу'"
Write-Host '  .\tools\aurora.ps1 task-list dmitry dmitry'
Write-Host '  .\tools\aurora.ps1 --help'
Write-Host ''
Write-Host 'Данные сохраняются локально в data\aurora.json.' -ForegroundColor Yellow
