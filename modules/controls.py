from fabric.audio.service import Audio
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.widgets.scale import Scale
from gi.repository import Gdk, GLib

import config.data as data
import modules.icons as icons
from services.brightness import Brightness
import threading
import time


class VolumeSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            h_align="fill",
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("vol")
        self._pending_value = None
        self._update_source_id = None
        self._debounce_timeout = 100
        self.on_speaker_changed()

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def on_value_changed(self, _):
        if self.audio.speaker:
            self._pending_value = self.value * 100
            if self._update_source_id is not None:
                GLib.source_remove(self._update_source_id)
            self._update_source_id = GLib.timeout_add(self._debounce_timeout, self._update_volume_callback)

    def _update_volume_callback(self):
        if self._pending_value is not None and self.audio.speaker:
            self.audio.speaker.volume = self._pending_value
            self._pending_value = None
        self._update_source_id = None
        return False

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        self.value = self.audio.speaker.volume / 100
        
        if self.audio.speaker.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")

class MicSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("mic")
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def on_value_changed(self, _):
        if self.audio.microphone:
            self.audio.microphone.volume = self.value * 100

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        self.value = self.audio.microphone.volume / 100
        

        if self.audio.microphone.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")

class BrightnessSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(5, 10),
            **kwargs,
        )
        self.client = Brightness.get_initial()
        if self.client.screen_brightness == -1:
            self.destroy()
            return

        self.set_range(0, self.client.max_screen)
        self.set_value(self.client.screen_brightness)
        self.add_style_class("brightness")

        self._pending_value = None
        self._update_source_id = None
        self._updating_from_brightness = False
        self._debounce_timeout = 100

        self.connect("change-value", self.on_scale_move)
        self.connect("scroll-event", self.on_scroll)
        self.client.connect("screen", self.on_brightness_changed)

    def on_scale_move(self, widget, scroll, moved_pos):
        if self._updating_from_brightness:
            return False
        self._pending_value = moved_pos
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        self._update_source_id = GLib.timeout_add(self._debounce_timeout, self._update_brightness_callback)
        return False

    def _update_brightness_callback(self):
        if self._pending_value is not None:
            value_to_set = self._pending_value
            self._pending_value = None
            if value_to_set != self.client.screen_brightness:
                self.client.screen_brightness = value_to_set
            self._update_source_id = None
            return False
        else:
            self._update_source_id = None
            return False

    def on_scroll(self, widget, event):
        current_value = self.get_value()
        step_size = 1
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < 0:
                new_value = min(current_value + step_size, self.client.max_screen)
            elif event.delta_y > 0:
                new_value = max(current_value - step_size, 0)
            else:
                return False
        else:
            if event.direction == Gdk.ScrollDirection.UP:
                new_value = min(current_value + step_size, self.client.max_screen)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                new_value = max(current_value - step_size, 0)
            else:
                return False
        self.set_value(new_value)
        return True

    def on_brightness_changed(self, client, _):
        self._updating_from_brightness = True
        self.set_value(self.client.screen_brightness)
        self._updating_from_brightness = False
        percentage = int((self.client.screen_brightness / self.client.max_screen) * 100)
        self.set_tooltip_text(f"{percentage}%")

    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        super().destroy()

