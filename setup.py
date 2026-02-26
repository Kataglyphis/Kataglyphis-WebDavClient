"""Build configuration for packaging and optional Cython compilation."""

import base64
import hashlib
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


LOGGER = logging.getLogger(__name__)


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except Exception:
    _bdist_wheel = None

# Accept several truthy values for CYTHONIZE (so "True", True, "1", "true" all work)
CYTHONIZE_RAW = os.getenv("CYTHONIZE", "0")
CYTHONIZE = str(CYTHONIZE_RAW).strip().lower() in ("1", "true", "yes", "on")

if CYTHONIZE:
    from Cython.Build import cythonize

# Compiler-Env will be set based on OS
if sys.platform == "win32":
    os.environ["CC"] = "clang-cl"
    os.environ["CXX"] = "clang-cl"
    os.environ["DISTUTILS_USE_SDK"] = "1"
else:
    os.environ.pop("DISTUTILS_USE_SDK", None)
    # I really like clang
    os.environ.setdefault("CC", "clang")
    os.environ.setdefault("CXX", "clang")


class StripWheel(_bdist_wheel if _bdist_wheel is not None else object):
    """Build the wheel, then rewrite it to exclude source files (.py, .pyc, .c, etc.).

    and rebuild the .dist-info/RECORD so the wheel remains valid.

    - Use ZipInfo objects and preserve file metadata where possible.
    - Skip directory entries and signature files (RECORD.jws, .asc, .sig, .jws)
    - Correctly compute sha256 and sizes for binary files and write a valid RECORD
    - Avoid writing RECORD into itself when computing hashes
    - Replace the original wheel atomically
    """

    exclude_suffixes = (".py", ".pyc", ".pyo", ".c", ".h", ".pxd", ".pyi")

    def run(self) -> None:
        """Build wheel artifacts and strip source files from resulting wheels."""
        # Run the normal wheel build if available
        if _bdist_wheel is not None:
            super().run()
        else:
            # fallback: let setuptools create dist/ wheel via other commands
            error_message = "wheel bdist_wheel not available; install 'wheel' package"
            raise RuntimeError(error_message)

        dist_dir = Path(getattr(self, "dist_dir", "dist"))
        # find the newly created wheel(s)
        for wheel_path in dist_dir.iterdir():
            if wheel_path.suffix != ".whl":
                continue
            self._strip_wheel(wheel_path)

    def _strip_wheel(self, wheel_path: Path | str) -> None:
        wheel_path = Path(wheel_path)
        dirname = wheel_path.parent
        tmpfd, tmpname = tempfile.mkstemp(suffix=".whl", dir=dirname)
        os.close(tmpfd)
        tmp_path = Path(tmpname)

        try:
            with zipfile.ZipFile(wheel_path, "r") as zin:
                zin_infos = zin.infolist()

                # locate the dist-info RECORD path
                dist_info_record = next(
                    (
                        zi.filename
                        for zi in zin_infos
                        if zi.filename.endswith(".dist-info/RECORD")
                    ),
                    None,
                )
                if dist_info_record is None:
                    # try to find dist-info directory if RECORD missing (very unlikely)
                    dist_info_dir = next(
                        (
                            zi.filename
                            for zi in zin_infos
                            if zi.filename.endswith(".dist-info/")
                        ),
                        None,
                    )
                    if dist_info_dir is None:
                        error_message = (
                            "Could not locate .dist-info directory inside wheel"
                        )
                        raise RuntimeError(error_message)
                    dist_info_record = dist_info_dir + "RECORD"
                else:
                    dist_info_dir = dist_info_record.rsplit("/", 1)[0] + "/"

                kept_infos = []  # list of (ZipInfo, data)

                # Determine which files to keep
                for zi in zin_infos:
                    name = zi.filename
                    # skip directory entries
                    if name.endswith("/"):
                        continue
                    # skip the original RECORD (we regenerate it)
                    if name == dist_info_record:
                        continue
                    # skip signature files under dist-info (they would be invalid after we modify RECORD)
                    if name.startswith(dist_info_dir) and name.lower().endswith(
                        (".jws", ".asc", ".sig")
                    ):
                        # skip signatures
                        continue
                    # skip excluded suffixes
                    if any(name.endswith(suf) for suf in self.exclude_suffixes):
                        continue
                    # keep everything else
                    data = zin.read(name)
                    kept_infos.append((zi, data))

            # Write kept files into new wheel and compute RECORD entries
            record_lines = []
            with zipfile.ZipFile(
                tmpname, "w", compression=zipfile.ZIP_DEFLATED
            ) as zout:
                for zi, data in kept_infos:
                    # preserve original ZipInfo metadata where possible
                    new_zi = zipfile.ZipInfo(filename=zi.filename)
                    # copy date_time and external_attr to preserve timestamps and permissions
                    new_zi.date_time = zi.date_time
                    new_zi.external_attr = zi.external_attr

                    # write entry
                    zout.writestr(new_zi, data)

                    # compute hash and size for RECORD
                    h = hashlib.sha256(data).digest()
                    b64 = base64.urlsafe_b64encode(h).rstrip(b"=").decode("ascii")
                    size = str(len(data))
                    record_lines.append(f"{zi.filename},sha256={b64},{size}")

                # Add the new RECORD file with entries computed above.
                # RECORD itself has an empty hash and size.
                record_content = "\n".join(
                    [*record_lines, f"{dist_info_dir}RECORD,,"]
                ).encode("utf-8")

                # create ZipInfo for RECORD and set reasonable permissions
                record_zi = zipfile.ZipInfo(filename=dist_info_dir + "RECORD")
                record_zi.date_time = (1980, 1, 1, 0, 0, 0)
                # set rw-r--r-- permissions
                record_zi.external_attr = (0o644 & 0xFFFF) << 16
                zout.writestr(record_zi, record_content)

            # replace original wheel with the stripped one
            shutil.move(tmpname, wheel_path)
            LOGGER.info("Stripped wheel written: %s", wheel_path)
        finally:
            # cleanup tmp file if it still exists
            if tmp_path.exists():
                tmp_path.unlink()


