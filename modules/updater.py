import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import gi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fabric.utils.helpers import get_relative_path

import config.data as data

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

# File locations
VERSION_FILE = get_relative_path("../utils/version.json")
REMOTE_VERSION_FILE = "/tmp/remote_version.json"
REMOTE_URL = "https://raw.githubusercontent.com/Axenide/Ax-Shell/refs/heads/main/utils/version.json"
REPO_DIR = get_relative_path("../")

SNOOZE_FILE_NAME = "updater_snooze.txt"
SNOOZE_DURATION_SECONDS = 8 * 60 * 60  # 8 hours

# --- Helper Functions ---
def get_snooze_file_path():
    cache_dir = data.CACHE_DIR or os.path.expanduser(f"~/.cache/{data.APP_NAME}")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating cache directory {cache_dir}: {e}")
    return os.path.join(cache_dir, SNOOZE_FILE_NAME)


def fetch_remote_version():
    try:
        subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", REMOTE_URL, "-o", REMOTE_VERSION_FILE],
            check=False,
            timeout=15
        )
    except subprocess.TimeoutExpired:
        print("Error: curl command timed out while fetching remote version.")
    except FileNotFoundError:
        print("Error: curl command not found. Please install curl.")
    except Exception as e:
        print(f"Error fetching remote version: {e}")


def get_local_version():
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r") as f:
                content = json.load(f)
                return content.get("version", "0.0.0"), content.get("changelog", [])
        except Exception as e:
            print(f"Error reading local version file {VERSION_FILE}: {e}")
    return "0.0.0", []


def get_remote_version():
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            with open(REMOTE_VERSION_FILE, "r") as f:
                content = json.load(f)
                return (
                    content.get("version", "0.0.0"),
                    content.get("changelog", []),
                    content.get("download_url", "#"),
                )
        except Exception as e:
            print(f"Error reading remote version file {REMOTE_VERSION_FILE}: {e}")
    return "0.0.0", [], "#"


def update_local_version_file():
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            shutil.move(REMOTE_VERSION_FILE, VERSION_FILE)
        except Exception as e:
            print(f"Error updating local version file: {e}")
            raise


