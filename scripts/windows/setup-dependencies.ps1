Param(
    [string]$ClangVersion  = '21.1.1',
    [string]$VulkanVersion = '1.4.341.1',
    [string]$VulkanSdkPath = 'C:\VulkanSDK'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$containerHubModulesPath = Join-Path $repoRoot "ExternalLib\Kataglyphis-ContainerHub\windows\scripts\modules"
$sharedModulePath = Join-Path $containerHubModulesPath "WindowsScripts.Shared.psm1"

if (-not (Test-Path -Path $sharedModulePath)) {
    throw "Required shared module not found: $sharedModulePath"
}

Import-Module $sharedModulePath -Force

Write-Host "=== Installing build dependencies on Windows ==="

Write-Host "Installing LLVM/Clang $ClangVersion..."
winget install --accept-source-agreements --accept-package-agreements --id=LLVM.LLVM -v $ClangVersion -e

Write-Host "Installing Ninja via winget..."
winget install --accept-source-agreements --accept-package-agreements --id=Ninja-build.Ninja -e

Write-Host "Installing Ccache..."
winget install --accept-source-agreements --accept-package-agreements --id=Ccache.Ccache -e

if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Scoop..."
    iwr -useb get.scoop.sh | iex
}

Write-Host "Installing sccache via Scoop..."
scoop install sccache
sccache --version
sccache -s

Write-Host "Installing CMake, Cppcheck, NSIS..."
winget install --accept-source-agreements --accept-package-agreements cmake cppcheck nsis

Write-Host "Installing WiX Toolset..."
winget install --accept-source-agreements --accept-package-agreements --id WiXToolset.WiXToolset -e

Write-Host "Installing Vulkan SDK $VulkanVersion..."
winget install --accept-source-agreements --accept-package-agreements --id KhronosGroup.VulkanSDK -v $VulkanVersion -e

$binPath = "${VulkanSdkPath}\${VulkanVersion}\Bin"
$libPath = "${VulkanSdkPath}\${VulkanVersion}\Lib"
$includePath = "${VulkanSdkPath}\${VulkanVersion}\Include"

foreach ($path in @($binPath, $libPath, $includePath)) {
    if (Test-Path $path) {
        Write-Host "Appending $path to GITHUB_PATH"
        $path | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
    } else {
        Write-Warning "Path not found: $path"
    }
}

$nsisPath = 'C:\Program Files (x86)\NSIS'
if (Test-Path $nsisPath) {
    Write-Host "Adding NSIS path to GITHUB_PATH: $nsisPath"
    $nsisPath | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
} else {
    Write-Warning "NSIS installation path not found at $nsisPath"
}

Write-Host "=== Dependency installation completed ==="