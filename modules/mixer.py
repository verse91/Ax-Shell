import gi
from fabric.audio.service import Audio
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import GLib

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class MixerSlider(Box):
    def __init__(self, stream, **kwargs):
        super().__init__(
            orientation="v",
            spacing=4,
            h_expand=True,
            v_align="center",
        )

        self.stream = stream

        self.label = Label(
            label=stream.name or stream.description,
            h_expand=True,
            h_align="start",
            v_align="center",
            max_width_chars=15,
            ellipsize="end",
            wrap=False,
            single_line_mode=True,
        )

        self.scale = Scale(
            name="control-slider",
            orientation="h",
            min_value=0,
            max_value=1,
            value=stream.volume / 100,
            h_expand=True,
            v_align="center",
            has_origin=True,
            increments=(0.01, 0.1),
            draw_value=False,
            style_classes=["no-icon"],
        )

        # Add debouncing variables
        self._pending_value = None
        self._update_source_id = None
        self._updating_from_stream = False

        self.scale.connect("value-changed", self.on_volume_changed)
        stream.connect("changed", self.on_stream_changed)

        # Set tooltip to show volume percentage
        self.scale.set_tooltip_text(f"{stream.volume:.0f}%")

        # Apply appropriate style class based on stream type
        if hasattr(stream, "type"):
            if "microphone" in stream.type.lower() or "input" in stream.type.lower():
                self.scale.add_style_class("mic")
            else:
                self.scale.add_style_class("vol")
        else:
            # Default to volume style
            self.scale.add_style_class("vol")

        self.add(self.label)
        self.add(self.scale)

        # Set initial muted state
        self.update_muted_state()

    def on_volume_changed(self, scale):
        if self._updating_from_stream:
            return
        self._pending_value = scale.get_value()
        if self._update_source_id is None:
            self._update_source_id = GLib.timeout_add(50, self._update_volume_callback)

    def _update_volume_callback(self):
        if self._pending_value is not None:
            value_to_set = self._pending_value
            self._pending_value = None
            volume_percent = value_to_set * 100
            if volume_percent != self.stream.volume:
                self.stream.volume = volume_percent
                self.scale.set_tooltip_text(f"{volume_percent:.0f}%")
            return True
        else:
            self._update_source_id = None
            return False

    def on_stream_changed(self, stream):
        self._updating_from_stream = True
        self.scale.set_value(stream.volume / 100)
        self.scale.set_tooltip_text(f"{stream.volume:.0f}%")
        self.update_muted_state()
        self._updating_from_stream = False

    def update_muted_state(self):
        if self.stream.muted:
            self.scale.add_style_class("muted")
        else:
            self.scale.remove_style_class("muted")

    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        super().destroy()


class MixerSection(Box):
    def __init__(self, title, **kwargs):
        super().__init__(
            orientation="v",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        self.title_label = Label(
            label=title,
            h_align="center",
            v_align="start",
            style_classes=["mixer-section-title"],
        )

        self.content_box = Box(
            orientation="v",
            spacing=4,
            h_expand=True,
            v_expand=True,
        )

        self.add(self.title_label)
        self.add(self.content_box)

    def update_streams(self, streams):
        for child in self.content_box.get_children():
            self.content_box.remove(child)

        for stream in streams:
            slider = MixerSlider(stream)
            self.content_box.add(slider)

        self.content_box.show_all()


class Mixer(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="mixer",
            orientation="v",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        try:
            self.audio = Audio()
        except Exception as e:
            error_label = Label(
                label=f"Audio service unavailable: {str(e)}",
                h_align="center",
                v_align="center",
                h_expand=True,
                v_expand=True,
            )
            self.add(error_label)
            return

        self.main_container = Box(
            orientation="h",
            spacing=8,
            h_expand=True,
            v_expand=True,
        )

        self.main_container.set_homogeneous(True)

        self.outputs_section = MixerSection("Outputs")
        self.inputs_section = MixerSection("Inputs")

        self.main_container.add(self.outputs_section)
        self.main_container.add(self.inputs_section)

        self.scrolled = ScrolledWindow(
            h_expand=True,
            v_expand=True,
            child=self.main_container,
        )

        self.add(self.scrolled)

        self.audio.connect("changed", self.on_audio_changed)
        self.audio.connect("stream-added", self.on_audio_changed)
        self.audio.connect("stream-removed", self.on_audio_changed)

        self.update_mixer()

    def on_audio_changed(self, *args):
        self.update_mixer()

    def update_mixer(self):
        outputs = []
        inputs = []

        if self.audio.speaker:
            outputs.append(self.audio.speaker)
        outputs.extend(self.audio.applications)

        if self.audio.microphone:
            inputs.append(self.audio.microphone)
        inputs.extend(self.audio.recorders)

        self.outputs_section.update_streams(outputs)
        self.inputs_section.update_streams(inputs)
