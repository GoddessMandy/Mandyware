# Desktop Companion

A small habit-building desktop companion: mood check-ins, a streak tracker,
reward minigames, adjustable "encouragement intensity," theme swapping, and
a temporary wallpaper swap while it's running.

## Getting the .exe WITHOUT installing anything on your own computer

This uses GitHub's free cloud build machines to compile the Windows exe for
you, so nothing gets installed on your PC. You only need a free GitHub
account.

1. Go to https://github.com and sign up for a free account (if you don't
   already have one).
2. Click the **+** in the top right → **New repository**. Name it anything
   (e.g. `desktop-companion`). Keep it Public or Private, either is fine.
   Click **Create repository**.
3. On the new repo's page, click **uploading an existing file** (or
   **Add file > Upload files**).
4. Drag in these files, keeping the folder structure:
   - `desktop_companion.py`
   - `.github/workflows/build.yml`
   (GitHub will let you create the `.github/workflows/` folder automatically
   when you drop the file in during upload — just type the full path
   `.github/workflows/build.yml` as the filename if it doesn't create the
   folder for you.)
5. Click **Commit changes**.
6. Click the **Actions** tab at the top of your repo. You'll see a workflow
   run start automatically (called "Build Windows Exe"). Wait for the green
   checkmark (takes 1-2 minutes).
7. Click on that completed run, scroll down to **Artifacts**, and download
   **DesktopCompanion-windows-exe**. That download is a zip containing your
   `DesktopCompanion.exe` — no Python or PyInstaller ever touched your own
   computer.

## Sharing it (download → extract → run)

1. Extract `DesktopCompanion.exe` from the artifact zip you downloaded from
   GitHub.
2. Zip it up again on its own (or just re-share the GitHub artifact zip
   directly).
3. Upload to GoFile (or wherever) and share the link.
4. Whoever downloads it: extracts the zip, double-clicks
   `DesktopCompanion.exe`. Done — no installs needed on their end either.

Note: since the exe isn't digitally signed, Windows SmartScreen may show a
one-time "Windows protected your PC" warning. Clicking **More info > Run
anyway** gets past it. This is normal for small unsigned tools.

## Data storage

Everything is stored locally in `%APPDATA%\DesktopCompanion\`:
- `settings.json` — your preferences
- `history.json` — daily mood/streak log

Nothing is sent anywhere. You can delete either file (or use "Reset
streak/history data" in Settings) at any time.

## Removing it later

Since there's no installer, removal is just:
1. Delete `DesktopCompanion.exe` and the folder it's in.
2. (Optional) Delete `%APPDATA%\DesktopCompanion\` to clear saved data.

## Setting a wallpaper to swap to

The app doesn't have a file picker built in yet. To set one:

1. Run the app once so it creates its settings file at:
   `%APPDATA%\DesktopCompanion\settings.json`
2. Close the app.
3. Open `settings.json` in Notepad and set:
   ```json
   "wallpaper_choice": "C:\\Users\\you\\Pictures\\my-focus-wallpaper.jpg"
   ```
4. Save and relaunch the app.

## What it does

- **Check-in**: asks your mood, then whether anything unproductive happened.
  - Good day → congratulates you, streak +1, offers a reward minigame.
  - Off-track day → resets streak, shows a 20-second calming screen with
    rotating positive messages (press **Esc** any time to skip it).
- **Minigames**: Memory Match, Reaction Time, Trivia, Breathing Break —
  unlocked after a "good day" check-in.
- **Intensity** (Settings): Passive / Moderate / Active — controls how often
  the companion proactively pings you and how direct its tone is.
- **Theme**: 4 color palettes (calm, forest, sunset, midnight) for the
  companion's own windows.
- **Wallpaper swap**: switches your desktop wallpaper while the app runs,
  automatically restores your original wallpaper when you quit.

## Notes / limitations

- Windows-only (the wallpaper API calls are Windows-specific).
- Cursor swapping isn't included — a real system-wide cursor swap needs a
  set of `.cur`/`.ani` files and registry changes that are easy to leave in
  a broken state if the app crashes.
- The 20-second reset screen always has an Esc-to-skip so nobody is ever
  actually locked out of their machine.
