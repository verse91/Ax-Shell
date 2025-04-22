import os
import subprocess
import re
from threading import Lock
from gi.repository import GLib
from loguru import logger
from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command_async, monitor_file
import utils.functions as helpers

class Brightness(Service):
    """Service to manage screen brightness levels using either ddcutil or brightnessctl backends."""

    instance = None
    DDCUTIL_PARAMS = "--disable-dynamic-sleep --sleep-multiplier=0.05 --noverify"

    @staticmethod
    def get_initial():
        """Singleton pattern implementation to get the Brightness service instance."""
        if Brightness.instance is None:
            Brightness.instance = Brightness()
        return Brightness.instance

    @Signal
    def screen(self, value: int) -> None: 
        """Signal emitted when screen brightness changes (value: current brightness level)."""
        pass

    def __init__(self, backend=None, **kwargs):
        """Initialize brightness service with automatic backend detection."""
        super().__init__(**kwargs)
        self._pending_brightness = None  # Pending brightness value to apply
        self._brightness_timer_id = None  # GLib timeout ID for delayed brightness changes
        self._lock = Lock()  # Thread lock for thread-safe operations
        self._last_brightness = -1  # Cache for last known brightness value
        self.backend = self._detect_backend(backend)  # Detected backend (ddcutil/brightnessctl)
        
        if self.backend:
            # Maximum brightness value depends on backend
            self.max_screen = 100 if self.backend == "ddcutil" else self._read_max_brightness()
            
            # For brightnessctl, monitor brightness file changes
            if self.backend == "brightnessctl":
                monitor_file(f"/sys/class/backlight/{self._get_screen_device()}/brightness").connect(
                    "changed", lambda _, f, *a: self._handle_brightness_change(f))

    def _handle_brightness_change(self, file):
        """Handler for brightness change events from monitored file."""
        new_value = round(int(file.load_bytes()[0].get_data()))
        if new_value != self._last_brightness:
            self._last_brightness = new_value
            self.emit("screen", new_value)

    def _detect_backend(self, backend):
        """Detect available brightness control backend (ddcutil or brightnessctl)."""
        if backend: 
            return backend
            
        # Check for ddcutil first
        if helpers.executable_exists("ddcutil"):
            bus = self._detect_ddcutil_bus()
            if bus != -1:
                self.ddcutil_bus = bus
                return "ddcutil"
                
        # Fallback to brightnessctl if available
        if helpers.executable_exists("brightnessctl") and self._get_screen_device():
            return "brightnessctl"
            
        logger.error("No available brightness backend")
        return None

    def _get_screen_device(self):
        """Get the first available backlight device from sysfs."""
        try: 
            return os.listdir("/sys/class/backlight")[0]
        except: 
            return ""

    def _detect_ddcutil_bus(self):
        """Detect the I2C bus number for ddcutil communication."""
        try:
            output = subprocess.check_output(["ddcutil", "detect"], text=True)
            match = re.search(r"I2C bus:\s*/dev/i2c-(\d+)", output)
            return int(match.group(1)) if match else -1
        except: 
            return -1

    def _read_max_brightness(self):
        """Read maximum brightness value from sysfs."""
        try:
            with open(f"/sys/class/backlight/{self._get_screen_device()}/max_brightness") as f:
                return int(f.readline())
        except: 
            return -1

    @Property(int, "read-write")
    def screen_brightness(self):
        """Get current screen brightness level (0-100%)."""
        if self.backend == "brightnessctl":
            try:
                with open(f"/sys/class/backlight/{self._get_screen_device()}/brightness") as f:
                    return int(f.readline())
            except: 
                return -1
        elif self.backend == "ddcutil":
            if self._last_brightness != -1: 
                return self._last_brightness
            try:
                cmd = f"ddcutil --bus {self.ddcutil_bus} {self.DDCUTIL_PARAMS} getvcp 10"
                output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=1)
                value = int(re.search(r"current value\s*=\s*(\d+)", output).group(1))
                self._last_brightness = value
                return value
            except: 
                return self._last_brightness if self._last_brightness != -1 else 50

    @screen_brightness.setter
    def screen_brightness(self, value: int):
        """Set new screen brightness level (0-100%)."""
        with self._lock:
            value = max(0, min(value, self.max_screen))
            if value == self._last_brightness: 
                return
            self._pending_brightness = value
            if self._brightness_timer_id: 
                GLib.source_remove(self._brightness_timer_id)
            self._brightness_timer_id = GLib.timeout_add(100, self._apply_brightness)

    def _apply_brightness(self):
        """Apply pending brightness change with debounce delay."""
        with self._lock:
            if not self._pending_brightness: 
                return False
            value = self._pending_brightness
            self._pending_brightness = None
            self._brightness_timer_id = None

        try:
            if self.backend == "brightnessctl":
                exec_shell_command_async(f"brightnessctl --device '{self._get_screen_device()}' set {value}")
            elif self.backend == "ddcutil":
                exec_shell_command_async(
                    f"ddcutil --bus {self.ddcutil_bus} {self.DDCUTIL_PARAMS} --terse setvcp 10 {value}",
                    lambda *_: self._update_brightness_cache(value))
            self._last_brightness = value
            self.emit("screen", int((value / self.max_screen) * 100))
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
        return False

    def _update_brightness_cache(self, value):
        """Update cached brightness value after successful change."""
        self._last_brightness = value
        self.emit("screen", int((value / self.max_screen) * 100))