import json
import os
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk, GLib, Gtk, Vte

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fabric.utils.helpers import get_relative_path

import config.data as data

VERSION_FILE = get_relative_path("../utils/version.json")
REMOTE_VERSION_FILE = "/tmp/remote_version.json"
REMOTE_URL = "https://raw.githubusercontent.com/Axenide/Ax-Shell/refs/heads/main/utils/version.json"
REPO_DIR = get_relative_path("../")

SNOOZE_FILE_NAME = "updater_snooze.txt"
SNOOZE_DURATION_SECONDS = 8 * 60 * 60

_QUIT_GTK_IF_NO_WINDOW_STANDALONE = False

def get_snooze_file_path():
    """
    Devuelve la ruta al archivo de 'snooze' dentro de ~/.cache/APP_NAME.
    """
    cache_dir_base = data.CACHE_DIR or os.path.expanduser(f"~/.cache/{data.APP_NAME}")
    try:
        os.makedirs(cache_dir_base, exist_ok=True)
    except Exception as e:
        print(f"Error creando directorio de cache {cache_dir_base}: {e}")
    return os.path.join(cache_dir_base, SNOOZE_FILE_NAME)

def fetch_remote_version():
    """
    Descarga el JSON de versión remota usando curl, con timeout y manejo de errores.
    """
    try:
        subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", REMOTE_URL, "-o", REMOTE_VERSION_FILE],
            check=False,
            timeout=15
        )
    except subprocess.TimeoutExpired:
        print("Error: curl ha expirado al obtener la versión remota.")
    except FileNotFoundError:
        print("Error: curl no encontrado. Instala curl, por favor.")
    except Exception as e:
        print(f"Error obteniendo versión remota: {e}")

def get_local_version():
    """
    Lee el archivo local de versión y devuelve (version, changelog).
    """
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r") as f:
                data_content = json.load(f)
                return data_content.get("version", "0.0.0"), data_content.get("changelog", [])
        except json.JSONDecodeError:
            print(f"Error: JSON inválido en el archivo local: {VERSION_FILE}")
            return "0.0.0", []
        except Exception as e:
            print(f"Error leyendo archivo local de versión {VERSION_FILE}: {e}")
            return "0.0.0", []
    return "0.0.0", []

