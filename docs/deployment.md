# Deploying weather-station

This covers the Raspberry Pi (Zero W or Pi 4) running `weather-station` with
a Pimoroni Inky Impression 7.3" panel attached.

## Hardware

- Seat the Inky Impression on the Pi's 40-pin GPIO header (no soldering
  needed on a Pi with headers already attached; a Pi Zero needs headers
  installed first). It draws power and talks SPI over the header --
  nothing else to wire.
- The board's four rear buttons are fixed to these BCM GPIO pins:

  | Button | BCM GPIO | Mapped to |
  |---|---|---|
  | A | 5 | daily forecast, primary location (default) |
  | B | 6 | daily forecast, secondary location |
  | C | 16 | unused (reserved) |
  | D | 24 | hourly forecast, last location checked via A/B |

  `weather_station/buttons.py` hardcodes the pin mapping (`BUTTON_PINS`); it's
  a physical fact about the board, not something `config.json` needs to
  configure. `config.json`'s `display.buttons` section maps letters to page
  names, which is configurable -- `C` is simply omitted there for now.
- Enable SPI on the Pi (`sudo raspi-config` -> Interface Options -> SPI)
  before the `inky` library will find the panel.
- **Required**: the Inky Impression's driver (for this exact 7.3" Spectra 6
  panel) does not use the kernel's automatic SPI chip-select at all -- it
  explicitly grabs CS0 (GPIO8) as a plain GPIO line and toggles it itself, so
  the kernel's default SPI0 config, which reserves GPIO8 for its own
  hardware-managed chip-select, conflicts with it outright. Symptom:
  `weather-station` crash-loops with `SystemExit: Woah there, some pins we
  need are in use! Chip Select: (line 8, GPIO8) currently claimed by spi0
  CS0`. Fix: tell SPI0 to manage *zero* hardware chip-select lines, freeing
  GPIO8 for the driver to control directly --

  ```
  sudo raspi-config   # confirm SPI is on (Interface Options -> SPI)
  echo 'dtoverlay=spi0-0cs' | sudo tee -a /boot/firmware/config.txt
  sudo reboot
  ```

  (On older Raspberry Pi OS releases this file is `/boot/config.txt` --
  `/boot/firmware/config.txt` is a symlink to it on current bookworm/trixie
  images.) This has to be a firmware/boot config change, not something
  `install.sh` or the Python code can paper over -- the conflict is between
  two kernel-level GPIO consumers before Python ever runs.

## Software install

Fastest path -- run `install.sh` from the repo root (as root, or via
`sudo`):

```
sudo ./install.sh
```

It creates the `weather-station` system user (adding it to
`gpio`/`spi`/`i2c` if those groups exist on this box), copies the code to
`/opt/weather-station`, writes `/etc/weather-station/config.json` (unless
one already exists), installs the `inky`/`gpiozero`/Pillow dependencies via
apt/pip, installs the systemd unit, and enables the service. Run it with
`--dry-run` first to see exactly what it will do without changing anything.

Useful flags (see `--help` for the full list):
- `--skip-deps` -- install the service but don't try to apt/pip install its
  dependencies (if you've already installed them, or this box has no
  internet access).
- `--install-root`, `--config-dir` -- override the default install/config
  locations.

It's safe to re-run -- code and the unit file are refreshed every time, but
an existing `config.json` is left alone unless you pass `--force-config`.

You still need to edit `/etc/weather-station/config.json`'s
`latitude`/`longitude` afterward for your location -- see
`config/README.md`.

### Manual install

If you'd rather do it by hand (or need to understand what the installer
does):

