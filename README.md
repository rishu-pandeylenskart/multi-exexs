# 7-in-1 Automation Launcher

This repo creates one Windows launcher that bundles seven separate custom EXE tools into a single build.

The workflow:
- downloads all seven required latest release assets from the GitHub repositories using a GitHub token
- stores them under a local `dist_assets` folder
- packages them into a launcher app using PyInstaller
- produces one `7_in_1_launcher.exe`
- uploads the final EXE to a GitHub Release automatically

## Required setup

1. Create a GitHub repository for this launcher.
2. Add a repository secret named `PRIVATE_GH_TOKEN` with access to all seven app repos, including `rishu-pandeylenskart/saudi-bulk-booking` and `rishu-pandeylenskart/thailand_bulk_data_splitter`.
3. Run each app's build workflow at least once so its EXE is published in a GitHub Release.
4. The launcher build fails if any required app release or asset is unavailable.
5. Update the app metadata in `apps.json` so each app points to the right repository and asset name.

## Files to update

- `apps.json` : list of 7 apps to include
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

- `Actions` -> `Build 7-in-1 Launcher` -> `Run workflow`

The workflow uploads the EXE as a build artifact and also creates a GitHub Release with the final EXE attached.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:PRIVATE_GH_TOKEN = gh auth token
python scripts/download_release_assets.py --config apps.json --token "$env:PRIVATE_GH_TOKEN"
pyinstaller --noconfirm --onefile --windowed --name "7_in_1_launcher" --add-data "apps.json;." --add-data "dist_assets;dist_assets" launcher_app.py
```

The generated EXE will launch the included automation tools from a single launcher.
