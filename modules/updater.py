import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time  # Ya estaba importado
from pathlib import Path

import gi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fabric.utils.helpers import \
    get_relative_path  # Asumo que esta ruta es correcta para tu proyecto

import config.data as data  # Asumo que este módulo existe y está configurado

gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91") # Nueva importación para VTE
from gi.repository import Gdk, GLib, Gtk, Vte  # Vte añadido aquí

# File locations (sin cambios)
VERSION_FILE = get_relative_path("../utils/version.json")
REMOTE_VERSION_FILE = "/tmp/remote_version.json"
REMOTE_URL = "https://raw.githubusercontent.com/Axenide/Ax-Shell/refs/heads/main/utils/version.json"
# REPO_DIR ya no se usa para git pull directamente, pero podría ser relevante para otros aspectos.
REPO_DIR = get_relative_path("../") 
SNOOZE_FILE_NAME = "updater_snooze.txt"
SNOOZE_DURATION_SECONDS = 8 * 60 * 60  # 8 hours

# --- Global state for standalone execution control ---
_QUIT_GTK_IF_NO_WINDOW_STANDALONE = False

# --- NUEVA FUNCIÓN (sin cambios) ---
def get_snooze_file_path():
    cache_dir_base = data.CACHE_DIR
    if not cache_dir_base:
        print(f"Warning: data.CACHE_DIR is not defined. Falling back to ~/.cache/{data.APP_NAME}")
        cache_dir_base = os.path.expanduser(f"~/.cache/{data.APP_NAME}")
    try:
        os.makedirs(cache_dir_base, exist_ok=True)
    except Exception as e:
        print(f"Error creating cache directory {cache_dir_base}: {e}")
    return os.path.join(cache_dir_base, SNOOZE_FILE_NAME)

# --- Network and Version Functions (sin cambios en su mayoría) ---
def fetch_remote_version():
    try:
        subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", REMOTE_URL, "-o", REMOTE_VERSION_FILE],
            check=False, # No lanzar excepción en error, lo manejamos por la existencia del archivo
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
                    data_content.get("changelog", []), # Changelog aún se obtiene, aunque no se use igual
                    data_content.get("download_url", "#"), # download_url aún se obtiene
                )
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from remote version file: {REMOTE_VERSION_FILE}")
            return "0.0.0", [], "#"
        except Exception as e:
            print(f"Error reading remote version file {REMOTE_VERSION_FILE}: {e}")
            return "0.0.0", [], "#"
    return "0.0.0", [], "#"

def update_local_version_file():
    """Mueve el REMOTE_VERSION_FILE descargado al VERSION_FILE local."""
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            shutil.move(REMOTE_VERSION_FILE, VERSION_FILE)
            print(f"Local version file updated: {VERSION_FILE}")
        except Exception as e:
            print(f"Error updating local version file: {e}")
            # Considerar si se debe relanzar la excepción o manejarla
            # raise

# --- update_local_repo ELIMINADA ---
# La funcionalidad de git pull se reemplaza por el terminal VTE y el script.

# --- Funciones de Proceso (sin cambios) ---
def kill_processes():
    subprocess.run(["pkill", data.APP_NAME], check=False)