class BrightnessSmall(Button):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-brightness", **kwargs)
        # Ensure Button can receive scroll and pointer events
        self.add_events(
            Gdk.EventMask.SCROLL_MASK | 
            Gdk.EventMask.SMOOTH_SCROLL_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        
        self.brightness = Brightness.get_initial()
        if self.brightness.screen_brightness == -1:
            self.destroy()
            return

        self.progress_bar = CircularProgressBar(
            name="button-brightness", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.brightness_label = Label(name="brightness-label", markup=icons.brightness_high)
        self.brightness_button = Button(child=self.brightness_label)
        self.brightness_level = Label(name="brightness-level", label="0%")
        self.brightness_revealer = Revealer(
            name="brightness-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.brightness_level,
            child_revealed=False,
        )
        
        overlay_box = Overlay(
            child=self.progress_bar,
            overlays=self.brightness_button
        )
        
        main_box = Box(
            name="brightness-box",
            orientation="h",
            spacing=0,
            children=[overlay_box, self.brightness_revealer],
        )
        # Ensure the revealer and its child are visible
        self.brightness_revealer.show_all()
        
        # Add scroll event handling to the overlay_box via EventBox
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=main_box,
        )
        self.event_box.connect("scroll-event", self.on_scroll)
        # Also connect scroll to Button to ensure events are received
        self.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        
        # Connect hover events directly to self (Button) - Button widgets handle these naturally
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        self._updating_from_brightness = False
        self._pending_value = None
        self._update_source_id = None
        self._debounce_timeout = 100
        self._scroll_pending_value = None
        self._scroll_update_source_id = None
        self._scroll_processing = False
        self.hide_timer = None
        self.hover_counter = 0

        self.progress_bar.connect("notify::value", self.on_progress_value_changed)
        self.brightness.connect("screen", self.on_brightness_changed)
        self.on_brightness_changed()

    def on_scroll(self, widget, event):
        if self.brightness.max_screen == -1:
            return False
        
        # Prevent duplicate processing if already handling a scroll event
        if self._scroll_processing:
            return True

        step_size = 5
        current_brightness = self.brightness.screen_brightness
        
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            # Smooth scrolling (trackpad)
            if event.delta_y < 0:
                new_brightness = min(current_brightness + step_size, self.brightness.max_screen)
            elif event.delta_y > 0:
                new_brightness = max(current_brightness - step_size, 0)
            else:
                return False
        elif event.direction == Gdk.ScrollDirection.UP:
            # Scroll up - increase brightness
            new_brightness = min(current_brightness + step_size, self.brightness.max_screen)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            # Scroll down - decrease brightness
            new_brightness = max(current_brightness - step_size, 0)
        else:
            return False
        
        if new_brightness != current_brightness:
            # Use debounced update to prevent rapid duplicate calls
            self._scroll_processing = True
            self._scroll_pending_value = new_brightness
            if self._scroll_update_source_id is not None:
                GLib.source_remove(self._scroll_update_source_id)
            self._scroll_update_source_id = GLib.timeout_add(50, self._update_brightness_from_scroll)
            # Return True to stop event propagation
            return True
        
        return False
    
    def _update_brightness_from_scroll(self):
        if self._scroll_pending_value is not None:
            self.brightness.screen_brightness = self._scroll_pending_value
            self._scroll_pending_value = None
        self._scroll_update_source_id = None
        return False

    def on_progress_value_changed(self, widget, pspec):
        if self._updating_from_brightness:
            return
        new_norm = widget.value
        new_brightness = int(new_norm * self.brightness.max_screen)
        self._pending_value = new_brightness
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        self._update_source_id = GLib.timeout_add(self._debounce_timeout, self._update_brightness_callback)

    def _update_brightness_callback(self):
        if self._pending_value is not None and self._pending_value != self.brightness.screen_brightness:
            self.brightness.screen_brightness = self._pending_value
            self._pending_value = None
        self._update_source_id = None
        return False

    def on_mouse_enter(self, widget, event):
        if not data.VERTICAL:
            self.hover_counter += 1
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
                self.hide_timer = None
            self.brightness_revealer.set_reveal_child(True)
            return False

    def on_mouse_leave(self, widget, event):
        if not data.VERTICAL:
            if self.hover_counter > 0:
                self.hover_counter -= 1
            if self.hover_counter == 0:
                if self.hide_timer is not None:
                    GLib.source_remove(self.hide_timer)
                self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
            return False

    def hide_revealer(self):
        if not data.VERTICAL:
            self.brightness_revealer.set_reveal_child(False)
            self.hide_timer = None
            return False

    def on_brightness_changed(self, *args):
        if self.brightness.max_screen == -1:
            return
        normalized = self.brightness.screen_brightness / self.brightness.max_screen
        self._updating_from_brightness = True
        self.progress_bar.value = normalized
        self._updating_from_brightness = False

        brightness_percentage = int(normalized * 100)
        self.brightness_level.set_label(f"{brightness_percentage}%")
        if brightness_percentage >= 75:
            self.brightness_label.set_markup(icons.brightness_high)
        elif brightness_percentage >= 24:
            self.brightness_label.set_markup(icons.brightness_medium)
        else:
            self.brightness_label.set_markup(icons.brightness_low)
        self.set_tooltip_text(f"{brightness_percentage}%")

    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        if self._scroll_update_source_id is not None:
            GLib.source_remove(self._scroll_update_source_id)
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
        super().destroy()

class VolumeSmall(Button):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-vol", **kwargs)
        # Ensure Button can receive scroll and pointer events
        self.add_events(
            Gdk.EventMask.SCROLL_MASK | 
            Gdk.EventMask.SMOOTH_SCROLL_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        
        self.audio = Audio()
        self.progress_bar = CircularProgressBar(
            name="button-volume", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.vol_label = Label(name="vol-label", markup=icons.vol_high)
        self.vol_button = Button(on_clicked=self.toggle_mute, child=self.vol_label)
        self.vol_level = Label(name="vol-level", label="0%", visible=True)
        self.vol_revealer = Revealer(
            name="vol-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.vol_level,
            child_revealed=False,
            visible=True,
        )
        
        overlay_box = Overlay(child=self.progress_bar, overlays=self.vol_button)
        
        main_box = Box(
            name="vol-box",
            orientation="h",
            spacing=0,
            children=[overlay_box, self.vol_revealer],
        )
        
        # Add scroll event handling via EventBox
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=main_box,
        )
        
        # Headphone detection
        self._last_device_state = None
        self._headphone_thread = None
        self._headphone_running = False
        
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()
        self.event_box.connect("scroll-event", self.on_scroll)
        # Also connect scroll to Button to ensure it works
        self.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        
        # Connect hover events directly to self (Button) like MetricsSmall does
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        
        # Start headphone detection thread
        self._start_headphone_detection()
        
        self.hide_timer = None
        self.hover_counter = 0

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def toggle_mute(self, event):
        current_stream = self.audio.speaker
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.on_speaker_changed()
                self.progress_bar.add_style_class("muted")
                self.vol_label.add_style_class("muted")
            else:
                self.on_speaker_changed()
                self.progress_bar.remove_style_class("muted")
                self.vol_label.remove_style_class("muted")

    def on_scroll(self, _, event):
        if not self.audio.speaker:
            return False
            
        step_size = 5  # Volume step size
        
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            # Smooth scrolling (trackpad)
            if abs(event.delta_y) > 0:
                new_volume = self.audio.speaker.volume - (event.delta_y * step_size)
                self.audio.speaker.volume = max(0, min(100, new_volume))
                return True
            if abs(event.delta_x) > 0:
                new_volume = self.audio.speaker.volume + (event.delta_x * step_size)
                self.audio.speaker.volume = max(0, min(100, new_volume))
                return True
        elif event.direction == Gdk.ScrollDirection.UP:
            # Scroll up - increase volume
            new_volume = min(100, self.audio.speaker.volume + step_size)
            self.audio.speaker.volume = new_volume
            return True
        elif event.direction == Gdk.ScrollDirection.DOWN:
            # Scroll down - decrease volume
            new_volume = max(0, self.audio.speaker.volume - step_size)
            self.audio.speaker.volume = new_volume
            return True
        
        return False

    def _start_headphone_detection(self):
        """Start the headphone detection thread"""
        if self._headphone_thread and self._headphone_thread.is_alive():
            return
            
        self._headphone_running = True
        self._headphone_thread = threading.Thread(target=self._headphone_detection_loop, daemon=True)
        self._headphone_thread.start()
    
    def _headphone_detection_loop(self):
        """Main headphone detection loop running in background thread"""
        while self._headphone_running:
            try:
                self._check_headphone_state()
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                print(f"Headphone detection error: {e}")
                time.sleep(1)
    
    def _check_headphone_state(self):
        """Check if headphones are connected and update icon accordingly"""
        if not self.audio.speaker:
            current_state = "no_device"
        else:
            try:
                device_type = self.audio.speaker.port.type
                if device_type == 'headphones':
                    current_state = "headphones"
                else:
                    current_state = "speaker"
            except AttributeError:
                # Fallback: check if device name contains "headphone" or similar
                device_name = getattr(self.audio.speaker, 'name', '').lower()
                if any(keyword in device_name for keyword in ['headphone', 'headset', 'earphone', 'earbud']):
                    current_state = "headphones"
                else:
                    current_state = "speaker"
        
        # Only update if state changed
        if current_state != self._last_device_state:
            self._last_device_state = current_state
            GLib.idle_add(self._update_volume_icon, current_state)
    
    def on_mouse_enter(self, widget, event):
        if not data.VERTICAL:
            self.hover_counter += 1
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
                self.hide_timer = None
            self.vol_revealer.set_reveal_child(True)
            return False

    def on_mouse_leave(self, widget, event):
        if not data.VERTICAL:
            if self.hover_counter > 0:
                self.hover_counter -= 1
            if self.hover_counter == 0:
                if self.hide_timer is not None:
                    GLib.source_remove(self.hide_timer)
                self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
            return False

    def hide_revealer(self):
        if not data.VERTICAL:
            self.vol_revealer.set_reveal_child(False)
            self.hide_timer = None
            return False

    def _update_volume_icon(self, device_state):
        """Update volume icon based on device state"""
        if not self.audio.speaker:
            self.vol_label.set_markup("")
            self.set_tooltip_text("No audio device")
            return False
            
        if self.audio.speaker.muted:
            # When muted, always show muted icon regardless of device type
            self.vol_label.set_markup(icons.vol_mute)
            self.progress_bar.add_style_class("muted")
            self.vol_label.add_style_class("muted")
            self.vol_level.set_label("Muted")
            self.set_tooltip_text("Muted")
        else:
            # When not muted, show appropriate icon based on device type
            self.progress_bar.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")
            
            volume = round(self.audio.speaker.volume)
            self.vol_level.set_label(f"{volume}%")
            
            if device_state == "headphones":
                self.vol_label.set_markup(icons.headphones)
            else:
                # Show volume level icon for speakers
                if volume > 74:
                    self.vol_label.set_markup(icons.vol_high)
                elif volume > 0:
                    self.vol_label.set_markup(icons.vol_medium)
                else:
                    self.vol_label.set_markup(icons.vol_off)
            
            self.set_tooltip_text(f"{volume}%")
        
        # Update progress bar
        self.progress_bar.value = self.audio.speaker.volume / 100
        return False

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            self.vol_level.set_label("0%")
            return

        # Update volume percentage immediately
        if self.audio.speaker.muted:
            self.vol_level.set_label("Muted")
        else:
            volume = round(self.audio.speaker.volume)
            self.vol_level.set_label(f"{volume}%")
        
        # Update progress bar
        self.progress_bar.value = self.audio.speaker.volume / 100

        # Trigger device state check for icon update
        self._check_headphone_state()

    def destroy(self):
        # Stop headphone detection thread
        self._headphone_running = False
        if self._headphone_thread and self._headphone_thread.is_alive():
            self._headphone_thread.join(timeout=1)
        
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
        super().destroy()

class MicSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-mic", **kwargs)
        self.audio = Audio()
        self.progress_bar = CircularProgressBar(
            name="button-mic", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.mic_label = Label(name="mic-label", markup=icons.mic)
        self.mic_button = Button(on_clicked=self.toggle_mute, child=self.mic_label)
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(child=self.progress_bar, overlays=self.mic_button),
        )
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.add(self.event_box)
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def toggle_mute(self, event):
        current_stream = self.audio.microphone
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.mic_button.get_child().set_markup(icons.mic_mute)
                self.progress_bar.add_style_class("muted")
                self.mic_label.add_style_class("muted")
            else:
                self.on_microphone_changed()
                self.progress_bar.remove_style_class("muted")
                self.mic_label.remove_style_class("muted")

    def on_scroll(self, _, event):
        if not self.audio.microphone:
            return
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if abs(event.delta_y) > 0:
                self.audio.microphone.volume -= event.delta_y
            if abs(event.delta_x) > 0:
                self.audio.microphone.volume += event.delta_x

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        if self.audio.microphone.muted:
            self.mic_button.get_child().set_markup(icons.mic_mute)
            self.progress_bar.add_style_class("muted")
            self.mic_label.add_style_class("muted")
            self.set_tooltip_text("Muted")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.mic_label.remove_style_class("muted")
        self.progress_bar.value = self.audio.microphone.volume / 100
        self.set_tooltip_text(f"{round(self.audio.microphone.volume)}%")
        if self.audio.microphone.volume >= 1:
            self.mic_button.get_child().set_markup(icons.mic)
        else:
            self.mic_button.get_child().set_markup(icons.mic_mute)

class BrightnessIcon(Box):
    def __init__(self, **kwargs):
        super().__init__(name="brightness-icon", **kwargs)
        self.brightness = Brightness.get_initial()
        if self.brightness.screen_brightness == -1:
            self.destroy()
            return
            
        self.brightness_label = Label(name="brightness-label-dash", markup=icons.brightness_high, h_align="center", v_align="center", h_expand=True, v_expand=True)
        self.brightness_button = Button(child=self.brightness_label, h_align="center", v_align="center", h_expand=True, v_expand=True)
        

        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=self.brightness_button,
            h_align="center", 
            v_align="center", 
            h_expand=True, 
            v_expand=True
        )
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        
        self._pending_value = None
        self._update_source_id = None
        self._updating_from_brightness = False
        
        self.brightness.connect("screen", self.on_brightness_changed)
        self.on_brightness_changed()
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
    
    def on_scroll(self, _, event):
        if self.brightness.max_screen == -1:
            return
            
        step_size = 5
        current_brightness = self.brightness.screen_brightness
        
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < 0:
                new_brightness = min(current_brightness + step_size, self.brightness.max_screen)
            elif event.delta_y > 0:
                new_brightness = max(current_brightness - step_size, 0)
            else:
                return
        else:
            if event.direction == Gdk.ScrollDirection.UP:
                new_brightness = min(current_brightness + step_size, self.brightness.max_screen)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                new_brightness = max(current_brightness - step_size, 0)
            else:
                return
        
        self._pending_value = new_brightness
        if self._update_source_id is None:
            self._update_source_id = GLib.timeout_add(100, self._update_brightness_callback)
    
    def _update_brightness_callback(self):
        if self._pending_value is not None and self._pending_value != self.brightness.screen_brightness:
            self.brightness.screen_brightness = self._pending_value
            self._pending_value = None
            return True
        else:
            self._update_source_id = None
            return False
    
    def on_brightness_changed(self, *args):
        if self.brightness.max_screen == -1:
            return
            
        self._updating_from_brightness = True
        normalized = self.brightness.screen_brightness / self.brightness.max_screen
        brightness_percentage = int(normalized * 100)
        
        if brightness_percentage >= 75:
            self.brightness_label.set_markup("󰃠")
        elif brightness_percentage >= 24:
            self.brightness_label.set_markup("󰃠")
        else:
            self.brightness_label.set_markup("󰃠")
        self.set_tooltip_text(f"{brightness_percentage}%")
        self._updating_from_brightness = False
        
    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        super().destroy()

class VolumeIcon(Box):
    def __init__(self, **kwargs):
        super().__init__(name="vol-icon", **kwargs)
        self.audio = Audio()

        self.vol_label = Label(name="vol-label-dash", markup="", h_align="center", v_align="center", h_expand=True, v_expand=True)
        self.vol_button = Button(on_clicked=self.toggle_mute, child=self.vol_label, h_align="center", v_align="center", h_expand=True, v_expand=True)

        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=self.vol_button,
            h_align="center",
            v_align="center",
            h_expand=True,
            v_expand=True
        )
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)

        self._pending_value = None
        self._update_source_id = None
        
        # Headphone detection
        self._last_device_state = None
        self._headphone_thread = None
        self._headphone_running = False

        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)

        # Start headphone detection thread
        self._start_headphone_detection()
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

    def on_scroll(self, _, event):
        if not self.audio.speaker:
            return
            
        step_size = 5
        current_volume = self.audio.speaker.volume
        
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < 0:
                new_volume = min(current_volume + step_size, 100)
            elif event.delta_y > 0:
                new_volume = max(current_volume - step_size, 0)
            else:
                return
        else:
            if event.direction == Gdk.ScrollDirection.UP:
                new_volume = min(current_volume + step_size, 100)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                new_volume = max(current_volume - step_size, 0)
            else:
                return
                
        self._pending_value = new_volume
        if self._update_source_id is None:
            self._update_source_id = GLib.timeout_add(100, self._update_volume_callback)
            
    def _update_volume_callback(self):
        if self._pending_value is not None and self._pending_value != self.audio.speaker.volume:
            self.audio.speaker.volume = self._pending_value
            self._pending_value = None
            return True
        else:
            self._update_source_id = None
            return False
            
    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()
            
    def toggle_mute(self, event):
        current_stream = self.audio.speaker
        if current_stream:
            current_stream.muted = not current_stream.muted

            self.on_speaker_changed()

    def _start_headphone_detection(self):
        """Start the headphone detection thread"""
        if self._headphone_thread and self._headphone_thread.is_alive():
            return
            
        self._headphone_running = True
        self._headphone_thread = threading.Thread(target=self._headphone_detection_loop, daemon=True)
        self._headphone_thread.start()
    
    def _headphone_detection_loop(self):
        """Main headphone detection loop running in background thread"""
        while self._headphone_running:
            try:
                self._check_headphone_state()
                time.sleep(1)  # Check every 1 second
            except Exception as e:
                print(f"Headphone detection error: {e}")
                time.sleep(2)
    
    def _check_headphone_state(self):
        """Check if headphones are connected using PulseAudio"""
        current_state = self._detect_headphone_state()
        
        # Only update if state changed
        if current_state != self._last_device_state:
            self._last_device_state = current_state
            GLib.idle_add(self._update_volume_icon, current_state)
    
    def _detect_headphone_state(self):
        """Detect headphone state using PulseAudio directly"""
        try:
            import subprocess
            result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                output = result.stdout
                # Look for "Active Port:" line
                for line in output.split('\n'):
                    if 'Active Port:' in line:
                        active_port = line.split('Active Port:')[1].strip()
                        if 'headphone' in active_port.lower():
                            return "headphones"
                        else:
                            return "speaker"
        except Exception as e:
            print(f"PulseAudio detection error: {e}")
        
        # Default to speaker if detection fails
        return "speaker"
    
    def _update_volume_icon(self, device_state):
        """Update volume icon based on device state"""
        if self.audio.speaker and self.audio.speaker.muted:
            # When muted, always show muted icon
            self.vol_label.set_markup(icons.vol_mute)
            self.add_style_class("muted")
            self.vol_label.add_style_class("muted")
            self.vol_button.add_style_class("muted")
            self.set_tooltip_text("Muted")
        else:
            # When not muted, show appropriate icon based on device type
            self.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")
            self.vol_button.remove_style_class("muted")
            
            if device_state == "headphones":
                self.vol_label.set_markup(icons.headphones)
                self.set_tooltip_text("Headphones")
            else:
                # Show volume level icon for speakers
                if self.audio.speaker:
                    volume = self.audio.speaker.volume
                    if volume > 74:
                        self.vol_label.set_markup(icons.vol_high)
                    elif volume > 0:
                        self.vol_label.set_markup(icons.vol_medium)
                    else:
                        self.vol_label.set_markup(icons.vol_off)
                    self.set_tooltip_text(f"{round(volume)}%")
                else:
                    self.vol_label.set_markup(icons.vol_high)
                    self.set_tooltip_text("Speaker")
        
        return False

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            self.vol_label.set_markup("")
            self.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")
            self.vol_button.remove_style_class("muted")
            self.set_tooltip_text("No audio device")
            return

        # Trigger immediate update
        self._check_headphone_state()

    def update_device_icon(self):
        """Legacy method - now handled by headphone detection thread"""
        return True

    def destroy(self):
        # Stop headphone detection thread
        self._headphone_running = False
        if self._headphone_thread and self._headphone_thread.is_alive():
            self._headphone_thread.join(timeout=1)
            
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)

        if hasattr(self, '_periodic_update_source_id') and self._periodic_update_source_id is not None:
            GLib.source_remove(self._periodic_update_source_id)
        super().destroy()

