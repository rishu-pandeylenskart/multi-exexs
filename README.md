# Automation Hub (7-in-1 Automation Launcher)

One Windows launcher EXE that bundles the separate automation tools and starts
any of them from a modern dashboard. The child EXEs are downloaded from their
GitHub Releases at build time and are launched exactly as before - they stay
fully independent applications.

## Features

- Dashboard with application cards rendered from `apps.json` (add a tool = add a JSON entry)
- Status on every card: Ready, Not installed, Launching, Running, Error (icon + text, not colour alone)
- Search (Ctrl+K) across name, description, category, repository and filename; Enter launches a single match
- Category filter, favourites (pinned first), recently used list, quick actions
- Light / dark theme, collapsible sidebar, remembered window size
- Friendly error dialogs with an expandable "technical details" section
- Everything personal is stored locally in `%APPDATA%\AutomationHub\preferences.json`; if it cannot be read or written the launcher still works

"Running" is shown only for tools this launcher started in the current session.
The launcher does not scan system processes.

## Configuration (`apps.json`)

Existing keys are unchanged and still drive the download script and the build:

```json
{
  "name": "FEDEX AUTOMATION",
  "filename": "FBT-Manifest-Generator.exe",
  "repo": "rishu-pandeylenskart/FEDEX_AUTOMATION",
  "asset_name": "FBT-Manifest-Generator.exe",
  "tag": "latest",
  "required": true,
  "category": "Shipping Automation",
  "description": "Splits a FedEx booking export into the US and Non-US FBT batch upload templates.",
  "icon": "plane"
}
```

`category`, `description` and `icon` are optional (UI only). Missing values fall back to
"General", the file name and a generic icon. Icons available: `table truck bolt package plane globe app`.

### Adding a new automation

1. Publish the tool's EXE as a GitHub Release asset.
2. Add an entry to `apps.json`, then make sure `PRIVATE_GH_TOKEN` can read that repository.
3. Push to `main` (or run the workflow). No UI code changes are needed; the cards, count and filters update themselves.

## Build

GitHub Actions (`.github/workflows/build.yml`, runs on `windows-latest`):

1. Install dependencies
2. Download every child EXE with `scripts/download_release_assets.py` using the `PRIVATE_GH_TOKEN` secret
3. `scripts/write_build_info.py` stamps build number / commit / date (shown on the About page)
4. PyInstaller builds the single `7_in_1_launcher.exe` (icon, `apps.json`, `dist_assets`, `assets`, `build_info.json` bundled)
5. Artifact upload and GitHub Release (tags `v*` or manual run)

The EXE file name is unchanged so existing links and release assets keep working.

Local build:

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
$env:PRIVATE_GH_TOKEN = gh auth token
python scripts/download_release_assets.py --config apps.json --token "$env:PRIVATE_GH_TOKEN"
python scripts/write_build_info.py
pyinstaller --noconfirm --onefile --windowed --name "7_in_1_launcher" --icon "assets\app.ico" --add-data "apps.json;." --add-data "dist_assets;dist_assets" --add-data "assets;assets" --add-data "build_info.json;." launcher_app.py
```

### Token requirements

`PRIVATE_GH_TOKEN` (repository secret) needs read access to the Releases of every repository in `apps.json`,
including the private ones. It is only used by the download step and is never written into the EXE.

## Code layout

```
launcher_app.py        entry point (keeps load_apps / launch_app for compatibility)
hub/config.py          apps.json loading and search
hub/process_manager.py launching (unchanged Popen call) and status tracking
hub/preferences.py     local favourites / recent / theme
hub/app.py cards.py widgets.py theme.py icons.py   presentation
tests/                 unit tests + UI smoke test
tools/                 icon preview / icon generation (Pillow, dev only)
```

The product name shown in the UI is defined in `hub/__init__.py`.

## Testing

```
python -m unittest discover -s tests
```

`test_core.py` covers config loading, search, preferences, launch mechanics and status logic.
`test_ui_smoke.py` runs every page and handler against a fake `tkinter`; it catches code errors but
cannot judge appearance. Before a release, open the built EXE on Windows and check: all cards render,
resize/collapse the window, search, favourite, launch a tool, switch theme, and view About.

## Troubleshooting

- **A card says "Not installed"** - the EXE was not bundled. Check the download step of the build log and `asset_name` in `apps.json`.
- **"closed unexpectedly"** - the tool started and exited at once; run its EXE directly to see its own message.
- **Launcher shows a configuration banner** - `apps.json` is invalid JSON; the launcher falls back to the bundled EXEs.
- **Preferences reset** - delete `%APPDATA%\AutomationHub\preferences.json`.
