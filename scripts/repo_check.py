#!/usr/bin/env python3
"""No-Podman checks for docs, recipes, and helper scripts."""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from trial_runner import TrialError, load_simple_yaml, normalize_trial  # noqa: E402


REQUIRED_FILES = [
    ".containerignore",
    ".dockerignore",
    ".gitattributes",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/hardware_bringup.yml",
    ".github/ISSUE_TEMPLATE/trial_recipe.yml",
    ".github/ISSUE_TEMPLATE/workflow_example.yml",
    ".github/workflows/publish-runtime-image.yml",
    ".github/workflows/repo-check.yml",
    "LICENSE",
    "NOTICE",
    "README.md",
    "CONTRIBUTING.md",
    "CITATION.cff",
    "SECURITY.md",
    "Containerfile",
    "Makefile",
    "compose.yaml",
    "scripts/trial_evaluator.py",
    "docs/quickstart.md",
    "docs/container-quickstart.md",
    "docs/workflow-guide.md",
    "docs/component-swap-guide.md",
    "docs/hardware-bom.md",
    "docs/hardware-readiness-checklist.md",
    "docs/object-search-and-approach.md",
    "docs/reproducibility.md",
    "docs/logging-spec.md",
    "docs/asset-attribution.md",
    "docs/preview-release-notes.md",
    "docs/runtime-image-release.md",
    "docs/troubleshooting.md",
    "docs/visual-media-guide.md",
    "docs/assets/openhri-logo.svg",
    "docs/assets/openhri-wordmark.svg",
    "docs/assets/media/office-bot-object-hunt-demo.mp4",
    "docs/assets/media/office-bot-object-hunt-demo-poster.jpg",
    "recipes/trials/bottle-demo.yaml",
    "recipes/trials/bottle-tabletop.yaml",
    "recipes/trials/chair-occluded.yaml",
    "recipes/trials/chair-visible.yaml",
    "recipes/trials/memory-stale-object.yaml",
    "recipes/trials/sofa-visible.yaml",
]

TEXT_SUFFIXES = {
    ".cff",
    ".cfg",
    ".cmake",
    ".conf",
    ".config",
    ".cpp",
    ".css",
    ".desktop",
    ".h",
    ".hpp",
    ".html",
    ".json",
    ".launch",
    ".material",
    ".md",
    ".mtl",
    ".names",
    ".obj",
    ".part",
    ".py",
    ".rviz",
    ".sdf",
    ".sh",
    ".svg",
    ".txt",
    ".urdf",
    ".world",
    ".xacro",
    ".xml",
    ".yaml",
    ".yml",
}

TEXT_FILENAMES = {
    ".containerignore",
    ".dockerignore",
    ".gitattributes",
    ".gitignore",
    "CMakeLists.txt",
    "Containerfile",
    "LICENSE",
    "Makefile",
}

SKIP_PARTS = {
    ".agents",
    ".codex",
    ".git",
    ".pytest_cache",
    ".serena",
    "__pycache__",
    "build",
    "install",
    "log",
}

GENERATED_DIR_NAMES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}

GENERATED_FILE_NAMES = {
    ".DS_Store",
}

GENERATED_SUFFIXES = {
    ".bag",
    ".db3",
    ".engine",
    ".mcap",
    ".mov",
    ".mp4",
    ".onnx",
    ".pt",
    ".pth",
    ".pyc",
    ".pyo",
    ".zip",
}

PUBLIC_MEDIA_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".mp4",
    ".png",
    ".webp",
}

MAX_PUBLIC_VIDEO_BYTES = 25 * 1024 * 1024
MAX_PUBLIC_IMAGE_BYTES = 2 * 1024 * 1024

PRIVATE_PATTERNS = [
    re.compile(r"/Users/[^)\s]+"),
    re.compile(r"/home/thedevmanek"),
    re.compile(r"office_bot/dev_ws"),
    re.compile(r"2256f0d3bfc7"),
    re.compile(r"d61712ae6423f349c13cfec6c521edba8b765495"),
]

FORBIDDEN_RELEASE_TERMS = [
    "OpenHRI Office",
    "Office Simulation",
    "research preview",
    "researcher",
    "TODO",
    "FIXME",
    "TBD",
    "WIP",
    "actor_walk",
    "office_bot_hardware",
    "researcher_session.py",
    "docs/demo-script.md",
    "docs/researcher-guide.md",
    "docs/study-ideas",
    "experiments/trials/bottle-demo.yaml",
]