class MicIcon(Box):
    def __init__(self, **kwargs):
        super().__init__(name="mic-icon", **kwargs)
        self.audio = Audio()
        
        self.mic_label = Label(name="mic-label-dash", markup=icons.mic, h_align="center", v_align="center", h_expand=True, v_expand=True)
        self.mic_button = Button(on_clicked=self.toggle_mute, child=self.mic_label, h_align="center", v_align="center", h_expand=True, v_expand=True)
        

        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=self.mic_button,
            h_align="center", 
            v_align="center", 
            h_expand=True, 
            v_expand=True
        )
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        
        self._pending_value = None
        self._update_source_id = None
        
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.on_microphone_changed()
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        
    def on_scroll(self, _, event):
        if not self.audio.microphone:
            return
            
        step_size = 5
        current_volume = self.audio.microphone.volume
        
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < 0:
                new_volume = min(current_volume + step_size, 100)
            elif event.delta_y > 0:
                new_volume = max(current_volume - step_size, 0)
            else:
                return
        else:
            if event.direction == Gdk.ScrollDirection.UP:
                new_volume = min(current_volume + step_size, 100)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                new_volume = max(current_volume - step_size, 0)
            else:
                return
                
        self._pending_value = new_volume
        if self._update_source_id is None:
            self._update_source_id = GLib.timeout_add(100, self._update_volume_callback)
            
    def _update_volume_callback(self):
        if self._pending_value is not None and self._pending_value != self.audio.microphone.volume:
            self.audio.microphone.volume = self._pending_value
            self._pending_value = None
            return True
        else:
            self._update_source_id = None
            return False
            
    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()
            
    def toggle_mute(self, event):
        current_stream = self.audio.microphone
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.mic_button.get_child().set_markup("")
                self.mic_label.add_style_class("muted")
                self.mic_button.add_style_class("muted")
            else:
                self.on_microphone_changed()
                self.mic_label.remove_style_class("muted")
                self.mic_button.remove_style_class("muted")
                
    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        if self.audio.microphone.muted:
            self.mic_button.get_child().set_markup("")
            self.add_style_class("muted")
            self.mic_label.add_style_class("muted")
            self.set_tooltip_text("Muted")
            return
        else:
            self.remove_style_class("muted")
            self.mic_label.remove_style_class("muted")
            
        self.set_tooltip_text(f"{round(self.audio.microphone.volume)}%")
        if self.audio.microphone.volume >= 1:
            self.mic_button.get_child().set_markup("")
        else:
            self.mic_button.get_child().set_markup("")
            
    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        super().destroy()