class ClangBuildExt(build_ext):
    """Under windows i bend the compiler to be clang-cl!!!

    Open source >>> closed source
    """

    def build_extension(self, ext: Extension) -> None:
        """Build one extension and map MSVC toolchain calls to LLVM binaries."""
        if self.compiler.compiler_type == "msvc":
            original_spawn = self.compiler.spawn

            def clang_spawn(cmd: Sequence[str]) -> object:
                if not cmd:
                    return original_spawn(cmd)

                exe = cmd[0].strip('"')  # remove surrounding quotes if any
                name = Path(exe).name.lower()

                if name in {"cl.exe", "cl"}:
                    cmd[0] = "clang-cl"
                elif name in {"link.exe", "link"}:
                    cmd[0] = "lld-link.exe"

                return original_spawn(cmd)

            self.compiler.spawn = clang_spawn

            if hasattr(self.compiler, "cc"):
                self.compiler.cc = "clang-cl"
            if hasattr(self.compiler, "linker_so"):
                self.compiler.linker_so = "lld-link"
            if hasattr(self.compiler, "linker"):
                self.compiler.linker = "lld-link"

        super().build_extension(ext)


package_dir = "kataglyphis_webdavclient"
version = Path("VERSION.txt").read_text().strip()


def list_py_files(package_dir: str) -> list[str]:
    """Return all Python module file paths under the package directory."""
    return [str(path) for path in Path(package_dir).rglob("*.py")]


py_files = list_py_files(package_dir)

extensions = []
if CYTHONIZE:
    if sys.platform == "win32":
        extra_compile_args = ["/O2", "/MD"]
        extra_link_args = ["/OPT:REF", "/OPT:ICF", "/LTCG:OFF"]
    else:
        extra_compile_args = ["-O3", "-flto", "-fvisibility=hidden"]
        extra_link_args = ["-flto"]

    extensions = [
        Extension(
            py_file.replace(os.path.sep, ".")[:-3],  # + "_compiled",
            [py_file],
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
        )
        for py_file in py_files
    ]

setup_kwargs = {"name": package_dir, "version": version, "zip_safe": False}

if CYTHONIZE:
    # merge cmdclasses
    cmds = {"build_ext": ClangBuildExt}
    if _bdist_wheel is not None:
        cmds["bdist_wheel"] = StripWheel
    setup_kwargs.update(
        {
            "ext_modules": cythonize(
                extensions,
                compiler_directives={
                    "language_level": "3",
                    "emit_code_comments": False,
                    "linetrace": False,
                    "embedsignature": False,
                    "binding": False,
                    "profile": False,
                    "annotation_typing": False,
                    "initializedcheck": False,
                    "warn.undeclared": False,
                    "infer_types": False,
                },
            ),
            "cmdclass": cmds,  # {"build_ext": ClangBuildExt},
            "package_data": {"": ["*.c", "*.so", "*.pyd"]},
        }
    )
else:
    setup_kwargs.update({"packages": [package_dir], "include_package_data": True})

setup(**setup_kwargs)
