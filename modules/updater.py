import os
import time

import gi

# Configuración para terminal embebida VTE
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk, GLib, Gtk, Vte

import config.data as data

# Nombre del archivo de snooze y duración en segundos (8 horas)
SNOOZE_FILE_NAME = "updater_snooze.txt"
SNOOZE_DURATION_SECONDS = 8 * 60 * 60  # 8 horas

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

class UpdateWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=f"{data.APP_NAME_CAP} Updater")
        self.set_default_size(500, 200)
        self.set_border_width(16)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        # Contenedor principal
        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(self.main_vbox)

        # Texto informativo
        info_label = Gtk.Label(
            label=f"Hay una actualización disponible para {data.APP_NAME_CAP}."
        )
        info_label.set_xalign(0)
        info_label.set_line_wrap(True)
        self.main_vbox.pack_start(info_label, False, False, 0)

        # Contenedor de botones
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END)
        self.main_vbox.pack_start(action_box, False, False, 10)

        # Botón "Update"
        self.update_button = Gtk.Button(label="Update")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self.on_update_clicked)
        action_box.pack_end(self.update_button, False, False, 0)

        # Botón "Later"
        self.later_button = Gtk.Button(label="Later")
        self.later_button.connect("clicked", self.on_later_clicked)
        action_box.pack_end(self.later_button, False, False, 0)

        # Espacio reservado para la terminal VTE (se crea al hacer clic en "Update")
        self.terminal_container = None
        self.vte_terminal = None

        self.connect("destroy", Gtk.main_quit)

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
        Al presionar 'Update', deshabilita botones y crea la terminal VTE para ejecutar el script.
        """
        self.update_button.set_sensitive(False)
        self.later_button.set_sensitive(False)

        # Si no existe el contenedor de la terminal, lo creamos
        if self.terminal_container is None:
            # Contenedor scrolleable
            self.terminal_container = Gtk.ScrolledWindow()
            self.terminal_container.set_hexpand(True)
            self.terminal_container.set_vexpand(True)
            self.terminal_container.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            # Terminal VTE
            self.vte_terminal = Vte.Terminal()
            self.vte_terminal.set_size(120, 24)
            # Aumentamos el tamaño de la ventana para dar espacio a la terminal
            self.set_default_size(720, 400)
            self.terminal_container.add(self.vte_terminal)
            self.main_vbox.pack_start(self.terminal_container, True, True, 0)

        self.show_all()

        # Comando de actualización: descarga y ejecuta el instalador
        curl_command = "curl -fsSL https://raw.githubusercontent.com/Axenide/Ax-Shell/main/install.sh | bash"

        # Ejecuta el comando dentro de la VTE
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
        Callback al terminar el script de actualización. Cierra la ventana.
        """
        # Opcional: podrías mostrar un mensaje basado en exit_status aquí antes de cerrar.
        self.destroy()

def run_updater():
    win = UpdateWindow()
    win.show_all()
    Gtk.main()
