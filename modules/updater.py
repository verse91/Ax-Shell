import json
import os
import shutil
import socket
import subprocess
import sys
import threading
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

# --- Global state for standalone execution control ---
_QUIT_GTK_IF_NO_WINDOW_STANDALONE = False


# --- Network and Version Functions ---
def fetch_remote_version():
    try:
        # Use timeout for curl to prevent indefinite blocking on network issues
        subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", REMOTE_URL, "-o", REMOTE_VERSION_FILE],
            check=False,
            timeout=15  # Overall timeout for the command
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
                data_content = json.load(f)
                return data_content.get("version", "0.0.0"), data_content.get("changelog", [])
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from local version file: {VERSION_FILE}")
            return "0.0.0", []
        except Exception as e:
            print(f"Error reading local version file {VERSION_FILE}: {e}")
            return "0.0.0", []
    return "0.0.0", []


def get_remote_version():
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            with open(REMOTE_VERSION_FILE, "r") as f:
                data_content = json.load(f)
                return (
                    data_content.get("version", "0.0.0"),
                    data_content.get("changelog", []),
                    data_content.get("download_url", "#"),
                )
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from remote version file: {REMOTE_VERSION_FILE}")
            return "0.0.0", [], "#"
        except Exception as e:
            print(f"Error reading remote version file {REMOTE_VERSION_FILE}: {e}")
            return "0.0.0", [], "#"
    return "0.0.0", [], "#"


def update_local_version_file():
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            shutil.move(REMOTE_VERSION_FILE, VERSION_FILE)
        except Exception as e:
            print(f"Error updating local version file: {e}")
            # Potentially re-raise or handle more gracefully if this is critical
            raise