1. Install OS packages the process needs. `gpiozero`, Pillow, and numpy have
   proper apt packages; `inky` doesn't, and Debian/Raspberry Pi OS (bookworm
   and newer) refuse a bare `pip3 install` outside a venv (PEP 668's
   "externally managed environment"), so it goes into a
   `--system-site-packages` venv instead -- that still sees the
   apt-installed Pillow/gpiozero/numpy, it just gives pip somewhere it's
   actually allowed to write:

   ```
   sudo apt install python3-pip python3-venv python3-pil python3-numpy python3-gpiozero python3-lgpio fonts-dejavu-core
   sudo python3 -m venv --system-site-packages /opt/weather-station/venv
   sudo /opt/weather-station/venv/bin/pip install -r requirements.txt
   ```

   **`python3-numpy` is not optional either.** Without it, `pip install
   inky` pulls its own numpy wheel from PyPI/piwheels instead of seeing the
   apt one, and that wheel dynamically links `libopenblas.so.0` without
   bundling it -- apt's `python3-numpy` pulls in `libopenblas` as a real
   package dependency, a pip-only numpy install doesn't. Symptom:
   `weather-station` crash-loops with `ImportError: libopenblas.so.0:
   cannot open shared object file: No such file or directory` on numpy
   import. If you hit this after already installing, `sudo apt install
   python3-numpy` and then re-running `pip install --force-reinstall
   --no-deps inky` (or just deleting and recreating the venv) picks up the
   apt-provided numpy instead.

   (`fonts-dejavu-core` provides the TrueType fonts `renderer.py` looks for;
   if it's missing, rendering still works via Pillow's built-in bitmap
   font, just less legibly at small sizes.)

   `weather-station.service`'s `ExecStart` points at this venv's `python3`
   (not `/usr/bin/python3`) for exactly this reason.

   **`python3-lgpio` is not optional.** Without it, `gpiozero` silently
   falls back to its deprecated `/sys/class/gpio` ("native") pin factory,
   which fails outright on current Raspberry Pi OS kernels --
   `Button(pin)` raises `OSError: [Errno 22] Invalid argument` trying to
   export the pin. Installing `python3-lgpio` makes gpiozero's
   auto-detection pick it up instead. The unit file also sets
   `Environment=GPIOZERO_PIN_FACTORY=lgpio` explicitly so this never
   silently regresses to the broken fallback again.

   **A writable working directory is also required**, for a separate
   reason: `lgpio`'s Python bindings create a notification pipe
   (`.lgd-nfyN`) in the process's *current working directory* on import.
   systemd defaults `WorkingDirectory` to `/` when unset, which the
   `weather-station` user can't write to, so the pipe creation fails with
   `FileNotFoundError: '.lgd-nfy...'` before the display ever draws
   anything. `weather-station.service` sets both `StateDirectory=
   weather-station` (so `/var/lib/weather-station` exists, owned by the
   `weather-station` user) and `WorkingDirectory=/var/lib/weather-station`
   to fix this -- this also happens to be where `cache_path`'s default
   relative path (`weather_cache.json`) resolves to.

2. Create a dedicated system user:

   ```
   sudo useradd --system --no-create-home --shell /usr/sbin/nologin weather-station
   sudo usermod -aG gpio,spi,i2c weather-station
   ```

3. Copy the repo to `/opt/weather-station/`:

   ```
   sudo mkdir -p /opt/weather-station
   sudo cp -r weather_station /opt/weather-station/
   sudo chown -R weather-station:weather-station /opt/weather-station
   ```

4. Create the config:

   ```
   sudo mkdir -p /etc/weather-station
   sudo cp config/config.example.json /etc/weather-station/config.json
   sudo $EDITOR /etc/weather-station/config.json   # set latitude/longitude
   sudo chown -R weather-station:weather-station /etc/weather-station
   ```

5. Install and enable the service:

   ```
   sudo cp systemd/weather-station.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now weather-station
   ```

   `StateDirectory=weather-station` in the unit creates
   `/var/lib/weather-station` (owned by the `weather-station` user)
   automatically -- no manual `mkdir` needed.

## Verify

```
sudo systemctl status weather-station
sudo journalctl -u weather-station -f
```

The display should physically refresh within
`display.refresh_min_interval_seconds` of startup (a forced initial refresh
happens immediately, then the 20-35 second panel refresh itself). Pressing
button A or B should trigger a refresh as soon as any refresh already in
progress finishes -- button presses aren't subject to
`display.refresh_min_interval_seconds` at all.

## Local development without any Pi/Inky hardware

`weather_station/inky_driver.py` never imports the real `inky` package
unless asked to -- pass `--mock-output` and it writes a PNG instead:

```
python3 weather_station/main.py --config config.json --mock-output preview.png
```

For iterating on a single page without running the full async loop, use
`scripts/render_preview.py` instead -- it renders once and exits, and can
use a canned fixture with no config file or network call at all:

```
python3 scripts/render_preview.py --page daily --mock-weather --output daily.png
python3 scripts/render_preview.py --page hourly --mock-weather --output hourly.png
```

To confirm the real Open-Meteo combined daily+hourly query still works
without running the full app:

```
python3 scripts/live_api_smoke_test.py --latitude 42.8285 --longitude -71.7105
```

## Checking text/color contrast on the real panel

E-ink contrast doesn't reliably match what a color looks like in a PNG on a
normal screen. `scripts/render_color_swatch.py` renders every ink color as a
background against several text color/weight/size combinations, so
contrast questions can be settled by looking at the actual panel:

```
python3 scripts/render_color_swatch.py --output swatch.png   # preview, no hardware
sudo /opt/weather-station/venv/bin/python3 scripts/render_color_swatch.py --real   # push to the real panel
```

Note `--real` needs the venv's `python3` (same reason as everything else
that imports the real `inky` package -- see "Software install" above);
`--output` (the default) works with plain system `python3` since it never
imports `inky` at all.

The hourly page's 10-column layout (78px/column) is a laptop-screen
estimate and should be treated as provisional until checked on the real
panel -- likely to need a resizing pass the same way the daily page's
fonts/icon sizes did during development.

