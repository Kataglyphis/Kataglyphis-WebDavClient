# AGENTS.md

Guidance for coding agents (and new contributors) working in
Kataglyphis-WebDavClient.

Laid out per ContainerHub's
[`shared/templates/AGENTS.md.template`](ExternalLib/Kataglyphis-ContainerHub/shared/templates/README.md).
The rule that shapes it: *would this still be true in a different project?* If
yes, ContainerHub owns it and § 2 links to it. If no, it is written out in § 3.

## 1. What this project is

A Python package for talking to a WebDAV host. Python ≥ 3.10, managed with `uv`.
It builds a **binary** wheel, which is what makes its packaging lane differ from
the other Python repos here.

| Path | What lives there |
| --- | --- |
| `kataglyphis_webdavclient/` | The package — `webdavclient.py` is the substance |
| `tests/` | `unit/`, `integration/`, `fuzzy/`, `remote/`, plus `mock_webdav_server.py` |
| `bench/`, `demo/` | Benchmarks and a runnable example |
| `scripts/linux/` | Four ~15–30 line wrappers over ContainerHub's Python CI drivers |
| `scripts/windows/` | `Build-Windows.ps1` + the `Resolve-BuildModule.ps1` bootstrap |
| `ExternalLib/Kataglyphis-ContainerHub` | The submodule owning every reusable script, module and doc |

Distribution name and module name agree here (`kataglyphis_webdavclient`), so
upstream's `PACKAGE_NAME` derivation from `pyproject.toml` is correct and no
wrapper overrides it.

## 2. What ContainerHub owns — links only

**Do not restate these procedures here.** Start at
[`ExternalLib/Kataglyphis-ContainerHub/docs/INDEX.md`](ExternalLib/Kataglyphis-ContainerHub/docs/INDEX.md),
which maps topic → owning document, so these links survive upstream
reorganisation.

| Topic | Where |
| --- | --- |
| Wiring this repo to ContainerHub — resolver, actions, libraries | `docs/adopting-in-a-new-project.md` |
| Linux container builds | `docs/linux-build-basics.md` |
| Running Linux containers on a Windows host | `docs/rancher-desktop-linux-containers.md` |
| The Windows image, its entrypoint and known traps | `docs/windows-builds.md` |
| Bind mount vs tar-pipe, Dev Drive filter setup, container reuse | `docs/windows-container-build-performance.md` |
| Opting a commit into the heavy CI lanes | `docs/ci-build-triggers.md` |
| The five shell-safety bug classes | ContainerHub `AGENTS.md` § *Shell safety conventions* |

**The four `scripts/linux/ci_*.sh` are wrappers, not implementations.** Each is a
guard plus `exec bash "$_DRIVER"` into
`ExternalLib/Kataglyphis-ContainerHub/linux/scripts/02-toolchain/python/`. When
behaviour needs to change, change it **upstream** — a fix made in the wrapper is
a fix the other Python consumers never get.

| Wrapper | Upstream driver | Local addition |
| --- | --- | --- |
| `ci_tests.sh` | `python/ci_tests.sh` | none |
| `ci_static_analysis.sh` | `python/ci_static_analysis.sh` | none |
| `ci_build_docs.sh` | `python/ci_build_docs.sh` | none |
| `ci_packaging.sh` | `python/ci_packaging.sh` | installs `patchelf` — see § 3 |

Two upstream facts repeated here only because they bite before you reach a doc:

- Every ContainerHub PowerShell module declares `#requires -Version 7.0`, so
  `Build-Windows.ps1` does too — launch with `pwsh`, never `powershell`. Under
  5.1 it fails as an opaque `Import-Module` error.
- Composite actions resolve at `@main`, so a ContainerHub change a workflow
  depends on must be pushed **before** the consumer change.

**This repo's glue:** `scripts/windows/Resolve-BuildModule.ps1` — the one file
that cannot live upstream, because it is what *finds* the submodule. Note that
nested imports inside a `.psm1` are **module-private**, so every module you call
into must be named in the `Import-BuildModule` list explicitly.

## 3. Pitfalls specific to this project

Everything here is false or meaningless in another repo — that is why it is
written out rather than linked.

- **`ci_packaging.sh` keeps one local step: `patchelf`.** The binary wheel needs
  its RPATHs repaired on the runner and upstream's driver does not install it.
  This stays local deliberately — no second consumer needs it, and the
  two-consumer rule says one consumer is not enough to justify going upstream.
  If a second binary-wheel project appears, move it up then.
- **`WORKSPACE_ROOT` must be exported by every wrapper.** Upstream's
  `detect_workspace` derives it from the sourcing script's location, which for a
  *delegated* driver resolves inside `ExternalLib/Kataglyphis-ContainerHub/` —
  so every tool would run against the submodule tree instead of this repo. Each
  wrapper pins it to the repo root; `detect_workspace` honours a pre-set value
  and still overrides to `/workspace` in the container, so CI is unaffected.
  This is the single most likely thing to break if a wrapper is "simplified".
- **Do not re-add a `PACKAGE_NAME` default.** The pre-wrapper `ci_tests.sh`
  defaulted it to `orchestr_ant_ion` — the *sibling* project's name, copy-pasted.
  It only ever worked because CI passed the name explicitly. Upstream derives it
  from `pyproject.toml`, which is why that class of bug cannot recur; hardcoding
  it again reintroduces the failure mode.
- **`tests/remote/` talks to a real host.** The offline path is
  `tests/mock_webdav_server.py`; `tests/remote/data` holds its fixtures. Do not
  assume a plain `pytest` run exercises the remote lane.
- **There is no Flutter step here.** The pre-wrapper `ci_build_docs.sh` put
  `$WORKSPACE_ROOT/flutter/bin` on `PATH`, copied from a Flutter sibling. It was
  dropped rather than ported — if you see it reappear, it is copy-paste.

## 4. Build, run, test

```bash
uv sync

bash scripts/linux/ci_tests.sh           # pytest + coverage
bash scripts/linux/ci_static_analysis.sh # lint + type check
bash scripts/linux/ci_build_docs.sh      # Sphinx
bash scripts/linux/ci_packaging.sh       # binary wheel + sdist (installs patchelf)
```

Windows:

```powershell
pwsh -NoProfile -File .\scripts\windows\Build-Windows.ps1
```

CI lanes: `.github/workflows/ubuntu-24.04-amd64-arm64.yml` (native x86-64 and
arm64) and `.github/workflows/windows-2025.yml`.

## 5. Docs owned by this repo

- Sphinx sources in `docs/`.
- `CHANGELOG.md` and `VERSION.txt` — the version is read from `VERSION.txt`, so
  bump it there.
- Update docs in the same PR as user-facing behaviour changes.