def update_local_repo(progress_callback):
    try:
        subprocess.run(["git", "stash"], cwd=REPO_DIR, check=False, capture_output=True, text=True)
        proc = subprocess.Popen(
            ["git", "pull"],
            cwd=REPO_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.stdout:
            for line in proc.stdout:
                progress_callback(line)
        proc.wait()
        if proc.returncode != 0:
            err = proc.stderr.read() if proc.stderr else ""
            print(f"Git pull failed: {err}")
        subprocess.run(["git", "stash", "apply"], cwd=REPO_DIR, check=False, capture_output=True, text=True)
    except Exception as e:
        print(f"Error updating local repository: {e}")
        raise


def is_connected():
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False

# --- Process Management ---
def kill_old_instance():
    main_py = os.path.expanduser(
        f"{data.HOME_DIR}/.config/{data.APP_NAME_CAP}/main.py"
    )
    try:
        subprocess.run(
            ["pkill", "-f", main_py],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2
        )
        print("Old instance killed.")
    except subprocess.TimeoutExpired:
        print("Warning: pkill timed out.")
    except Exception as e:
        print(f"Error killing old instance: {e}")


def run_disowned_command(logfile="/tmp/ax-shell-restart.log"):
    main_py = os.path.expanduser(
        f"{data.HOME_DIR}/.config/{data.APP_NAME_CAP}/main.py"
    )
    start_cmd = ["uwsm", "app", "--", "python", main_py]
    try:
        with open(logfile, "a") as lf:
            subprocess.Popen(
                start_cmd,
                stdout=lf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=os.environ.copy()
            )
        print(f"{data.APP_NAME_CAP} restart initiated (logs → {logfile}).")
    except FileNotFoundError as e:
        print(f"Error: comando no encontrado ({e})")
    except Exception as e:
        print(f"Error arrancando {data.APP_NAME_CAP}: {e}")

# --- GTK Update Window ---
class UpdateWindow(Gtk.Window):
    def __init__(self, latest_version, changelog, is_standalone_mode=False):
        super().__init__(name="update-window", title=f"{data.APP_NAME_CAP} Updater")
        self.set_default_size(500, 480)
        self.set_border_width(16)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.is_standalone_mode = is_standalone_mode
        self.quit_gtk_main_on_destroy = False

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(main_vbox)

        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>📦 Update Available ✨</span>")
        title.get_style_context().add_class("title-1")
        main_vbox.pack_start(title, False, False, 10)

        info = Gtk.Label(label=f"A new version ({latest_version}) of {data.APP_NAME_CAP} is available.")
        info.set_xalign(0)
        info.set_line_wrap(True)
        main_vbox.pack_start(info, False, False, 0)

        log_header = Gtk.Label()
        log_header.set_markup("<b>Changelog:</b>")
        log_header.set_xalign(0)
        main_vbox.pack_start(log_header, False, False, 5)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        textview.get_style_context().add_class("changelog-view")
        buf = textview.get_buffer()
        if changelog:
            for c in changelog:
                buf.insert_at_cursor(f"• {c}\n")
        else:
            buf.insert_at_cursor("No specific changes listed.\n")
        scrolled.add(textview)
        main_vbox.pack_start(scrolled, True, True, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_no_show_all(True)
        main_vbox.pack_start(self.progress_bar, False, False, 5)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END)
        main_vbox.pack_start(action_box, False, False, 10)

        self.update_button = Gtk.Button(label="Update and Restart")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self.on_update_clicked)
        action_box.pack_end(self.update_button, False, False, 0)

        self.close_button = Gtk.Button(label="Later")
        self.close_button.connect("clicked", self.on_later_clicked)
        action_box.pack_end(self.close_button, False, False, 0)

        self.connect("destroy", self.on_window_destroyed)

    def on_later_clicked(self, _):
        path = get_snooze_file_path()
        try:
            with open(path, "w") as f:
                f.write(str(time.time()))
            print(f"Update snoozed (file: {path})")
        except Exception as e:
            print(f"Error snoozing update: {e}")
        self.destroy()

    def on_update_clicked(self, _):
        self.update_button.set_sensitive(False)
        self.close_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Initializing update...")
        self.pulse_id = GLib.timeout_add(100, self.pulse_progress_bar)
        threading.Thread(target=self.run_update_process, daemon=True).start()

    def pulse_progress_bar(self):
        self.progress_bar.pulse()
        return True

    def run_update_process(self):
        try:
            GLib.idle_add(self.progress_bar.set_text, "Updating version info...")
            update_local_version_file()
            GLib.idle_add(self.progress_bar.set_text, "Pulling latest code...")
            update_local_repo(lambda l: GLib.idle_add(self._git_callback, l))
            GLib.idle_add(self.handle_update_success)
        except Exception as e:
            print(f"Update process failed: {e}")
            GLib.idle_add(self.handle_update_failure, str(e))

    def _git_callback(self, line):
        self.progress_bar.pulse()

    def handle_update_success(self):
        if hasattr(self, 'pulse_id'):
            GLib.source_remove(self.pulse_id)
        self.progress_bar.set_text("Update complete. Restarting...")
        self.progress_bar.set_fraction(1.0)
        GLib.timeout_add_seconds(2, self.trigger_restart_and_close)

    def handle_update_failure(self, err):
        if hasattr(self, 'pulse_id'):
            GLib.source_remove(self.pulse_id)
        self.progress_bar.set_text("Update failed.")
        self.progress_bar.set_fraction(0)
        self.update_button.set_sensitive(True)
        self.close_button.set_sensitive(True)
        dlg = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Update Failed",
        )
        dlg.format_secondary_text(err)
        dlg.run()
        dlg.destroy()

    def trigger_restart_and_close(self):
        self.destroy()
        kill_old_instance()
        run_disowned_command()
        return False

    def on_window_destroyed(self, _):
        if hasattr(self, 'pulse_id'):
            GLib.source_remove(self.pulse_id)
        if self.is_standalone_mode:
            Gtk.main_quit()

# --- Update Flow Control ---
def _initiate_update_check_flow(is_standalone_mode):
    if not is_connected():
        print("No internet, skipping updates.")
        if is_standalone_mode:
            GLib.idle_add(Gtk.main_quit)
        return

    snooze = get_snooze_file_path()
    if os.path.exists(snooze):
        try:
            with open(snooze) as f:
                ts = float(f.read().strip())
            if time.time() - ts < SNOOZE_DURATION_SECONDS:
                print("Update snoozed.")
                if is_standalone_mode:
                    GLib.idle_add(Gtk.main_quit)
                return
            else:
                os.remove(snooze)
        except Exception:
            os.remove(snooze)

    fetch_remote_version()
    local_version, _ = get_local_version()
    remote_version, changelog, _ = get_remote_version()
    if remote_version > local_version and remote_version != "0.0.0":
        GLib.idle_add(launch_update_window, remote_version, changelog, is_standalone_mode)
    else:
        print(f"{data.APP_NAME_CAP} is up to date.")
        if is_standalone_mode:
            GLib.idle_add(Gtk.main_quit)


def launch_update_window(latest, changelog, standalone):
    win = UpdateWindow(latest, changelog, standalone)
    win.is_standalone_mode = standalone
    win.show_all()


def check_for_updates():
    threading.Thread(target=_initiate_update_check_flow, args=(False,), daemon=True).start()


def run_updater():
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE
    _QUIT_GTK_IF_NO_WINDOW_STANDALONE = True
    threading.Thread(target=_initiate_update_check_flow, args=(True,), daemon=True).start()
    Gtk.main()
