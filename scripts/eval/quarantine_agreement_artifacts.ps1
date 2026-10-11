param(
    [string]$InventoryPath = 'docs/eval/quarantine_agreement_20261012.json',
    [switch]$VerifyOnly
)

# Maintainer-requested artifact relocation. Never overwrite or remove a file.
# The inventory fixes the selection and preserves the original hashes for recovery.
$ErrorActionPreference = 'Stop'
$inventoryFullPath = (Resolve-Path -LiteralPath $InventoryPath).Path
$inventory = Get-Content -LiteralPath $inventoryFullPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sourceRoot = [IO.Path]::GetFullPath($inventory.source_root).TrimEnd('\')
$archiveRoot = [IO.Path]::GetFullPath($inventory.destination_root).TrimEnd('\')
$priorRoot = [IO.Path]::GetFullPath($inventory.prior_archive_root).TrimEnd('\')
$expectedArchive = Join-Path (Split-Path -Parent $sourceRoot) 'Falsified'
if ($archiveRoot -ne $expectedArchive) { throw 'Destination must be the explicit sibling Falsified directory.' }
if ($priorRoot -ne (Join-Path (Split-Path -Parent $sourceRoot) 'narrativewiki-old-ai-evals-2026-10-10-d95d307')) {
    throw 'Unexpected prior archive root.'
}
if (-not $inventoryFullPath.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Inventory must be inside the source repository.'
}

function Assert-Hash([string]$Path, [string]$ExpectedHash) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHash) {
        throw "Hash mismatch: $Path"
    }
}

# Validate every resolved source and destination before the first mutation.
$destinations = @{}
foreach ($entry in $inventory.entries) {
    $source = [IO.Path]::GetFullPath($entry.source)
    $destination = [IO.Path]::GetFullPath((Join-Path $archiveRoot $entry.destination_relative))
    if (-not ($source.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
              $source.StartsWith($priorRoot + '\', [StringComparison]::OrdinalIgnoreCase))) {
        throw "Source escapes the explicitly named roots: $source"
    }
    if (-not $destination.StartsWith($archiveRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Destination escapes Falsified: $destination"
    }
    if ($destinations.ContainsKey($destination)) { throw "Duplicate destination: $destination" }
    $destinations[$destination] = $true
    if ($VerifyOnly) {
        if (Test-Path -LiteralPath $source) { throw "Source still present: $source" }
        Assert-Hash $destination $entry.sha256
    } elseif (Test-Path -LiteralPath $source -PathType Leaf) {
        if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite: $destination" }
        Assert-Hash $source $entry.sha256
    } else {
        # Resume only files already moved with exactly the inventoried bytes.
        Assert-Hash $destination $entry.sha256
    }
}

if (-not $VerifyOnly) {
    [IO.Directory]::CreateDirectory($archiveRoot) | Out-Null
    $externalManifest = Join-Path $archiveRoot 'archive-manifest.json'
    [IO.File]::WriteAllText($externalManifest, ($inventory | ConvertTo-Json -Depth 20) + "`n", [Text.UTF8Encoding]::new($false))
    foreach ($entry in $inventory.entries) {
        $source = [IO.Path]::GetFullPath($entry.source)
        $destination = [IO.Path]::GetFullPath((Join-Path $archiveRoot $entry.destination_relative))
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
            Move-Item -LiteralPath $source -Destination $destination
        }
        Assert-Hash $destination $entry.sha256
        if (Test-Path -LiteralPath $source) { throw "Source remains after move: $source" }
    }
    $inventory.status = 'completed'
    $inventory.verification = [pscustomobject]@{
        all_destination_hashes_match = $true
        all_original_sources_absent = $true
        verified_files = $inventory.file_count
        verified_at_utc = [DateTime]::UtcNow.ToString('o')
    }
    $json = ($inventory | ConvertTo-Json -Depth 20) + "`n"
    [IO.File]::WriteAllText($inventoryFullPath, $json, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText($externalManifest, $json, [Text.UTF8Encoding]::new($false))
    $readme = @'
# Falsified

Review/annotation artifacts and derived agreement reports moved here at the
maintainer's request on 2026-10-12. The directory name was requested by the
maintainer; this relocation does not independently establish artifact authorship.

Original relative paths and exact bytes are preserved. archive-manifest.json
lists every original source, destination, size and SHA256. The earlier external
Gemini/Nemotron archive was consolidated here; its original manifest is under
prior_archive/. Manuscript sources and historical records remain in the repo.

Only cached responses for the agreement annotation stage were moved. The
unrelated pipeline cache remains in place. Do not rerun the annotation workflow
to recreate these files or incur duplicate model charges.
'@
    [IO.File]::WriteAllText((Join-Path $archiveRoot 'README.md'), $readme + "`n", [Text.UTF8Encoding]::new($false))
}
Write-Output ("Verified {0} artifacts in {1}; all original sources absent." -f $inventory.file_count, $archiveRoot)
