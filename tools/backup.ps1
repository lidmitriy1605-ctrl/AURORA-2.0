param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('dmitry', 'eva')]
    [string]$Actor,
    [Parameter(Mandatory = $true)]
    [ValidateSet('dmitry', 'eva', 'family')]
    [string]$Space,
    [string]$Directory = (Join-Path $PSScriptRoot '..\exports')
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $PSScriptRoot '..\src'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$path = Join-Path $Directory "aurora-$Space-$timestamp.json"
python -m aurora.cli export $Actor $Space $path
