import gi

gi.require_version('Gtk', '3.0')
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.stack import Stack

import config.data as data
from modules.bluetooth import BluetoothConnections
from modules.buttons import Buttons
from modules.calendar import Calendar
from modules.controls import ControlSliders
from modules.metrics import Metrics
from modules.network import NetworkConnections
from modules.notifications import NotificationHistory
from modules.player import Player


class Widgets(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dash-widgets",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )

        vertical_layout = False
        if data.PANEL_THEME == "Panel" and (data.BAR_POSITION in ["Left", "Right"] or data.PANEL_POSITION in ["Start", "End"]):
            vertical_layout = True

        # Determinar el modo de vista del calendario
        calendar_view_mode = "week" if vertical_layout else "month"
        
        # Instanciar Calendar con el view_mode apropiado
        self.calendar = Calendar(view_mode=calendar_view_mode)

        self.notch = kwargs["notch"]

        self.buttons = Buttons(widgets=self)
        self.bluetooth = BluetoothConnections(widgets=self)

        self.box_1 = Box(
            name="box-1",
            h_expand=True,
            v_expand=True,
        )

        self.box_2 = Box(
            name="box-2",
            h_expand=True,
            v_expand=True,
        )

        self.box_3 = Box(
            name="box-3",
            v_expand=True,
        )

        self.controls = ControlSliders()

        # self.calendar ya está inicializado arriba con el view_mode correcto

        self.player = Player()

        self.metrics = Metrics()

        self.notification_history = NotificationHistory()

        self.network_connections = NetworkConnections(widgets=self)

        self.applet_stack = Stack(
            h_expand=True,
            v_expand=True,
            transition_type="slide-left-right",
            children=[
                self.notification_history,
                self.network_connections,
                self.bluetooth,
            ]
        )

        self.applet_stack_box = Box(
            name="applet-stack",
            h_expand=True,
            v_expand=True,
            h_align="fill",
            children=[
                self.applet_stack,
            ]
        )

        # Modificar la definición de self.children_1 para usar self.calendar
        # y ajustar la disposición para el modo vertical
        if not vertical_layout:
            self.children_1 = [
                Box(
                    name="container-sub-1",
                    h_expand=True,
                    v_expand=True,
                    spacing=8,
                    children=[
                        self.calendar,  # Usar la instancia self.calendar
                        self.applet_stack_box,
                    ]
                ),
                self.metrics,
            ]
        else: # vertical_layout es True
            self.children_1 = [
                self.calendar, # Usar la instancia self.calendar (será semanal aquí)
                self.applet_stack_box,
                self.player,
            ]
            # En el diseño vertical, el reproductor se mueve aquí
            # y las métricas podrían necesitar una reubicación o ser omitidas
            # según el diseño deseado. Por ahora, se omite self.metrics
            # si no está explícitamente en la nueva lista.
            # Si self.player estaba en children_3, ahora está aquí.

        self.container_1 = Box(
            name="container-1",
            h_expand=True,
            v_expand=True,
            orientation="h" if not vertical_layout else "v",
            spacing=8,
            children=self.children_1,
        )

        self.container_2 = Box(
            name="container-2",
            h_expand=True,
            v_expand=True,
            orientation="v",
            spacing=8,
            children=[
                self.buttons,
                self.controls,
                self.container_1,
            ]
        )
        
        # Ajustar children_3 según si el reproductor se movió
        if not vertical_layout:
            self.children_3 = [
                self.player,
                self.container_2,
            ]
        else: # vertical_layout es True, self.player ya está en self.children_1
            self.children_3 = [
                self.container_2,
            ]


        self.container_3 = Box(
            name="container-3",
            h_expand=True,
            v_expand=True,
            orientation="h", # Esta orientación podría necesitar ser "v" si todo es vertical
            spacing=8,
            children=self.children_3,
        )

        self.add(self.container_3)

    def show_bt(self):
        self.applet_stack.set_visible_child(self.bluetooth)

    def show_notif(self):
        self.applet_stack.set_visible_child(self.notification_history)

    def show_network_applet(self):
        self.notch.open_notch("network_applet")