class ControlSliders(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-sliders",
            orientation="h",
            spacing=8,
            **kwargs,
        )
        
        brightness = Brightness.get_initial()
        

        if (brightness.screen_brightness != -1):
            brightness_row = Box(orientation="h", spacing=0, h_expand=True, h_align="fill")
            brightness_row.add(BrightnessIcon())
            brightness_row.add(BrightnessSlider())
            self.add(brightness_row)
            
        volume_row = Box(orientation="h", spacing=0, h_expand=True, h_align="fill")
        volume_row.add(VolumeIcon())
        volume_row.add(VolumeSlider())
        self.add(volume_row)
        
        mic_row = Box(orientation="h", spacing=0, h_expand=True, h_align="fill")
        mic_row.add(MicIcon())
        mic_row.add(MicSlider())
        self.add(mic_row)
        
        self.show_all()

class ControlSmall(Box):
    def __init__(self, **kwargs):
        brightness = Brightness.get_initial()
        children = []
        if (brightness.screen_brightness != -1):
            children.append(BrightnessSmall())
        children.extend([VolumeSmall(), MicSmall()])
        super().__init__(
            name="control-small",
            orientation="h" if not data.VERTICAL else "v",
            spacing=4,
            children=children,
            **kwargs,
        )
        self.show_all()