def get_remote_version():
    """
    Lee el archivo remoto descargado y devuelve (version, changelog, download_url).
    """
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            with open(REMOTE_VERSION_FILE, "r") as f:
                data_content = json.load(f)
                return (
                    data_content.get("version", "0.0.0"),
                    data_content.get("changelog", []),
                    data_content.get("download_url", "
                )
        except json.JSONDecodeError:
            print(f"Error: JSON inválido en el archivo remoto: {REMOTE_VERSION_FILE}")
            return "0.0.0", [], "
        except Exception as e:
            print(f"Error leyendo archivo remoto de versión {REMOTE_VERSION_FILE}: {e}")
            return "0.0.0", [], "
    return "0.0.0", [], "

def update_local_version_file():
    """
    Reemplaza la versión local con la remota, moviendo el JSON descargado al archivo de versiones local.
    """
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            shutil.move(REMOTE_VERSION_FILE, VERSION_FILE)
        except Exception as e:
            print(f"Error actualizando archivo local de versión: {e}")
            raise

def kill_processes():
    """
    Mata los procesos de la aplicación original antes de reiniciar.
    """
    subprocess.run(["pkill", data.APP_NAME], check=False)

def run_disowned_command():
    """
    Lanza la aplicación nuevamente en background usando uwsgi, similar al comportamiento original.
    """
    try:
        command = (
            f"bash -c 'killall -q {data.APP_NAME}; sleep 0.2; "
            f"uwsm app -- python {data.HOME_DIR}/.config/{data.APP_NAME_CAP}/main.py'"
        )
        subprocess.Popen(
            command,
            shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"{data.APP_NAME_CAP} proceso reiniciado en background.")
    except Exception as e:
        print(f"Error reiniciando {data.APP_NAME_CAP} en background: {e}")

def is_connected():
    """
    Verifica conectividad básica intentando conectar a www.google.com:80.
    """
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False

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

        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(self.main_vbox)

        title_label = Gtk.Label(name="update-title")
        title_label.set_markup("<span size='xx-large' weight='bold'>📦 Update Available ✨</span>")
        title_label.get_style_context().add_class("title-1")
        self.main_vbox.pack_start(title_label, False, False, 10)

        info_label = Gtk.Label(
            label=f"A new version ({latest_version}) of {data.APP_NAME_CAP} is available."
        )
        info_label.set_xalign(0)
        info_label.set_line_wrap(True)
        self.main_vbox.pack_start(info_label, False, False, 0)

        changelog_header_label = Gtk.Label()
        changelog_header_label.set_markup("<b>Changelog:</b>")
        changelog_header_label.set_xalign(0)
        self.main_vbox.pack_start(changelog_header_label, False, False, 5)

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
        self.main_vbox.pack_start(scrolled_window, True, True, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_no_show_all(True)
        self.progress_bar.set_visible(False)
        self.main_vbox.pack_start(self.progress_bar, False, False, 5)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END)
        self.main_vbox.pack_start(action_box, False, False, 10)

        self.update_button = Gtk.Button(name="update-button", label="Update")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self.on_update_clicked)
        action_box.pack_end(self.update_button, False, False, 0)

        self.close_button = Gtk.Button(name="later-button", label="Later")
        self.close_button.connect("clicked", self.on_later_clicked)
        action_box.pack_end(self.close_button, False, False, 0)

        self.connect("destroy", self.on_window_destroyed)

        self.terminal_container = None
        self.vte_terminal = None

    def on_later_clicked(self, _widget):
        """
        Al hacer clic en 'Later', crea/actualiza archivo de snooze y cierra la ventana.
        """
        snooze_file_path = get_snooze_file_path()
        try:
            with open(snooze_file_path, "w") as f:
                f.write(str(time.time()))
            print(f"Update snoozed. Snooze file en: {snooze_file_path}")
        except Exception as e:
            print(f"Error creando snooze file {snooze_file_path}: {e}")
        self.destroy()

    def on_update_clicked(self, _widget):
        """
        Al presionar 'Update', se deshabilitan botones, se oculta la progress bar
        y se crea una terminal VTE donde se corre el script curl | bash.
        """

        self.update_button.set_sensitive(False)
        self.close_button.set_sensitive(False)

        self.progress_bar.set_visible(False)

        if self.terminal_container is None:

            self.terminal_container = Gtk.ScrolledWindow()
            self.terminal_container.set_hexpand(True)
            self.terminal_container.set_vexpand(True)
            self.terminal_container.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            self.vte_terminal = Vte.Terminal()
            self.vte_terminal.set_size(120, 48)
            self.terminal_container.add(self.vte_terminal)

            self.main_vbox.pack_start(self.terminal_container, True, True, 0)

        self.show_all()

        curl_command = "curl -fsSL https://raw.githubusercontent.com/Axenide/Ax-Shell/main/install.sh | bash"

        self.vte_terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ.get("HOME", "/"),
            ["/bin/bash", "-lc", curl_command],
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            None,
            self.on_curl_script_exit,
            None
        )

    def on_curl_script_exit(self, terminal, exit_status, user_data):
        """
        Callback cuando el script terminado en la terminal VTE finaliza.
        Dependiendo del exit_status, se considera éxito o fallo.
        """

        if exit_status == 0:

            GLib.idle_add(self.handle_update_success)
        else:

            end_iter = self.vte_terminal.get_end_iter()
            start_iter = self.vte_terminal.get_iter_at_line(max(0, self.vte_terminal.get_line_count() - 5))
            error_excerpt = self.vte_terminal.get_text_range(start_iter, end_iter, False)
            GLib.idle_add(self.handle_update_failure, f"Script terminó con status {exit_status}. Últimas líneas:\n{error_excerpt}")

    def handle_update_success(self):
        """
        Muestra mensaje de éxito en la progress bar y reinicia la aplicación tras 2 segundos.
        """

        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")

        if self.terminal_container:
            self.main_vbox.remove(self.terminal_container)

        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Update Complete. Restarting application...")
        self.progress_bar.set_show_text(True)

        self.show_all()

        GLib.timeout_add_seconds(2, self.trigger_restart_and_close)

    def trigger_restart_and_close(self):
        """
        Cierra la ventana y relanza la aplicación.
        """
        self.destroy()
        kill_processes()
        run_disowned_command()
        return False

    def handle_update_failure(self, error_message):
        """
        Muestra diálogo de error si falla la ejecución del script.
        """

        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")

        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Update Failed.")
        self.progress_bar.set_show_text(True)

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
        """
        Si la ventana se destruye y estamos en modo standalone, cerramos Gtk.main().
        """
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")

        if self.quit_gtk_main_on_destroy:
            Gtk.main_quit()