## Tuning refresh behavior

`display.refresh_min_interval_seconds` (default 90) in `config.json`
controls `refresh_policy.RefreshPolicy`, and only governs *background*
refreshes triggered by a new weather fetch. Confirmed on-device refresh time
for this panel is ~21s, so this is **clamped up to at least 45 seconds in
code** (`refresh_policy.HARD_MIN_REFRESH_SECONDS`), no matter what's in
config -- this leaves a genuine ~24s+ idle gap between unattended background
refresh cycles rather than allowing them back-to-back. You can raise it
above 45 for a less chatty display; you cannot lower it below that.

Button-triggered refreshes are deliberately exempt from this floor: a
button press means someone is standing at the panel waiting for a response,
so it refreshes as soon as nothing else is already mid-refresh (which,
given main.py's single-coroutine loop, just means as soon as any refresh
already in flight finishes). Repeated presses in quick succession don't
each trigger their own refresh -- they coalesce, same as before, but the
first press's page shows up as soon as the panel is free rather than being
silently overwritten by a later press before it's ever drawn.

## Read-only root filesystem (SD card longevity)

This device runs unattended with no interactive maintenance, so an
unexpected power loss (unplugging it, a brownout) risks corrupting the SD
card's filesystem if root is writable. Making root read-only is standard
hardening for this kind of always-on embedded device.

**No application or systemd unit code changes are needed for this.** The
only two things the running service ever writes to disk are
`weather_cache.json` and lgpio's transient `.lgd-nfyN` notification pipe,
both under `/var/lib/weather-station` (see "Software install" above). Both
are already safe against a read-only filesystem:
- `weather_client.save_cache()`/`load_cache()` wrap every write/read in
  `try/except OSError` (plus `FileNotFoundError`/`json.JSONDecodeError`/
  `KeyError` on load) and never raise -- a failed or missing cache
  write/read just means starting with no cached weather and fetching on
  the next poll, never a crash.
- Logging goes to stdout only (no `FileHandler`), so journald captures it
  without the app writing any log file itself.

This means the cache resets on every reboot once root is read-only (no
separate persistent partition is provisioned for it) -- a deliberate
tradeoff of setup simplicity over keeping the "instant last-known weather
on restart" nicety across reboots.

**Before starting**, back up the SD card image (e.g. `dd` from another
machine, or `rpi-clone`) -- write-protecting boot and root isn't easily
reversible if a step goes wrong and the Pi fails to boot, and the enclosure
on this particular unit makes the board awkward to get to for a manual SD
card pull.

**Checklist** (run directly on the Pi -- `raspi-config` is an interactive
TUI, not something to script blind; its `nonint` flags exist for
automation but should be confirmed against `raspi-config --help` on the
actual device rather than assumed, since they've shifted across Raspberry
Pi OS versions):

1. `sudo raspi-config` -> **Performance Options -> Overlay File System** ->
   enable. It will also ask about write-protecting the boot partition --
   say yes for full protection. Under the hood this mounts real root
   read-only as an overlayfs lower layer, with a tmpfs upper layer that's
   discarded every reboot.
2. Companion hardening, before rebooting so one reboot activates
   everything:
   - Disable swap, if `dphys-swapfile` is installed (`systemctl status
     dphys-swapfile` to check first -- Lite images may not have it):
     ```
     sudo dphys-swapfile swapoff
     sudo dphys-swapfile uninstall
     sudo systemctl disable dphys-swapfile
     ```
   - journald volatile storage -- in `/etc/systemd/journald.conf`, set
     `Storage=volatile`, then `sudo systemctl restart systemd-journald`.
   - Disable apt's periodic timers (pointless writes/network churn on a
     system that discards changes every reboot anyway):
     ```
     sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer
     ```
   - `/tmp`/`/var/log` on tmpfs and `noatime`: skip -- already subsumed by
     the overlay itself, since every write anywhere on root lands in the
     discardable tmpfs upper layer once it's active.
3. `sudo reboot`.
4. Verify: `mount | grep overlay` should show `/` mounted via overlay;
   `sudo systemctl status weather-station` and `sudo journalctl -u
   weather-station -b -n 50` should show a clean start. The startup log
   line (`weather-station starting: ... cached_days=%s cached_hours=%s`)
   will show a real cached count on the *first* reboot after cutover (the
   last real on-disk cache is still there), then `cached_days=0
   cached_hours=0` on every reboot after that by design -- either way, no
   crash, just a normal fetch and display shortly after.

**Workflow change going forward:** once overlay is active, any future
update to this project on the device (`git pull` + reinstall, editing
`/etc/weather-station/config.json`, etc.) won't persist past a reboot
unless you first disable the overlay via the same `raspi-config` menu,
make your changes, reboot to apply them normally, then re-enable overlay
and reboot again.
