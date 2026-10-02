# 5-in-1 Automation Launcher

This repo creates a single Windows launcher that bundles five separate custom EXE tools into one build.

The workflow:
- downloads the latest public release assets from the GitHub repositories
- stores them under a local `dist_assets` folder
- packages them into a launcher app using PyInstaller
- produces one `5_in_1_launcher.exe`
- uploads the final EXE to a GitHub Release automatically

## Required setup

1. Create a GitHub repository for this launcher.
2. Make the app release repos public.
3. Update the app metadata in `apps.json` so each app points to the right repository and asset name.

## Files to update

- `apps.json` : list of 5 apps to include
- `launcher_app.py` : the GUI launcher that starts each bundled EXE
- `.github/workflows/build.yml` : build and release pipeline for GitHub Actions

## Example structure in `apps.json`

```json
[
  {
    "name": "RAW DATA SPLITTER",
    "filename": "raw-data-splitter.exe",
    "repo": "rishu-pandeylenskart/raw-data-splitter",
    "asset_name": "raw-data-splitter.exe",
    "tag": "latest"
  }
]
```

## GitHub Actions

Push to `main` or run the workflow manually:

- `Actions` -> `Build 5-in-1 Launcher` -> `Run workflow`

The workflow uploads the EXE as a build artifact and also creates a GitHub Release with the final EXE attached.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_release_assets.py --config apps.json
pyinstaller --noconfirm --onefile --windowed --name "5_in_1_launcher" --add-data "dist_assets;dist_assets" launcher_app.py
```

The generated EXE will launch the included automation tools from a single launcher.
