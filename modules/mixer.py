import gi
from fabric.audio.service import Audio
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.widgets.scrolledwindow import ScrolledWindow

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
            max_value=100,
            value=stream.volume,
            h_expand=True,
            v_align="center",
            has_origin=True,
            increments=(1, 5),
            draw_value=True,
            value_pos="right",
            style_classes=["no-icon"],
        )

        self.scale.connect("value-changed", self.on_volume_changed)
        stream.connect("changed", self.on_stream_changed)

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
        self.stream.volume = scale.get_value()

    def on_stream_changed(self, stream):
        self.scale.set_value(stream.volume)
        self.update_muted_state()

    def update_muted_state(self):
        if self.stream.muted:
            self.scale.add_style_class("muted")
        else:
            self.scale.remove_style_class("muted")


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