def update_local_repo(progress_callback):
    try:
        subprocess.run(["git", "stash"], cwd=REPO_DIR, check=False, capture_output=True, text=True)

        process = subprocess.Popen(
            ["git", "pull"],
            cwd=REPO_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.stdout:
            for line in process.stdout:
                progress_callback(line)
        process.wait()
        
        # Check for errors in git pull
        if process.returncode != 0:
            stderr_output = process.stderr.read() if process.stderr else "Unknown error"
            print(f"Git pull failed with error: {stderr_output}")
            # raise Exception(f"Git pull failed: {stderr_output}") # Optionally raise

        subprocess.run(["git", "stash", "apply"], cwd=REPO_DIR, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        print("Error: git command not found. Please ensure git is installed and in PATH.")
        raise
    except Exception as e:
        print(f"Error updating local repository: {e}")
        raise


def kill_processes():
    subprocess.run(["pkill", data.APP_NAME], check=False)
    subprocess.run(["pkill", "cava"], check=False)


def run_disowned_command():
    try:
        command = f"killall -q {data.APP_NAME}; uwsm app -- python {data.HOME_DIR}/.config/{data.APP_NAME_CAP}/main.py"
        subprocess.Popen(
            command,
            shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL, # Suppress output from disowned process
            stderr=subprocess.DEVNULL
        )
        print(f"{data.APP_NAME_CAP} process restart initiated.")
    except Exception as e:
        print(f"Error restarting {data.APP_NAME_CAP} process: {e}")


def is_connected():
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False


# --- GTK Update Window ---
class UpdateWindow(Gtk.Window):
    def __init__(self, latest_version, changelog, is_standalone_mode=False):
        super().__init__(title=f"{data.APP_NAME_CAP} Updater")
        self.set_default_size(500, 480)
        # self.set_border_width(12)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.is_standalone_mode = is_standalone_mode
        self.quit_gtk_main_on_destroy = False

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(main_vbox)

        title_label = Gtk.Label()
        title_label.set_markup("<span size='xx-large' weight='bold'>Update Available</span>")
        title_label.get_style_context().add_class("title-1")
        main_vbox.pack_start(title_label, False, False, 10)

        info_label = Gtk.Label(
            label=f"A new version ({latest_version}) of {data.APP_NAME_CAP} is available."
        )
        info_label.set_xalign(0)
        info_label.set_line_wrap(True)
        main_vbox.pack_start(info_label, False, False, 0)

        changelog_header_label = Gtk.Label()
        changelog_header_label.set_markup("<b>Changelog:</b>")
        changelog_header_label.set_xalign(0)
        main_vbox.pack_start(changelog_header_label, False, False, 5)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.changelog_view = Gtk.TextView()
        self.changelog_view.set_editable(False)
        self.changelog_view.set_cursor_visible(False)
        self.changelog_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.changelog_view.get_style_context().add_class("changelog-view")
        
        changelog_buffer = self.changelog_view.get_buffer()
        if changelog:
            for change in changelog:
                changelog_buffer.insert_at_cursor(f"• {change}\n")
        else:
            changelog_buffer.insert_at_cursor("No specific changes listed for this version.\n")
        
        scrolled_window.add(self.changelog_view)
        main_vbox.pack_start(scrolled_window, True, True, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_no_show_all(True)
        self.progress_bar.set_visible(False)
        main_vbox.pack_start(self.progress_bar, False, False, 5)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END)
        main_vbox.pack_start(action_box, False, False, 10)

        self.update_button = Gtk.Button(label="Update and Restart")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self.on_update_clicked)
        action_box.pack_end(self.update_button, False, False, 0)

        self.close_button = Gtk.Button(label="Later")
        self.close_button.connect("clicked", lambda _: self.destroy())
        action_box.pack_end(self.close_button, False, False, 0)

        self.connect("destroy", self.on_window_destroyed)

    def on_update_clicked(self, _widget):
        self.update_button.set_sensitive(False)
        self.close_button.set_sensitive(False)

        self.progress_bar.set_visible(True)
        self.progress_bar.set_text("Initializing update...")
        self.progress_bar.set_show_text(True)
        self.progress_bar.pulse()
        
        self.pulse_timeout_id = GLib.timeout_add(100, self.pulse_progress_bar_tick)
        threading.Thread(target=self.run_update_process, daemon=True).start()

    def pulse_progress_bar_tick(self):
        self.progress_bar.pulse()
        return True  # Keep timeout active

    def run_update_process(self):
        try:
            GLib.idle_add(self.progress_bar.set_text, "Updating version information...")
            update_local_version_file()

            GLib.idle_add(self.progress_bar.set_text, "Downloading updates (git pull)...")
            update_local_repo(lambda line: GLib.idle_add(self.git_progress_callback, line))
            
            GLib.idle_add(self.handle_update_success)
        except Exception as e:
            print(f"Update process failed: {e}")
            GLib.idle_add(self.handle_update_failure, str(e))
            
    def git_progress_callback(self, line):
        self.progress_bar.pulse()
        # print(f"GIT: {line.strip()}") # Uncomment for verbose git output

    def handle_update_success(self):
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")
        
        self.progress_bar.set_text("Update Complete. Restarting application...")
        self.progress_bar.set_fraction(1.0)

        GLib.timeout_add_seconds(2, self.trigger_restart_and_close)
        
    def trigger_restart_and_close(self):
        self.destroy() # Close window first
        kill_processes()
        run_disowned_command()
        return False # Stop GLib timeout

    def handle_update_failure(self, error_message):
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")
        
        self.progress_bar.set_text(f"Update Failed.") # Keep it short on bar
        self.progress_bar.set_fraction(0.0)
        
        self.update_button.set_sensitive(True)
        self.close_button.set_sensitive(True)

        error_dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Update Failed",
        )
        error_dialog.format_secondary_text(error_message)
        error_dialog.run()
        error_dialog.destroy()

    def on_window_destroyed(self, _widget):
        if hasattr(self, "pulse_timeout_id"): # Clean up timer if window closed prematurely
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")
        
        if self.quit_gtk_main_on_destroy:
             Gtk.main_quit()


# --- Update Checking Logic ---
def _initiate_update_check_flow(is_standalone_mode):
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE # Used by standalone execution path

    if not is_connected():
        print("No internet connection. Skipping update check.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)
        return

    fetch_remote_version()

    current_version, _ = get_local_version()
    latest_version, changelog, _ = get_remote_version()

    # Basic version comparison (can be improved with packaging.version for robustness)
    if latest_version > current_version and latest_version != "0.0.0":
        GLib.idle_add(launch_update_window, latest_version, changelog, is_standalone_mode)
    else:
        print(f"{data.APP_NAME_CAP} is up to date or remote version is invalid.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)


def launch_update_window(latest_version, changelog, is_standalone_mode):
    win = UpdateWindow(latest_version, changelog, is_standalone_mode)
    if is_standalone_mode:
        win.quit_gtk_main_on_destroy = True # Ensure Gtk.main_quit on window close
    win.show_all()


def check_for_updates():
    """
    Public function to check for updates. Runs checks in a background thread.
    This is intended for use as a module.
    """
    thread = threading.Thread(target=_initiate_update_check_flow, args=(False,), daemon=True)
    thread.start()


# --- Main execution point for standalone script ---
if __name__ == '__main__':
    _QUIT_GTK_IF_NO_WINDOW_STANDALONE = True 
    
    # Run the update check logic in a thread.
    # This thread will use GLib.idle_add to interact with Gtk.main loop.
    update_check_thread = threading.Thread(target=_initiate_update_check_flow, args=(True,), daemon=True)
    update_check_thread.start()
    
    Gtk.main()
