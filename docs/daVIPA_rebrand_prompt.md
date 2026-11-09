# Rebrand task: daVIPA

Python desktop app, developed on macOS, built for macOS and Windows via GitHub Actions.

Work in phases. **Stop for my approval after Phase 1.** Do not edit anything until I approve.

---

## The change

|          | Old | New |
|----------|---|---|
| App name | GMD | daVIPA
| Long name | 'Get More Done' | `daVIPA'
| Tagline | Get More Done | `Vision - Planning - Action' |

**Capitalisation:** always `daVIPA` — capital V I P A, 'da' is lowercase. 
---

## Phase 1 — Discover and report. Change nothing.

First, tell me **which build tool this project uses** — PyInstaller, briefcase, py2app, cx_Freeze,
or Nuitka — and adapt everything below to it. The instructions assume PyInstaller as the most likely.

Then search the whole repo (source, config, CI, scripts, docs, tests, fixtures) for:

- `GMD`, 'gmd' — case-insensitive
- `Get More Done' in any case combination`
- IMPORTANT - the repo folder will be rename to daVIPA
- IMPORTANT - the Git hum repo will be renamed 
- the app name as passed to `platformdirs` / `appdirs` (`user_data_dir`, `user_config_dir`,
  `user_cache_dir`, `user_log_dir`) — **and any hard-coded path that duplicates it**
- `QSettings(...)` organisation/application arguments, if this is a Qt app
- the `.spec` file: `name=`, `icon=`, `bundle_identifier=`, `BUNDLE(...)`
- `pyproject.toml` / `setup.py` / `setup.cfg`: `name`, `description`, entry points, console/GUI scripts
- `.github/workflows/*`: artifact names, release asset names, upload/download steps, output paths,
  job and matrix names
- any Windows version-info resource file (`ProductName`, `FileDescription`, `InternalName`,
  `OriginalFilename`, `CompanyName`)
- `Info.plist` or plist templates: `CFBundleName`, `CFBundleDisplayName`, `CFBundleIdentifier`,
  `CFBundleExecutable`
- existing icon assets (`.icns`, `.ico`, `.png`) and every reference to them
- any auto-update feed/appcast URL or channel name
- hard-coded brand colours

Produce a table: **file · line · match · what it controls · proposed value · risk (safe /
needs-decision / dangerous)**. List anything you're unsure about separately. **Then stop.**

---

## Phase 2 — Safe renames (after approval)

- Window titles, menu bar, About dialog, tray/dock tooltips, notification titles
- All user-facing strings
- `pyproject.toml` / `setup.py` name and description
- README, docs, comments, LICENSE copyright line
- Test assertions that reference the display name

---

## Phase 3 — Dangerous. Ask before touching each.

### 3a. User data directory — the big one

If the app calls `platformdirs.user_data_dir("GMD")` (or equivalent), renaming it silently moves where the app looks for its data:

- macOS: `~/Library/Application Support/GMD` → `.../daVIPA`
- Windows: `%APPDATA%\GMD` → `%APPDATA%\daVIPA`

Every existing user loses their settings, database and history, and it will look like data loss, not
a rename. **Do not change this without a migration.** Propose one of:

1. Keep the old directory name permanently (invisible to users, zero risk), or
2. Rename it and add one-time migration on startup: if the new directory does not exist and the old
   one does, copy (do not move) the contents, write a marker file, and log it. Keep the old directory
   for at least one release.

Tell me which you recommend and why. The same applies to `QSettings` organisation/application names, log directories, cache directories, and any SQLite file path.

### 3b. macOS bundle identifier

If the app has already been distributed to anyone, [ the app has not be deistributed, except to myself]  **do not change `CFBundleIdentifier`.** It affects
code-signing identity, notarisation, LaunchServices registration, and any saved preferences domain.
A shipped app can keep a legacy identifier with a new display name — that is normal. Tell me whether
this app has shipped and let me decide.

### 3c. Executable filename on Windows

Renaming the `.exe` **resets accumulated SmartScreen reputation**, so early users may get an
"unrecognised app" warning again even if nothing else changed. Flag this; it may be worth renaming
anyway, but I want to know.

### 3d. Auto-update feeds

If there's an update channel, appcast, or release-asset naming convention, renaming assets breaks
updates for users on the old version. List every dependency before changing any of it.

### 3e. Do NOT rename

Analytics event names, feature-flag keys, log identifiers, metric names. These are internal
identifiers, not brand surface, and renaming them severs continuity with historical data.

---

## Phase 4 — Icons

See the diVIPA .zip file for all the icons and ico  images

| Platform | File | Shape |
|---|---|---|
| macOS | `davipa.icns` | Rounded squircle, inset with padding, gradient backgroudn |
| Windows | `davipa.ico` | Square, full-bleed, opaque, no rounding |

The reason: **macOS does not mask app icons** — the rounded shape and shadow must be baked into the `.icns`, and Apple's template insets the artwork to about 80% of the canvas. Windows does not mask
either, but its convention is square and full-bleed. Both files are already correct.
 See the zip file.


Wire them up:

- PyInstaller `.spec`: `icon='davipa.icns'` for the macOS build, `icon='davipa.ico'` for Windows.
  If the spec is shared, branch on `sys.platform`.
- Remove the old icon assets entirely; don't leave them orphaned in the repo.
- If the GitHub Actions workflow references icon paths, update them there too.

A full-bleed square master (`davipa_icon_F_navy_1024.png`) is also included for the README, docs, any
in-app about screen, and store/marketing use.

---

## Phase 5 — Brand palette

See the attached Brand Palette document

---

## Phase 6 — Verify

- Build locally on macOS and confirm the `.app` shows the new name and icon in Finder and the Dock.
  If the old icon persists, it's the LaunchServices cache — note it rather than chasing it.
- Push and confirm the GitHub Actions matrix builds succeed for both macOS and Windows, and that
  release artifacts are named correctly.
- Run the full test suite; fix assertions referencing the old name.
- Re-grep for `GMD`, `gmd`, `Get More Done` and show me every surviving hit with justification.
- Confirm no string reads `GMD`, `gmd`.
- If you implemented data-directory migration, test it: create the old directory with dummy contents,
  launch, confirm the data appears under the new path and the old is left intact.

---

## Rules

- **Never** run a blind global find-and-replace. Everything goes through the Phase 1 table first.
- Small, well-labelled commits. Icon changes separate from string changes separate from any
  data-path migration.
- If a change would alter persisted user state, stop and tell me first.
- If anything is ambiguous, ask. Do not guess at brand strings.

---

## Out of scope — I handle these

Apple Developer signing certificates, notarisation credentials, GitHub release descriptions, domain
registration, social handles. Tell me if you find a dependency on any of them, but don't touch them.
