import argparse
import json
import os
import sys
from pathlib import Path

import requests


def get_latest_release(repo: str, token: str | None, tag: str | None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    if tag and tag != "latest":
        url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    response = requests.get(url, headers=headers, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch release for {repo}: {response.status_code} {response.text[:500]}"
        )
    return response.json()


def download_asset(asset_url: str, output_path: Path, token: str | None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(asset_url, headers=headers, timeout=120, stream=True)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download asset {asset_url}: {response.status_code} {response.text[:500]}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handler:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                handler.write(chunk)


def main():
    parser = argparse.ArgumentParser(description="Download bundled EXE assets from GitHub releases")
    parser.add_argument("--config", default="apps.json")
    parser.add_argument("--output-dir", default="dist_assets")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        apps = json.load(fh)

    for app in apps:
        name = app.get("name", "UNKNOWN")
        filename = app.get("filename")
        repo = app.get("repo")
        asset_name = app.get("asset_name")
        asset_url = app.get("asset_url")
        tag = app.get("tag", "latest")

        if not filename:
            raise ValueError(f"Missing filename for app entry: {name}")
        if not repo and not asset_url:
            raise ValueError(f"Missing repo or asset_url for app entry: {name}")

        target_path = output_dir / filename
        if target_path.exists():
            print(f"[skip] {name}: already present -> {target_path}")
            continue

        if asset_url:
            print(f"[download] {name}: direct asset URL")
            download_asset(asset_url, target_path, args.token)
            continue

        release = get_latest_release(repo, args.token, tag)
        assets = release.get("assets", [])
        chosen = None

        for candidate in assets:
            asset_name_candidate = candidate.get("name")
            if asset_name and asset_name_candidate == asset_name:
                chosen = candidate
                break
            if not asset_name and asset_name_candidate.lower().endswith(".exe"):
                chosen = candidate
                break

        if not chosen:
            raise RuntimeError(f"No suitable EXE asset found for {repo}. Check asset_name in apps.json")

        print(f"[download] {name}: {chosen.get('name')} from {repo}")
        download_asset(chosen["browser_download_url"], target_path, args.token)

    print(f"Download complete. Files are stored in: {output_dir.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