def run_disowned_command():
    try:
        command = f"bash -c 'killall -q {data.APP_NAME}; sleep 0.2; uwsm app -- python {data.HOME_DIR}/.config/{data.APP_NAME_CAP}/main.py'"
        subprocess.Popen(
            command,
            shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
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

# --- GTK Update Window MODIFICADA ---
class UpdateWindow(Gtk.Window):
    def __init__(self, latest_version, changelog, is_standalone_mode=False):
        super().__init__(name="ax-shell-installer-window", title=f"{data.APP_NAME_CAP} - Ax-Shell Installer")
        self.set_default_size(750, 650) # Tamaño ajustado para el terminal
        self.set_border_width(16)
        self.set_resizable(True) # Permitir redimensionar
        self.set_position(Gtk.WindowPosition.CENTER)
        # self.set_keep_above(True) # Puede ser molesto con un terminal activo
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL) # Dialog puede ser muy restrictivo
        self.is_standalone_mode = is_standalone_mode
        self.quit_gtk_main_on_destroy = False

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(main_vbox)

        title_label = Gtk.Label(name="installer-title")
        title_label.set_markup("<span size='xx-large' weight='bold'>🚀 Ax-Shell Installation Terminal 🚀</span>")
        title_label.get_style_context().add_class("title-1")
        main_vbox.pack_start(title_label, False, False, 10)

        info_label = Gtk.Label(
            label=(f"This terminal will run the Ax-Shell installation script. "
                   f"New version available: {latest_version}.\n"
                   f"Click 'Run Install Script' to proceed.")
        )
        info_label.set_xalign(0)
        info_label.set_line_wrap(True)
        main_vbox.pack_start(info_label, False, False, 5)

        # --- VTE Terminal Widget ---
        self.terminal = Vte.Terminal()
        self.terminal.set_vexpand(True)
        self.terminal.set_hexpand(True)
        self.terminal.set_font_scale(1.0) # Ajustar según preferencia
        # Colores opcionales (ejemplo: fondo oscuro, texto claro)
        # self.terminal.set_color_background(Gdk.RGBA(0.1, 0.1, 0.1, 1.0))
        # self.terminal.set_color_foreground(Gdk.RGBA(0.9, 0.9, 0.9, 1.0))
        main_vbox.pack_start(self.terminal, True, True, 5)
        # --- FIN VTE Terminal ---

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END) # Alinea los botones a la derecha
        main_vbox.pack_start(action_box, False, False, 10)

        self.run_button = Gtk.Button(name="run-button", label="Run Install Script")
        self.run_button.get_style_context().add_class("suggested-action")
        self.run_button.connect("clicked", self.on_run_script_clicked)
        action_box.pack_end(self.run_button, False, False, 0)

        self.later_button = Gtk.Button(name="later-button", label="Later")
        self.later_button.connect("clicked", self.on_later_clicked)
        action_box.pack_end(self.later_button, False, False, 0) # Pack end para orden Later | Run

        self.connect("destroy", self.on_window_destroyed)

    def on_later_clicked(self, _widget):
        snooze_file_path = get_snooze_file_path()
        try:
            with open(snooze_file_path, "w") as f:
                f.write(str(time.time()))
            print(f"Update snoozed. Snooze file created at: {snooze_file_path}")
        except Exception as e:
            print(f"Error creating snooze file {snooze_file_path}: {e}")
        self.destroy()

    def on_run_script_clicked(self, _widget):
        self.run_button.set_sensitive(False)
        self.later_button.set_sensitive(False) # Deshabilitar 'Later' una vez iniciado

        # Comando a ejecutar en el terminal
        # Es importante que el shell (-c) maneje la tubería correctamente.
        command_to_run = "curl -fsSL https://raw.githubusercontent.com/Axenide/Ax-Shell/main/install.sh | bash"
        
        argv = ["/bin/bash", "-c", command_to_run]

        try:
            self.terminal.spawn_async(
                Vte.PtyFlags.DEFAULT,  # pty_flags
                None,                  # working_directory
                argv,                  # argv
                [],                    # envv
                GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH, # spawn_flags
                None,                  # child_setup
                None,                  # child_setup_data
                -1,                    # timeout
                None,                  # cancellable
                self.on_script_finished, # callback
                None                   # user_data
            )
            self.terminal.grab_focus() # Poner el foco en el terminal
        except GLib.Error as e:
            print(f"Error spawning terminal command: {e.message}")
            self.show_message_dialog("Error", f"Failed to start script: {e.message}", Gtk.MessageType.ERROR)
            self.run_button.set_sensitive(True)
            self.later_button.set_sensitive(True)

    def on_script_finished(self, terminal, pid, status, _user_data):
        # Llamado cuando el proceso en el VTE termina.
        # Es importante hacer las actualizaciones de UI en el hilo principal de GTK.
        GLib.idle_add(self._handle_script_completion, status)

    def _handle_script_completion(self, status):
        # Esta función se ejecuta en el hilo principal de GTK.
        if status == 0: # Éxito (código de salida 0)
            print("Ax-Shell installation script executed successfully.")
            
            # 1. Eliminar archivo snooze
            snooze_file_path = get_snooze_file_path()
            if os.path.exists(snooze_file_path):
                try:
                    os.remove(snooze_file_path)
                    print(f"Snooze file removed: {snooze_file_path}")
                except Exception as e:
                    print(f"Error removing snooze file {snooze_file_path}: {e}")

            # 2. (Opcional) Actualizar el archivo de versión local.
            #    Esto asume que REMOTE_VERSION_FILE fue descargado por fetch_remote_version()
            #    y representa la versión que el script acaba de instalar/configurar.
            try:
                update_local_version_file()
            except Exception as e:
                print(f"Note: Could not update local version file post-script: {e}")

            self.show_message_dialog(
                "Script Finished",
                "The Ax-Shell installation script has completed successfully. The application will now attempt to restart.",
                Gtk.MessageType.INFO,
                lambda: self.trigger_restart_and_close() # Callback para después de cerrar el diálogo
            )
        else:
            print(f"Ax-Shell installation script failed with status: {status}")
            self.show_message_dialog(
                "Script Failed",
                f"The script exited with status code: {status}. Check the terminal output for details.",
                Gtk.MessageType.ERROR
            )
            self.run_button.set_sensitive(True) # Permitir reintentar
            self.later_button.set_sensitive(True)

    def trigger_restart_and_close(self):
        self.destroy()
        # Funciones originales para reiniciar la aplicación principal
        kill_processes()
        run_disowned_command()
        return False # Para GLib si se usa en timeout

    def show_message_dialog(self, title, message, message_type, callback_on_ok=None):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0, # Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
            message_type=message_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        if callback_on_ok:
            dialog.connect("response", lambda d, response_id: [d.destroy(), callback_on_ok() if response_id == Gtk.ResponseType.OK else d.destroy()])
        else:
            dialog.connect("response", lambda d, response_id: d.destroy())
        dialog.show_all()


    def on_window_destroyed(self, _widget):
        # Cualquier limpieza necesaria si la ventana se cierra prematuramente
        if self.quit_gtk_main_on_destroy:
            Gtk.main_quit()

