param(
    [ValidateSet('Fast', 'Standard', 'Extended')]
    [string]$Tier = 'Fast'
)

$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = 'src'
$tiers = Get-Content -Raw 'config/v5_test_tiers.json' | ConvertFrom-Json

if ($Tier -eq 'Extended') {
    python -m unittest discover -s tests
    exit $LASTEXITCODE
}

$modules = @($tiers.tiers.$($Tier.ToLower()))
python -m unittest @modules
exit $LASTEXITCODE
