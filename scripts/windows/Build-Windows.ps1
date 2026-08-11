Param(
	[string[]]$PythonVersions = @("3.13", "3.14", "3.14t"),
	[string]$PackageName = "kataglyphis_webdavclient",
	[string]$LogDir = "logs",
	[switch]$StopOnError,  # Neuer Parameter: bei Fehler stoppen statt fortfahren
	[switch]$EnablePySpy
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

# Modules resolve through the shared bootstrap (a verbatim copy of
# ContainerHub's shared/windows/templates/Resolve-BuildModule.ps1) instead of a
# hard-coded submodule path: a module that moves upstream is picked up without
# editing this script, and a missing submodule reports the exact
# `git submodule update` command rather than a bare path.
. (Join-Path $PSScriptRoot 'Resolve-BuildModule.ps1')

# Dependency order: Shared, then Build, then what builds on them.
# (Import-BuildModule pulls WindowsScripts.Shared in regardless — a nested
# import inside a .psm1 is module-private and never reaches this session.)
Import-BuildModule @(
	'WindowsScripts.Shared'
	'WindowsBuild.Common'
	'WindowsUv.Common'
)

$script:BuildContext = New-BuildContext -Workspace $repoRoot -LogDir $LogDir -StopOnError:$StopOnError
$script:BuildContext.SuppressConsoleOutput = $true
$logPath = $script:BuildContext.LogPath
$script:CreatedUvEnvs = New-Object System.Collections.Generic.List[string]

# Tracking fÃ¼r Erfolg/Fehler

# NOTE: Results.SoftFailed / Results.SoftErrors used to be hand-added here for
# the local Invoke-Step fork. New-BuildContext already creates AllowedFailures,
# Errors and Durations, which the upstream Invoke-BuildStep populates instead.
$script:Results = $script:BuildContext.Results

function Close-Log {
	Close-BuildLog -Context $script:BuildContext
}

function Write-ImportantConsoleMessage {
	param(
		[Parameter(Mandatory)]
		[AllowEmptyString()]
		[string]$Message,
		[ValidateSet('Info', 'Warning', 'Error', 'Success')]
		[string]$Level = 'Info'
	)

	if (-not $Message) {
		Write-Host ''
		return
	}

	switch ($Level) {
		'Warning' {
			Write-Warning $Message
		}
		'Error' {
			Write-Host $Message -ForegroundColor Red
		}
		'Success' {
			Write-Host $Message -ForegroundColor Green
		}
		default {
			Write-Host $Message
		}
	}
}

function Test-IsImportantLogMessage {
	param(
		[Parameter(Mandatory)]
		[AllowEmptyString()]
		[string]$Message
	)

	if (-not $Message) {
		return $true
	}

	return $Message -match '^(===|>>>|<<<|Total:|Repo root:|Logging all output to:|Stop on error:|Unhandled critical error:|Stack trace:|--- Python )'
}

function Write-Log {
	param(
		[Parameter(Mandatory)]
		[AllowEmptyString()]
		[string]$Message
	)

	if (Test-IsImportantLogMessage -Message $Message) {
		Write-ImportantConsoleMessage -Message $Message
	}

	Write-BuildLog -Context $script:BuildContext -Message $Message
}

function Write-LogWarning {
	param(
		[Parameter(Mandatory)]
		[AllowEmptyString()]
		[string]$Message
	)

	Write-ImportantConsoleMessage -Message $Message -Level Warning
	Write-BuildLogWarning -Context $script:BuildContext -Message $Message
}

function Write-LogError {
	param(
		[Parameter(Mandatory)]
		[AllowEmptyString()]
		[string]$Message
	)

	Write-ImportantConsoleMessage -Message $Message -Level Error
	Write-BuildLogError -Context $script:BuildContext -Message $Message
}

function Write-LogSuccess {
	param(
		[Parameter(Mandatory)]
		[AllowEmptyString()]
		[string]$Message
	)

	Write-ImportantConsoleMessage -Message $Message -Level Success
	Write-BuildLogSuccess -Context $script:BuildContext -Message $Message
}

Open-BuildLog -Context $script:BuildContext

Write-Log "=== Windows build/test pipeline (PowerShell) ==="
Write-Log "Repo root: $repoRoot"
Write-Log "Logging all output to: $logPath"
Write-Log "Stop on error: $StopOnError"

function Invoke-Optional {
	param(
		[scriptblock]$Script,
		[string]$Name
	)

	Invoke-BuildOptional -Context $script:BuildContext -Script $Script -Name $Name
}

function Invoke-External {
	param(
		[Parameter(Mandatory)]
		[string]$File,
		[Alias('Args')]
		[string[]]$CommandArgs = @()
	)

	Invoke-BuildExternal -Context $script:BuildContext -File $File -Parameters $CommandArgs | Out-Null
}

$script:UvCommandRunner = {
	param([string]$File, [string[]]$CommandArgs)
	Invoke-BuildExternal -Context $script:BuildContext -File $File -Parameters $CommandArgs | Out-Null
}

$script:UvLogInfo = {
	param([string]$Message)
	Write-BuildLog -Context $script:BuildContext -Message $Message
}

$script:UvLogWarning = {
	param([string]$Message)
	Write-BuildLogWarning -Context $script:BuildContext -Message $Message
}

function New-UvEnvironment {
	param(
		[string]$PythonVersion,
		[string]$EnvName
	)

	$envPath = New-UvProjectEnvironment -Workspace $repoRoot -PythonVersion $PythonVersion -EnvName $EnvName -CommandRunner $script:UvCommandRunner -LogInfo $script:UvLogInfo -LogWarning $script:UvLogWarning
	$script:CreatedUvEnvs.Add($envPath) | Out-Null

	return $envPath
}

function Remove-UvEnvironment {
	param(
		[string]$EnvPath
	)

	Remove-UvProjectEnvironment -EnvPath $EnvPath -LogInfo $script:UvLogInfo -LogWarning $script:UvLogWarning
}

function Sync-ProjectDependencies {
	param(
		[switch]$NoBuildIsolationPackageWxPython,
		[switch]$UseLocked
	)

	Sync-UvProjectDependencies -NoBuildIsolationPackageWxPython:$NoBuildIsolationPackageWxPython -UseLocked:$UseLocked -CommandRunner $script:UvCommandRunner -LogInfo $script:UvLogInfo
}

function Ensure-TestResultsDir {
	New-Item -ItemType Directory -Force "docs/test_results" | Out-Null
}

# Neue Funktion: FÃ¼hrt einen Schritt aus und trackt Erfolg/Fehler

function Invoke-Step {
	# Delegates to ContainerHub's Invoke-BuildStep (WindowsBuild.Common), which
	# this script already imports. The local body replaced here was an older fork
	# of exactly that function - same parameters, same log format, same
	# StopOnError-and-Critical rethrow - but it tracked allowed failures in
	# hand-added Results.SoftFailed/SoftErrors instead of the AllowedFailures and
	# Errors that New-BuildContext already creates, and it had no timing.
	#
	# Delegating gains per-step durations and the machine-readable JSON summary
	# for free. Kept as a wrapper rather than editing every call site: the -Context
	# binding is the only thing those call sites would otherwise have to repeat.
	param(
		[Parameter(Mandatory)]
		[string]$StepName,
		[Parameter(Mandatory)]
		[scriptblock]$Script,
		[switch]$Critical,
		[switch]$AllowFailure
	)

	return Invoke-BuildStep -Context $script:BuildContext -StepName $StepName -Script $Script -Critical:$Critical -AllowFailure:$AllowFailure
}

function Write-Summary {
	# Delegates to ContainerHub's Write-BuildSummary. The 39-line local body this
	# replaced printed the same three sections from the same Results object; the
	# upstream one additionally reports per-step durations and writes the
	# machine-readable build-summary JSON to $Context.SummaryPath.
	Write-BuildSummary -Context $script:BuildContext
}

try {
	try {
		Ensure-TestResultsDir

		Write-Log "=== Pytest matrix (Windows) ==="

		foreach ($version in $PythonVersions) {
			$versionNumber = $null
			if ($version -match '^\d+(?:\.\d+)?') {
				try {
					$versionNumber = [version]$Matches[0]
				} catch {
					$versionNumber = $null
				}
			}
			$allowFailure = $false
			if ($versionNumber -and $versionNumber -ge [version]"3.14") {
				$allowFailure = $true
			}

			Invoke-Step -StepName "Python $version - Tests" -AllowFailure:$allowFailure -Script {
				Write-Log "--- Python $version ---"
				$envPath = New-UvEnvironment -PythonVersion $version -EnvName (".venv-$version")

				try {
					$useLocked = Test-Path -Path "uv.lock"
					if ($useLocked) {
						Sync-ProjectDependencies -NoBuildIsolationPackageWxPython -UseLocked
					} else {
						Sync-ProjectDependencies -NoBuildIsolationPackageWxPython
					}

					Invoke-External -File "uv" -Args @(
						"run", "pytest", "tests/unit", "-v",
						"--cov=$PackageName",
						"--cov-report=term-missing",
						"--cov-report=html:docs/test_results/coverage-html-$version",
						"--cov-report=xml:docs/test_results/coverage-$version.xml",
						"--junitxml=docs/test_results/report-$version.xml",
						"--html=docs/test_results/pytest-report-$version.html",
						"--self-contained-html",
						"--md-report",
						"--md-report-verbose=1",
						"--md-report-output",
						"docs/test_results/pytest-report-$version.md"
					)

					Invoke-External -File "uv" -Args @("run", "python", "bench/demo_cprofile.py")
					Invoke-External -File "uv" -Args @("run", "python", "bench/demo_line_profiler.py")
					# Invoke-External -File "uv" -Args @("run", "-m", "memory_profiler", "bench/demo_memory_profiling.py")
					if ($EnablePySpy) {
						Invoke-External -File "uv" -Args @("run", "py-spy", "record", "--rate", "200", "--duration", "45", "-o", "profile.svg", "--", "python", "bench/demo_py_spy.py")
					}
					Invoke-External -File "uv" -Args @("run", "pytest", "bench/demo_pytest_benchmark.py")
				} finally {
					Remove-UvEnvironment -EnvPath $envPath
				}
			} | Out-Null
		}

		Invoke-Step -StepName "Static Analysis (Python 3.13)" -Script {
			Write-Log "=== Static analysis (Python 3.13) ==="
			$envPath = New-UvEnvironment -PythonVersion "3.13" -EnvName ".venv-static"
			try {
				if (Test-Path -Path "uv.lock") {
					Sync-ProjectDependencies -NoBuildIsolationPackageWxPython -UseLocked
				} else {
					Sync-ProjectDependencies -NoBuildIsolationPackageWxPython
				}

				Invoke-Optional -Name "codespell" -Script {
					Invoke-External -File "uv" -Args @(
						"run", "codespell",
						"--skip", "./.venv/*,./logs/*,./docs/test_results/*,./docs/test_results/**,./resources/models/*.onnx,./resources/models/**/*.onnx"
					)
				}
				Invoke-Optional -Name "mypy" -Script { Invoke-External -File "uv" -Args @("run", "mypy", ".") }
				Invoke-Optional -Name "bandit" -Script { Invoke-External -File "uv" -Args @("run", "bandit", "-r", ".") }
				Invoke-Optional -Name "vulture" -Script { Invoke-External -File "uv" -Args @("run", "vulture", ".") }
				Invoke-Optional -Name "ruff" -Script { Invoke-External -File "uv" -Args @("run", "ruff", "check") }
				Invoke-Optional -Name "ty" -Script { Invoke-External -File "uv" -Args @("run", "ty", "check") }
			} finally {
				Remove-UvEnvironment -EnvPath $envPath
			}
		} | Out-Null

		Invoke-Step -StepName "Packaging (source)" -Script {
			Write-Log "=== Packaging (source) ==="
			$envPath = New-UvEnvironment -PythonVersion "3.13" -EnvName ".venv-packaging-sources"
			try {
				if (Test-Path -Path "uv.lock") {
					Sync-ProjectDependencies -NoBuildIsolationPackageWxPython -UseLocked
				} else {
					Sync-ProjectDependencies -NoBuildIsolationPackageWxPython
				}
				Invoke-External -File "uv" -Args @("build")
			} finally {
				Remove-UvEnvironment -EnvPath $envPath
			}
		} | Out-Null

		Invoke-Step -StepName "Packaging (Windows binaries)" -Script {
			Write-Log "=== Packaging (Windows binaries) ==="
			$env:CYTHONIZE = "True"

			$envPath = New-UvEnvironment -PythonVersion "3.13" -EnvName ".venv-packaging-binaries"
			try {
				if (Test-Path -Path "uv.lock") {
					Invoke-External -File "uv" -Args @("sync", "--locked", "--dev", "--all-extras")
				} else {
					Invoke-External -File "uv" -Args @("sync", "--dev", "--all-extras")
				}
				Invoke-External -File "uv" -Args @("build")
			} finally {
				Remove-UvEnvironment -EnvPath $envPath
			}
		} | Out-Null

		Write-Log "=== Completed Windows build/test pipeline ==="

	} catch {
		Write-LogError "Unhandled critical error: $($_.Exception.Message)"
		if ($_.ScriptStackTrace) {
			Write-LogError "Stack trace: $($_.ScriptStackTrace)"
		}
		throw
	}
} finally {
	# Cleanup aller Environments
	foreach ($envPath in $script:CreatedUvEnvs) {
		Remove-UvEnvironment -EnvPath $envPath
	}

	# Summary ausgeben
	Write-Summary

	Close-Log

	# Exit-Code basierend auf Fehlern
	if ($script:Results.Failed.Count -gt 0) {
		exit 1
	}
}

