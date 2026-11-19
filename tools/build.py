#!/usr/bin/env python3
"""Build a static Moader repository using Python 3.10+."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9_-]{1,48}")
TITLE_ID = re.compile(r"0[14][0-9A-F]{14}")
LIMIT = 128 * 1024 * 1024


def check(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    check(path.is_file() and not path.is_symlink(), f"Expected a regular file at {path}")
    return json.loads(path.read_bytes())


def string(obj, key, limit):
    value = obj.get(key)
    check(
        isinstance(value, str) and value.strip() and len(value.encode()) <= limit, f"Invalid {key}"
    )
    return value.strip()


def https(value):
    p = urlsplit(value)
    check(
        p.scheme == "https"
        and p.hostname
        and not p.username
        and not p.password
        and not any(c.isspace() or c in "<>\\" or ord(c) < 32 for c in value),
        f"Invalid HTTPS URL {value!r}",
    )
    return value


def archive(source, output):
    check(source.is_dir() and not source.is_symlink(), f"Missing payload in {source.parent.name}")
    files, total, names = [], 0, set()
    for path in sorted(source.rglob("*")):
        check(not path.is_symlink(), f"Symlink in payload at {path}")
        if path.is_dir():
            continue
        name = path.relative_to(source).as_posix()
        check(
            path.is_file()
            and len(name.encode()) <= 220
            and all(c not in '\\:<>"|?*' and ord(c) >= 32 for c in name),
            f"Invalid payload path {name}",
        )
        check(name.casefold() not in names, f"Duplicate path on SD {name}")
        names.add(name.casefold())
        check(
            all(not part.endswith((".", " ")) for part in path.relative_to(source).parts),
            f"Invalid SD filename {name}",
        )
        check(
            name.startswith(("romfs/", "exefs/", "exefs_patches/"))
            or name in ("romfs.bin", "exefs.nsp"),
            f"Use a supported Moader payload root for {name}",
        )
        file_size = path.stat().st_size
        check(file_size <= 64 * 1024 * 1024, f"{name} exceeds the 64 MiB file limit")
        total += file_size
        check(
            total <= 256 * 1024 * 1024 and len(files) < 4096, "Package exceeds file or size limits"
        )
        files.append((name, path))
    check(files, "Empty mod payload")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, path in files:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes())
    data = output.read_bytes()
    check(len(data) <= LIMIT, "Compressed archive exceeds 128 MiB")
    return len(data), hashlib.sha256(data).hexdigest()


def build(base, dest):
    repo = read_json(ROOT / "repository.json")
    name = string(repo, "name", 120)
    games = {}
    for entry in repo["games"]:
        title_id = string(entry, "titleId", 16).upper()
        check(
            TITLE_ID.fullmatch(title_id) and title_id not in games,
            f"Invalid or repeated Title ID {title_id}",
        )
        games[title_id] = {"titleId": title_id, "title": string(entry, "title", 200), "mods": []}
    check(0 < len(games) <= 256, "List between 1 and 256 games")
    shutil.copytree(ROOT / "site", dest, dirs_exist_ok=True)
    pages = dest / "packages"
    pages.mkdir()
    assets = dest / "previews"
    assets.mkdir()
    for f in sorted((ROOT / "mods").glob("*/mod.json")):
        check(not f.parent.is_symlink(), "Mod directories must be regular directories")
        m = read_json(f)
        mid = string(m, "id", 48)
        tid = string(m, "titleId", 16).upper()
        check(
            SLUG.fullmatch(mid) and f.parent.name == mid and tid in games,
            f"Invalid mod ID or Title ID at {f}",
        )
        entry = {
            k: string(m, k, n)
            for k, n in [
                ("id", 48),
                ("title", 200),
                ("author", 250),
                ("category", 40),
                ("summary", 2048),
                ("description", 4096),
                ("version", 64),
                ("published", 64),
                ("license", 100),
            ]
        }
        check(re.fullmatch(r"[a-zA-Z0-9._+-]{1,64}", entry["version"]), "Use a path-safe version")
        datetime.date.fromisoformat(entry["published"])
        folder = pages / tid / mid
        folder.mkdir(parents=True)
        package = folder / (mid + "-" + entry["version"] + ".zip")
        size, sha = archive(f.parent / "payload", package)
        entry["download"] = {
            "url": base + package.relative_to(dest).as_posix(),
            "bytes": size,
            "sha256": sha,
        }
        own = {"label": name, "url": base + "#mod/" + tid + "/" + mid}
        extras = m.get("sources", [])
        check(isinstance(extras, list) and len(extras) < 12, "Too many sources")
        entry["sources"] = [own] + [
            {"label": string(s, "label", 120), "url": https(string(s, "url", 2048))} for s in extras
        ]
        entry["previews"] = []
        pictures = m.get("previews", [])
        check(isinstance(pictures, list) and len(pictures) <= 12, "Too many previews")
        for filename in pictures:
            check(
                isinstance(filename, str)
                and re.fullmatch(r"[A-Za-z0-9_-]+\.(jpg|jpeg|png)", filename, re.I),
                "Use a local JPEG/PNG preview filename",
            )
            image = f.parent / "previews" / filename
            check(
                image.is_file()
                and not image.is_symlink()
                and not image.parent.is_symlink()
                and 0 < image.stat().st_size <= 2 * 1024 * 1024,
                f"Invalid preview {image}",
            )
            header = image.read_bytes()[:8]
            check(
                header == b"\x89PNG\r\n\x1a\n" or header.startswith(b"\xff\xd8\xff"),
                f"Unknown preview format {filename}",
            )
            stem = assets / tid / mid
            stem.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(image, stem / filename)
            entry["previews"].append(base + (stem / quote(filename)).relative_to(dest).as_posix())
        check(len(games[tid]["mods"]) < 512, "Too many releases for one game")
        games[tid]["mods"].append(entry)
    catalog = {
        "format": "moader.catalog.v1",
        "name": name,
        "description": string(repo, "description", 600),
        "games": list(games.values()),
    }
    text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    check(len(text.encode()) <= 1048576, "Catalog exceeds 1 MiB")
    (dest / "catalog.json").write_text(text, encoding="utf-8")
    (dest / ".nojekyll").touch()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--base-url", required=True, help="Public HTTPS site root, including repository subpath"
    )
    args = p.parse_args()
    base = https(args.base_url).rstrip("/") + "/"
    check(
        not urlsplit(base).query and not urlsplit(base).fragment,
        "Use the site root as the base URL",
    )
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        stage = Path(tmp) / "site"
        build(base, stage)
        output = ROOT / "_site"
        backup = Path(tmp) / "previous"
        if output.exists():
            output.rename(backup)
        try:
            stage.rename(output)
        except OSError:
            if backup.exists():
                backup.rename(output)
            raise
    print(f"Built {base}catalog.json")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as e:
        sys.exit(str(e))
