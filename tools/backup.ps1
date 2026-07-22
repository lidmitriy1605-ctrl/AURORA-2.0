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
$env:PYTHONPATH = Join-Path $PSScriptRoot '..\src'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$path = Join-Path $Directory "aurora-$Space-$timestamp.json"
python -m aurora.cli export $Actor $Space $path
