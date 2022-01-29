import board
import analogio
import stage
import displayio
import busio
import time
import keypad
import audiocore
import audiopwmio
import supervisor
import digitalio


K_X = 0x01
K_O = 0x02
K_START = 0x04  # Y
K_SELECT = 0x08  # X
K_DOWN = 0x10
K_LEFT = 0x20
K_RIGHT = 0x40
K_UP = 0x80


# re-initialize the display for correct rotation and RGB mode

_TFT_INIT = (
    b"\x01\x80\x96"  # _SWRESET and Delay 150ms
    b"\x11\x80\xFF"  # _SLPOUT and Delay 500ms
    b"\x3A\x81\x55\x0A"  # _COLMOD and Delay 10ms
    b"\x36\x01\x08"  # _MADCTL
    b"\x21\x80\x0A"  # _INVON Hack and Delay 10ms
    b"\x13\x80\x0A"  # _NORON and Delay 10ms
    b"\x36\x01\xC0"  # _MADCTL
    b"\x29\x80\xFF"  # _DISPON and Delay 500ms
    b"\x36\xA0"  # 反转屏幕Y轴
)


class _Buttons:
    def __init__(self):
        self.keys = keypad.Keys((
            board.GP6,
            board.GP5,
            board.GP8,
            board.GP7
        ), value_when_pressed=False, pull=True, interval=0.05)
        self.last_state = 0
        self.event = keypad.Event(0, False)
        self.last_z_press = None
        self.joy_x = analogio.AnalogIn(board.A3)
        self.joy_y = analogio.AnalogIn(board.A2)

    def get_pressed(self):
        buttons = self.last_state
        events = self.keys.events
        while events:
            if events.get_into(self.event):
                bit = 1 << self.event.key_number
                if self.event.pressed:
                    buttons |= bit
                    self.last_state |= bit
                else:
                    self.last_state &= ~bit
        if buttons & K_START:
            now = time.monotonic()
            if self.last_z_press:
                if now - self.last_z_press > 2:
                    supervisor.set_next_code_file(None)
                    supervisor.reload()
            else:
                self.last_z_press = now
        else:
            self.last_z_press = None
        dead = 15000
        x = self.joy_x.value - 32767
        if x < -dead:
            buttons |= K_LEFT
        elif x > dead:
            buttons |= K_RIGHT
        y = self.joy_y.value - 32767
        if y < -dead:
            buttons |= K_UP
        elif y > dead:
            buttons |= K_DOWN
        return buttons


class _Audio:
    last_audio = None

    def __init__(self):
        self.muted = True
        self.buffer = bytearray(128)
        self.audio = audiopwmio.PWMAudioOut(board.GP23)

    def play(self, audio_file, loop=False):
        if self.muted:
            return
        self.stop()
        wave = audiocore.WaveFile(audio_file, self.buffer)
        self.audio.play(wave, loop=loop)

    def stop(self):
        self.audio.stop()

    def mute(self, value=True):
        self.muted = value


displayio.release_displays()
spi = busio.SPI(clock=board.GP2, MOSI=board.GP3)
tft_cs = board.GP18
tft_dc = board.GP1
display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP0)
display = displayio.Display(display_bus, _TFT_INIT, width=240, height=240,
                            rotation=180, auto_refresh=False, rowstart=0)
audio = _Audio()
buttons = _Buttons()