LINK_RE = re.compile(r"!?\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    failures: list[str] = []
    failures.extend(check_required_files())
    failures.extend(check_markdown_links())
    failures.extend(check_trial_templates())
    failures.extend(check_no_generated_artifacts())
    failures.extend(check_public_media())
    failures.extend(check_private_strings())
    failures.extend(check_forbidden_release_terms())
    failures.extend(check_public_naming())
    failures.extend(check_ros_package_metadata())
    failures.extend(check_xml_files())
    failures.extend(check_package_uris())
    failures.extend(check_model_uris())
    failures.extend(check_xacro_mesh_uris())
    failures.extend(check_asset_attribution())
    failures.extend(check_executable_metadata())
    failures.extend(check_git_attributes())
    failures.extend(check_text_line_endings())

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("repo-check: ok")
    return 0


def check_required_files() -> list[str]:
    failures = []
    for rel in REQUIRED_FILES:
        if not (REPO_ROOT / rel).is_file():
            failures.append(f"missing required file: {rel}")
    return failures


def check_markdown_links() -> list[str]:
    failures = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            for raw_target in LINK_RE.findall(line):
                target = clean_markdown_target(raw_target)
                if not target or is_external_link(target) or target.startswith("#"):
                    continue
                target_path = (path.parent / target).resolve()
                try:
                    target_path.relative_to(REPO_ROOT)
                except ValueError:
                    failures.append(
                        f"{relative(path)}:{line_no}: link leaves repo: {raw_target}"
                    )
                    continue
                if not target_path.exists():
                    failures.append(
                        f"{relative(path)}:{line_no}: missing link target: {raw_target}"
                    )
    return failures


def check_trial_templates() -> list[str]:
    failures = []
    trial_dir = REPO_ROOT / "recipes" / "trials"
    for recipe_path in sorted(trial_dir.glob("*.yaml")):
        try:
            recipe = load_simple_yaml(recipe_path)
            normalize_trial(recipe, "", recipe_path)
        except TrialError as exc:
            failures.append(f"{relative(recipe_path)}: invalid trial recipe: {exc}")
            continue

        if recipe_path.name == "bottle-demo.yaml":
            if not str(recipe.get("operator_setup") or "").strip():
                failures.append(
                    f"{relative(recipe_path)}: runnable recipe must document operator_setup"
                )
            continue

        if recipe.get("template") is not True:
            failures.append(
                f"{relative(recipe_path)}: template recipe must set template: true"
            )
        if not str(recipe.get("operator_setup") or "").strip():
            failures.append(
                f"{relative(recipe_path)}: recipe must document operator_setup"
            )
        status = str(recipe.get("template_status") or "")
        if "template only" not in status.lower():
            failures.append(
                f"{relative(recipe_path)}: template recipe must explain template_status"
            )
    return failures


def check_no_generated_artifacts() -> list[str]:
    failures = []
    skip_parts = {".git", ".serena", "build", "install", "log"}
    for path in REPO_ROOT.rglob("*"):
        rel_parts = path.relative_to(REPO_ROOT).parts
        if skip_parts.intersection(rel_parts):
            continue
        if path.is_dir() and path.name in GENERATED_DIR_NAMES:
            failures.append(f"{relative(path)}: generated cache directory is present")
        if not path.is_file():
            continue
        if path.name in GENERATED_FILE_NAMES:
            failures.append(f"{relative(path)}: generated local file is present")
        if path.suffix.lower() in GENERATED_SUFFIXES and not is_public_media_asset(path):
            failures.append(f"{relative(path)}: generated artifact is present")
    return failures


def check_public_media() -> list[str]:
    failures = []
    media_root = REPO_ROOT / "docs" / "assets" / "media"
    if not media_root.exists():
        return failures
    for path in sorted(media_root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in PUBLIC_MEDIA_SUFFIXES:
            failures.append(f"{relative(path)}: unsupported public media type")
            continue
        size = path.stat().st_size
        if suffix == ".mp4" and size > MAX_PUBLIC_VIDEO_BYTES:
            failures.append(f"{relative(path)}: public video is too large")
        if suffix in {".jpg", ".jpeg", ".png", ".webp"} and size > MAX_PUBLIC_IMAGE_BYTES:
            failures.append(f"{relative(path)}: public image is too large")
    return failures


def check_private_strings() -> list[str]:
    failures = []
    for path in text_releasable_files(include_untracked=True):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if path.name == "repo_check.py" and "re.compile" in line:
                continue
            for pattern in PRIVATE_PATTERNS:
                if pattern.search(line):
                    failures.append(
                        f"{relative(path)}:{line_no}: private/local string leaked"
                    )
    return failures


def check_forbidden_release_terms() -> list[str]:
    failures = []
    for path in text_releasable_files(include_untracked=True):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if path.name == "repo_check.py":
                continue
            for term in FORBIDDEN_RELEASE_TERMS:
                if term in line:
                    failures.append(
                        f"{relative(path)}:{line_no}: stale release term: {term}"
                    )
    return failures


def check_public_naming() -> list[str]:
    required_snippets = {
        "README.md": "`office_bot` is the reference office-robot project inside OpenHRI",
        "CITATION.cff": 'title: "OpenHRI office_bot"',
        "NOTICE": "`office_bot`, the reference office-robot project within",
        "docs/preview-release-notes.md": "`office_bot`, the reference",
    }
    failures = []
    for rel, snippet in required_snippets.items():
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        if snippet not in text:
            failures.append(
                f"{rel}: missing OpenHRI umbrella / office_bot project naming"
            )
    return failures


def check_ros_package_metadata() -> list[str]:
    failures = []
    for path in sorted((REPO_ROOT / "dev_ws" / "src").glob("*/package.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            failures.append(f"{relative(path)}: invalid package.xml: {exc}")
            continue

        name = root.findtext("name") or path.parent.name
        version = root.findtext("version")
        description = (root.findtext("description") or "").strip()
        license_name = root.findtext("license")
        build_type = root.findtext("export/build_type")
        buildtool_deps = {
            (node.text or "").strip() for node in root.findall("buildtool_depend")
        }
        if version != "0.1.0":
            failures.append(f"{relative(path)}: expected version 0.1.0, got {version!r}")
        if not description or description in {name, "TODO: Package description"}:
            failures.append(f"{relative(path)}: description is not release-ready")
        if license_name != "Apache-2.0":
            failures.append(
                f"{relative(path)}: expected Apache-2.0 license, got {license_name!r}"
            )
        if build_type == "ament_python" and "ament_python" not in buildtool_deps:
            failures.append(f"{relative(path)}: missing buildtool_depend ament_python")
    return failures


def check_xml_files() -> list[str]:
    failures = []
    suffixes = {".sdf", ".urdf", ".world", ".xacro", ".xml"}
    for path in releasable_files():
        if path.suffix.lower() not in suffixes and path.name != "model.config":
            continue
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            failures.append(f"{relative(path)}: invalid XML-like file: {exc}")
    return failures


def check_package_uris() -> list[str]:
    package_root = REPO_ROOT / "dev_ws" / "src" / "office_bot_model"
    if not package_root.exists():
        return []

    uri_re = re.compile(r"package://office_bot_model/([^\"\s<>]+)")
    suffixes = {".sdf", ".urdf", ".world", ".xacro", ".xml", ".rviz", ".yaml", ".yml"}
    failures = []
    for path in releasable_files(include_untracked=True):
        if path.suffix.lower() not in suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for rel in uri_re.findall(text):
            if "$" in rel or "{" in rel:
                continue
            if not (package_root / rel).exists():
                failures.append(
                    f"{relative(path)}: missing package URI package://office_bot_model/{rel}"
                )
    return failures


def check_model_uris() -> list[str]:
    model_root = REPO_ROOT / "dev_ws" / "src" / "office_bot_model" / "models"
    if not model_root.exists():
        return []

    resource_roots = [
        model_root,
        model_root / "worlds" / "office_world",
        model_root / "worlds" / "office_world" / "models",
    ]
    uri_re = re.compile(r"model://([^/<\s]+)(?:/([^<\s]*))?")
    failures = []
    for path in sorted(model_root.rglob("*")):
        if path.suffix.lower() not in {".sdf", ".world"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in uri_re.finditer(text):
            first = match.group(1)
            rest = match.group(2) or ""
            if not any((root / first / rest).exists() for root in resource_roots):
                failures.append(
                    f"{relative(path)}: missing model URI model://{first}/{rest}"
                )
    return failures


def check_xacro_mesh_uris() -> list[str]:
    model_package = REPO_ROOT / "dev_ws" / "src" / "office_bot_model"
    xacro_root = model_package / "models" / "officebot_xacro"
    mesh_root = model_package / "models" / "officebot"
    if not xacro_root.exists():
        return []

    failures = []
    mesh_re = re.compile(r"\$\{mesh_uri_prefix\}([^\"\s<>]+)")
    for path in sorted(xacro_root.glob("*.xacro")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for rel in mesh_re.findall(text):
            if not (mesh_root / rel).exists():
                failures.append(
                    f"{relative(path)}: missing xacro mesh reference {rel}"
                )
    return failures


def check_asset_attribution() -> list[str]:
    attribution_path = REPO_ROOT / "docs" / "asset-attribution.md"
    notice_path = REPO_ROOT / "NOTICE"
    model_root = REPO_ROOT / "dev_ws" / "src" / "office_bot_model" / "models"
    if not model_root.exists() or not attribution_path.exists():
        return []

    text = attribution_path.read_text(encoding="utf-8")
    notice_text = notice_path.read_text(encoding="utf-8") if notice_path.exists() else ""
    failures = []
    for path in sorted(model_root.glob("**/model.config")):
        rel = relative(path)
        if rel not in text:
            failures.append(f"{relative(attribution_path)}: missing model entry for {rel}")
    shared_media_roots = [
        "dev_ws/src/office_bot_model/models/worlds/office_world/media/",
        "dev_ws/src/office_bot_model/models/worlds/office_world/models/media/",
    ]
    for rel in shared_media_roots:
        if rel not in text:
            failures.append(
                f"{relative(attribution_path)}: missing shared media entry for {rel}"
            )
    required_phrases = [
        "license-review-required",
        "Commercial redistribution of bundled world assets requires upstream source and",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            failures.append(
                f"{relative(attribution_path)}: missing redistribution note phrase: {phrase}"
            )
    if "docs/asset-attribution.md" not in notice_text:
        failures.append("NOTICE: missing pointer to docs/asset-attribution.md")
    if "not relicensed" not in notice_text or "Apache-2.0" not in notice_text:
        failures.append("NOTICE: missing third-party asset license boundary")
    return failures


def check_executable_metadata() -> list[str]:
    failures = []
    for path in releasable_files(include_untracked=True):
        rel = relative(path)
        first_line = path.open("rb").readline()
        executable = bool(path.stat().st_mode & 0o111)
        has_shebang = first_line.startswith(b"#!")
        if has_shebang and not executable:
            failures.append(f"{rel}: has a shebang but is not executable")
        if executable and not has_shebang:
            failures.append(f"{rel}: is executable without a shebang")
    return failures


def check_git_attributes() -> list[str]:
    if not (REPO_ROOT / ".git").exists():
        return []

    failures = []
    for path in releasable_files(include_untracked=True):
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(REPO_ROOT),
                "check-attr",
                "text",
                "eol",
                "--",
                relative(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            failures.append(f"{relative(path)}: could not read git attributes")
            continue

        attrs = {}
        for line in completed.stdout.splitlines():
            try:
                _, attr, value = line.split(": ", 2)
            except ValueError:
                continue
            attrs[attr] = value

        text_attr = attrs.get("text")
        eol_attr = attrs.get("eol")
        if text_attr == "auto":
            failures.append(f"{relative(path)}: git text attribute is still auto")
        if text_attr == "set" and eol_attr != "lf":
            failures.append(f"{relative(path)}: git text file does not force LF")
    return failures


def check_text_line_endings() -> list[str]:
    failures = []
    for path in text_releasable_files(include_untracked=True):
        data = path.read_bytes()
        if b"\r\n" in data:
            failures.append(f"{relative(path)}: uses CRLF line endings")
        if data and not data.endswith(b"\n"):
            failures.append(f"{relative(path)}: missing final newline")
        for line_no, line in enumerate(data.splitlines(), 1):
            if line.rstrip(b" \t") != line:
                failures.append(f"{relative(path)}:{line_no}: trailing whitespace")
                break
    return failures


def markdown_files() -> list[Path]:
    return sorted(REPO_ROOT.glob("*.md")) + sorted((REPO_ROOT / "docs").glob("**/*.md"))


def text_releasable_files(include_untracked=False) -> list[Path]:
    files = []
    for path in releasable_files(include_untracked=include_untracked):
        if (
            path.name in TEXT_FILENAMES
            or path.suffix.lower() in TEXT_SUFFIXES
            or path.parent.name == "resource"
        ):
            files.append(path)
    return files


def releasable_files(include_untracked=False) -> list[Path]:
    files = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or SKIP_PARTS.intersection(path.relative_to(REPO_ROOT).parts):
            continue
        if not include_untracked and is_untracked(path):
            continue
        files.append(path)
    return sorted(files)


def is_untracked(path: Path) -> bool:
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        return False
    import subprocess

    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", relative(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode != 0


def is_public_media_asset(path: Path) -> bool:
    media_root = REPO_ROOT / "docs" / "assets" / "media"
    try:
        path.resolve().relative_to(media_root)
    except ValueError:
        return False
    return path.suffix.lower() in PUBLIC_MEDIA_SUFFIXES


def clean_markdown_target(raw_target: str) -> str:
    target = raw_target.strip().strip("<>")
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return unquote(target)


def is_external_link(target: str) -> bool:
    lowered = target.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
