# GOTCHAS (macOS)

- **stdin hangs.** `sqlite3` with no SQL argument waits on stdin forever. Always run the backend with `stdin=subprocess.DEVNULL` (the wrapper does this whenever no input is given) and a timeout.
- **Help flags differ.** `--help`, `-help` and `-h` are not interchangeable. sqlite3 and ffmpeg answer to `-help`; many GNU-style tools only `--help`. Same for version: `--version`, `-version`, `-V`. Try each in order and accept the first with output.
- **Anaconda vs Homebrew binaries.** The same name can resolve to different programs and versions depending on PATH order (`/opt/anaconda3/bin` vs `/opt/homebrew/bin` vs `/usr/bin`). Always resolve with `shutil.which`, never hardcode a path, and record the resolved path.
- **ffmpeg writes to stderr.** Banners, version and help go to stderr, not stdout. Capture both and combine them when probing. Pass `-hide_banner` in wrapper commands.
- **Non-zero exit on help.** Some tools exit 1 or 2 on `--help` or `--version` while printing perfectly good text. Accept non-zero when there is output during probing. In the wrapper, do the opposite: a non-zero exit from a real command is a failure.
- **macOS BSD vs GNU flags.** Tools like `sed`, `date` and `stat` differ from their GNU versions. Probe the installed binary, not what you remember.