def _initiate_update_check_flow(is_standalone_mode):
    """
    Lógica que comprueba conexión, snooze y descarga versión remota.
    Si hay versión nueva, lanza la ventana de actualización.
    """
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE

    if not is_connected():
        print("No hay conexión a internet. Se omite chequeo de actualizaciones.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)
        return

    snooze_file_path = get_snooze_file_path()
    if os.path.exists(snooze_file_path):
        try:
            with open(snooze_file_path, "r") as f:
                snooze_timestamp_str = f.read().strip()
                snooze_timestamp = float(snooze_timestamp_str)

            current_time = time.time()
            if current_time - snooze_timestamp < SNOOZE_DURATION_SECONDS:
                snooze_until_time = snooze_timestamp + SNOOZE_DURATION_SECONDS
                snooze_until_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(snooze_until_time))
                print(f"Chequeo pospuesto. Se reanudará después de {snooze_until_time_str}.")
                if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
                    GLib.idle_add(Gtk.main_quit)
                return
            else:
                print("Periodo de snooze expirado. Eliminando archivo y chequeando actualizaciones.")
                os.remove(snooze_file_path)
        except ValueError:
            print(f"Error: contenido inválido en snooze file. Eliminando: {snooze_file_path}")
            try:
                os.remove(snooze_file_path)
            except OSError as e_remove:
                print(f"Error al eliminar snooze file corrupto: {e_remove}")
        except Exception as e_snooze:
            print(f"Error procesando snooze file {snooze_file_path}: {e_snooze}. Procediendo con chequeo.")
            try:
                os.remove(snooze_file_path)
            except OSError as e_remove_generic:
                print(f"Error al eliminar snooze file problemático: {e_remove_generic}")

    fetch_remote_version()

    current_version, _ = get_local_version()
    latest_version, changelog, _ = get_remote_version()

    if latest_version > current_version and latest_version != "0.0.0":
        GLib.idle_add(launch_update_window, latest_version, changelog, is_standalone_mode)
    else:
        print(f"{data.APP_NAME_CAP} está actualizado o la versión remota es inválida.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)

def launch_update_window(latest_version, changelog, is_standalone_mode):
    """
    Crea y muestra la ventana de actualización.
    """
    win = UpdateWindow(latest_version, changelog, is_standalone_mode)
    if is_standalone_mode:
        win.quit_gtk_main_on_destroy = True
    win.show_all()

def check_for_updates():
    """
    Función pública para módulo: lanza el chequeo de actualizaciones en background thread.
    """
    thread = threading.Thread(target=_initiate_update_check_flow, args=(False,), daemon=True)
    thread.start()

def run_updater():
    """
    Punto de entrada standalone: inicia Gtk.main y chequeo de actualizaciones.
    """
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE
    _QUIT_GTK_IF_NO_WINDOW_STANDALONE = True

    update_check_thread = threading.Thread(target=_initiate_update_check_flow, args=(True,), daemon=True)
    update_check_thread.start()

    Gtk.main()

if __name__ == "__main__":
    run_updater()