# --- Update Checking Logic (Lógica de comprobación de actualizaciones) ---
def _initiate_update_check_flow(is_standalone_mode):
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE
    if not is_connected():
        print("No internet connection. Skipping update check.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)
        return

    snooze_file_path = get_snooze_file_path()
    if os.path.exists(snooze_file_path):
        try:
            with open(snooze_file_path, "r") as f:
                snooze_timestamp = float(f.read().strip())
            if time.time() - snooze_timestamp < SNOOZE_DURATION_SECONDS:
                snooze_until_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(snooze_timestamp + SNOOZE_DURATION_SECONDS))
                print(f"Update check snoozed. Will check again after {snooze_until_time_str}.")
                if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
                    GLib.idle_add(Gtk.main_quit)
                return
            else:
                print("Snooze period expired. Removing snooze file.")
                os.remove(snooze_file_path)
        except Exception as e:
            print(f"Error processing snooze file {snooze_file_path}: {e}. Removing and proceeding.")
            try:
                os.remove(snooze_file_path)
            except OSError as e_remove:
                print(f"Error removing problematic snooze file: {e_remove}")
    
    print("Fetching remote version information...")
    fetch_remote_version() # Descarga REMOTE_VERSION_FILE
    current_version, _ = get_local_version()
    latest_version, changelog, _ = get_remote_version() # Lee de REMOTE_VERSION_FILE

    print(f"Current version: {current_version}, Latest version: {latest_version}")

    # Compara versiones (mejorar con packaging.version para semver robusto si es necesario)
    if latest_version > current_version and latest_version != "0.0.0":
        print(f"New version {latest_version} found. Current is {current_version}.")
        GLib.idle_add(launch_update_window, latest_version, changelog, is_standalone_mode)
    else:
        print(f"{data.APP_NAME_CAP} is up to date or remote version is invalid ({latest_version} vs {current_version}).")
        if os.path.exists(REMOTE_VERSION_FILE): # Limpiar el archivo temporal si no hay actualización
            try:
                os.remove(REMOTE_VERSION_FILE)
            except OSError:
                pass # No es crítico
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)

def launch_update_window(latest_version, changelog, is_standalone_mode):
    win = UpdateWindow(latest_version, changelog, is_standalone_mode)
    if is_standalone_mode:
        win.quit_gtk_main_on_destroy = True
    win.show_all()
    # Si hay un terminal, es bueno darle foco.
    if hasattr(win, 'terminal'):
        win.terminal.grab_focus()


def check_for_updates():
    """
    Función pública para verificar actualizaciones. Ejecuta las verificaciones en un hilo separado.
    """
    thread = threading.Thread(target=_initiate_update_check_flow, args=(False,), daemon=True)
    thread.start()

def run_updater():
    """
    Función principal para ejecutar el actualizador como una aplicación independiente.
    """
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE
    _QUIT_GTK_IF_NO_WINDOW_STANDALONE = True 
    
    # Es importante que las operaciones GTK se inicien desde el hilo principal,
    # pero _initiate_update_check_flow puede usar GLib.idle_add para la UI.
    update_check_thread = threading.Thread(target=_initiate_update_check_flow, args=(True,), daemon=True)
    update_check_thread.start()
    
    Gtk.main()

# --- Punto de entrada para ejecución directa (opcional, para probar) ---
if __name__ == "__main__":
    # Para probar este script directamente, necesitarás un mock de `config.data`
    # y `fabric.utils.helpers.get_relative_path` o ajustar las rutas.
    # Ejemplo de mock básico:
    class MockData:
        APP_NAME = "MyTestApp"
        APP_NAME_CAP = "MyTestApp"
        CACHE_DIR = os.path.expanduser(f"~/.cache/{APP_NAME}")
        HOME_DIR = os.path.expanduser("~")

    data = MockData() # Sobrescribir el import con el mock

    # Mockear get_relative_path si es necesario o ajustar VERSION_FILE
    def mock_get_relative_path(path_from_current_file):
        # Asumir que version.json está en el mismo dir que este script para la prueba
        if path_from_current_file == "../utils/version.json":
            return os.path.join(os.path.dirname(__file__), "version.json")
        return path_from_current_file
    
    get_relative_path = mock_get_relative_path
    VERSION_FILE = get_relative_path("../utils/version.json") # Re-evaluar con mock

    # Crear un version.json de ejemplo para probar
    if not os.path.exists(VERSION_FILE):
        os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
        with open(VERSION_FILE, "w") as f:
            json.dump({"version": "0.0.1", "changelog": ["Initial test version"]}, f)
            print(f"Created dummy version file: {VERSION_FILE}")
    
    # Asegurar que el directorio de caché exista para el snooze file
    os.makedirs(data.CACHE_DIR, exist_ok=True)

    print("Running updater in standalone test mode...")
    run_updater()
