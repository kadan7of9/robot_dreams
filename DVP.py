import time
import threading
import queue
import numpy as np
from ctypes import cast, POINTER, c_double

# from USB231_voltage_measurement import AI_RANGE
from scipy.signal import butter, sosfilt, sosfilt_zi

# MCC UL (mcculw)
from mcculw import ul
from mcculw.enums import ScanOptions, FunctionType, Status, ULRange, AnalogInputMode
from mcculw.device_info import DaqDeviceInfo

# Tkinter + Matplotlib
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ===================
# Configuration
# ===================
BOARD_NUM = 0  # Board number for MCC DAQ device
FS = 10_000  # samples/sec per channel (USB-231 max: 50 kS/s total, divided by 3 channels)
F0 = 2_000  # excitation frequency (must be < FS/2)

# Channels (edit if needed)
CH_EXC = 0  # excitation monitor (differential input)
CH_DIFF = 1  # differential probe output (differential input)
CH_ABS = 2  # absolute probe output (differential input)

LOW_CHAN = min(CH_EXC, CH_DIFF, CH_ABS)
HIGH_CHAN = max(CH_EXC, CH_DIFF, CH_ABS)
NUM_CHANS = HIGH_CHAN - LOW_CHAN + 1

AI_RANGE = (
    ULRange.BIP10VOLTS
)  # USB-231 supports: BIP10VOLTS, BIP5VOLTS, BIP2VOLTS, BIP1VOLTS

# Digital gain for each channel (applied to raw voltage readings)
GAIN_EXC = 10.0  # Excitation channel gain
GAIN_DIFF = 1.0  # Differential channel gain
GAIN_ABS = 1.0  # Absolute channel gain

# Processing parameters
# BLOCK_SIZE = 2048  # samples per channel per processing block (latency vs CPU)
# RING_BLOCKS = 40  # ring buffer length in blocks
# BASEBAND_FC = 500.0  # low-pass cutoff for baseband (Hz) - tune for scan dynamics
# LP_ORDER = 4
BLOCK_SIZE = 2048  # samples per channel per processing block (latency vs CPU)
RING_BLOCKS = 40  # ring buffer length in blocks
BASEBAND_FC = 100.0  # low-pass cutoff for baseband (Hz) - for 2kHz excitation (was 500.0 for 60kHz)
LP_ORDER = (
    6  # Increased order for better filtering at lower frequency (was 4 for 60kHz)
)

# Display parameters
DISPLAY_RATE = 1000  # decimated baseband points/sec to GUI
TIME_WINDOW_SEC = 5  # magnitude plot window
XY_WINDOW_SEC = 5  # XY plot window
UI_UPDATE_MS = 30  # —33 FPS update

# ===================
# Helpers
# ===================


def wrap_to_pi(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


class PhaseTracker:
    # Block-to-block phase smoother.
    def __init__(self, alpha=0.25):
        self.alpha = alpha
        self.phi = 0.0
        self.initialized = False

    def update(self, phi_meas):
        if not self.initialized:
            self.phi = phi_meas
            self.initialized = True
            return self.phi
        d = wrap_to_pi(phi_meas - self.phi)
        self.phi = self.phi + self.alpha * d
        return self.phi


# ===================
# MCC Continuous Acquisition (BACKGROUNDICONTINUOUS)
# ===================
class MCCContinuousAI:
    def __init__(
        self, board_num, low_chan, high_chan, fs, ring_blocks, block_size, ai_range
    ):
        self.board_num = board_num
        self.low_chan = low_chan
        self.high_chan = high_chan
        self.fs = fs
        self.ai_range = ai_range

        self.num_chans = high_chan - low_chan + 1
        self.block_size = block_size

        ## total_count must be a multiple of number of channels in scan
        self.total_count = ring_blocks * block_size * self.num_chans

        self.memhandle = None
        self.ctypes_array = None
        self.last_index = 0

    def start(self):
        daq_info = DaqDeviceInfo(self.board_num)
        if not daq_info.supports_analog_input:
            raise RuntimeError("DAQ does not support analog input.")

        ai_info = daq_info.get_ai_info()
        scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS

        # Use scaled data if supported (f10at64 volts) — easiest for DSP/plotting
        if ScanOptions.SCALEDATA in ai_info.supported_scan_options:
            scan_options |= ScanOptions.SCALEDATA
            self.memhandle = ul.scaled_win_buf_alloc(self.total_count)
            self.ctypes_array = cast(self.memhandle, POINTER(c_double))
        else:
            raise RuntimeError("SCALEDATA not supported; add raw conversion if needed.")

        if not self.memhandle:
            raise RuntimeError("Failed to allocate UL buffer.")

        # Try to set differential inputs for all three channels (skip if not supported)
        try:
            for ch in range(self.low_chan, self.high_chan + 1):
                ul.a_chan_input_mode(self.board_num, ch, AnalogInputMode.DIFFERENTIAL)
        except Exception:
            # Board doesn't support a_chan_input_mode - channels are configured by default
            pass

        # Start acquisition: rate is samples/sec per channel
        actual_rate = ul.a_in_scan(
            self.board_num,
            self.low_chan,
            self.high_chan,
            self.total_count,
            int(self.fs),
            self.ai_range,
            self.memhandle,
            scan_options,
        )
        self.fs = actual_rate

        # Initialize Last index
        status, cur_count, cur_index = ul.get_status(
            self.board_num, FunctionType.AIFUNCTION
        )
        self.last_index = cur_index

    def stop(self):
        try:
            ul.stop_background(self.board_num, FunctionType.AIFUNCTION)
        except Exception:
            pass
        if self.memhandle:
            ul.win_buf_free(self.memhandle)
            self.memhandle = None
            self.ctypes_array = None

    def read_new(self):
        # Return newly acquired samples as ndarray shape [N, num_chans] (interleaved low..high)
        status, cur_count, cur_index = ul.get_status(
            self.board_num, FunctionType.AIFUNCTION
        )
        if status != Status.RUNNING:
            return None
        if cur_index == self.last_index:
            return None

        buf = np.ctypeslib.as_array(self.ctypes_array, shape=(self.total_count,))

        if cur_index > self.last_index:
            chunk = buf[self.last_index : cur_index]
        else:
            chunk = np.concatenate((buf[self.last_index :], buf[:cur_index]))

        self.last_index = cur_index

        n = (len(chunk) // self.num_chans) * self.num_chans
        if n == 0:
            return None
        return chunk[:n].reshape((-1, self.num_chans))

    # ===================
    # DSP: Coherent demod using measured excitation (fast)
    # ===================


class EddyCurrentDSP:
    def __init__(self, fs, f0, block_size, lpf_fc, lpf_order):
        self.fs = fs
        self.f0 = f0
        self.block_size = block_size

        n = np.arange(block_size)
        self.osc = np.exp(-1j * 2 * np.pi * f0 * n / fs)  # e^{-jwn}

        self.sos = butter(lpf_order, lpf_fc / (fs / 2), btype="low", output="sos")
        self.zi_I_diff = sosfilt_zi(self.sos) * 0.0
        self.zi_Q_diff = sosfilt_zi(self.sos) * 0.0
        self.zi_I_abs = sosfilt_zi(self.sos) * 0.0
        self.zi_Q_abs = sosfilt_zi(self.sos) * 0.0

        self.phase_tracker = PhaseTracker(alpha=0.25)
        self.decim = max(1, int(fs / DISPLAY_RATE))

    def estimate_phase(self, exc_block):
        # Correlate at f0 (single-bin DFT-like) to estimate phase
        c = np.vdot(self.osc, exc_block)
        phi = np.angle(c)
        return self.phase_tracker.update(phi)

    def process_block(self, exc, sig_diff, sig_abs):
        phi = self.estimate_phase(exc)
        osc_phi = self.osc * np.exp(-1j * phi)

        z_diff = sig_diff * osc_phi
        z_abs = sig_abs * osc_phi

        I_diff_raw = np.real(z_diff)
        Q_diff_raw = np.imag(z_diff)
        I_abs_raw = np.real(z_abs)
        Q_abs_raw = np.imag(z_abs)

        I_diff, self.zi_I_diff = sosfilt(self.sos, I_diff_raw, zi=self.zi_I_diff)
        Q_diff, self.zi_Q_diff = sosfilt(self.sos, Q_diff_raw, zi=self.zi_Q_diff)
        I_abs, self.zi_I_abs = sosfilt(self.sos, I_abs_raw, zi=self.zi_I_abs)
        Q_abs, self.zi_Q_abs = sosfilt(self.sos, Q_abs_raw, zi=self.zi_Q_abs)

        # Decimate for Ul
        I_d = I_diff[:: self.decim]
        Q_d = Q_diff[:: self.decim]
        I_a = I_abs[:: self.decim]
        Q_a = Q_abs[:: self.decim]

        mag_d = np.hypot(I_d, Q_d)
        mag_a = np.hypot(I_a, Q_a)

        return I_d, Q_d, mag_d, I_a, Q_a, mag_a


# ===================
# Tkinter Ul
# ===================
class NDTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NDT Eddy Current (USB-231) - Tkinter Realtime")
        self.geometry("1100x900")

        ctrl = ttk.Frame(self)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        self.status_var = tk.StringVar(value="Starting...")
        ttk.Label(ctrl, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Button(ctrl, text="Quit", command=self.on_quit).pack(side=tk.RIGHT)

        fig = Figure(figsize=(10, 8), dpi=100)
        self.ax_mag = fig.add_subplot(311)
        self.ax_xy = fig.add_subplot(312)
        self.ax_raw = fig.add_subplot(313)

        # Adjust spacing between subplots
        fig.subplots_adjust(hspace=0.4)

        self.ax_mag.set_title("Magnitude (baseband)")
        self.ax_mag.set_xlabel("Samples (decimated)")
        self.ax_mag.set_ylabel("|Z|")
        self.ax_mag.grid(True, alpha=0.3)

        self.ax_xy.set_title("Impedance Plane (XY) - Differential Channel")
        self.ax_xy.set_xlabel("I")
        self.ax_xy.set_ylabel("Q")
        self.ax_xy.grid(True, alpha=0.3)
        self.ax_xy.set_aspect("equal", adjustable="box")

        self.ax_raw.set_title("Raw Sampled Data (Time Domain)")
        self.ax_raw.set_xlabel("Sample Index")
        self.ax_raw.set_ylabel("Voltage (V)")
        self.ax_raw.grid(True, alpha=0.3)

        (self.line_mag_diff,) = self.ax_mag.plot(
            [], [], color="gold", lw=1.8, label="Diff |Z|"
        )
        (self.line_mag_abs,) = self.ax_mag.plot(
            [], [], color="cyan", lw=1.8, label="Abs |Z|"
        )
        self.ax_mag.legend(loc="upper right")

        (self.line_xy,) = self.ax_xy.plot([], [], color="white", lw=1.0)

        (self.line_raw_exc,) = self.ax_raw.plot(
            [], [], color="red", lw=1.0, label="CH0 (Exc)"
        )
        (self.line_raw_diff,) = self.ax_raw.plot(
            [], [], color="green", lw=1.0, label="CH1 (Diff)"
        )
        (self.line_raw_abs,) = self.ax_raw.plot(
            [], [], color="blue", lw=1.0, label="CH2 (Abs)"
        )
        self.ax_raw.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.max_points = int(DISPLAY_RATE * TIME_WINDOW_SEC)
        self.max_xy = int(DISPLAY_RATE * XY_WINDOW_SEC)
        self.max_raw_samples = 2000  # Number of raw samples to display

        self.mag_diff_buf = np.zeros(self.max_points)
        self.mag_abs_buf = np.zeros(self.max_points)
        self.I_diff_buf = np.zeros(self.max_xy)
        self.Q_diff_buf = np.zeros(self.max_xy)

        # Raw data buffers
        self.raw_exc_buf = np.zeros(self.max_raw_samples)
        self.raw_diff_buf = np.zeros(self.max_raw_samples)
        self.raw_abs_buf = np.zeros(self.max_raw_samples)

        self.running = True
        self.plot_queue = None

    def set_plot_queue(self, q):
        self.plot_queue = q

    def on_quit(self):
        self.running = False
        self.destroy()

    def update_ui(self):
        if not self.running:
            return
        latest = None
        if self.plot_queue is not None:
            while True:
                try:
                    latest = self.plot_queue.get_nowait()
                except queue.Empty:
                    break

        if latest is not None:
            mag_d, mag_a, l_d, Q_d, raw_exc, raw_diff, raw_abs = latest
            n = len(mag_d)

            self.mag_diff_buf = np.roll(self.mag_diff_buf, -n)
            self.mag_abs_buf = np.roll(self.mag_abs_buf, -n)
            self.mag_diff_buf[-n:] = mag_d
            self.mag_abs_buf[-n:] = mag_a

            self.I_diff_buf = np.roll(self.I_diff_buf, -n)
            self.Q_diff_buf = np.roll(self.Q_diff_buf, -n)
            self.I_diff_buf[-n:] = l_d
            self.Q_diff_buf[-n:] = Q_d

            # Update raw data buffers
            n_raw = len(raw_exc)
            self.raw_exc_buf = np.roll(self.raw_exc_buf, -n_raw)
            self.raw_diff_buf = np.roll(self.raw_diff_buf, -n_raw)
            self.raw_abs_buf = np.roll(self.raw_abs_buf, -n_raw)
            self.raw_exc_buf[-n_raw:] = raw_exc
            self.raw_diff_buf[-n_raw:] = raw_diff
            self.raw_abs_buf[-n_raw:] = raw_abs

            x_mag = np.arange(self.max_points)
            self.line_mag_diff.set_data(x_mag, self.mag_diff_buf)
            self.line_mag_abs.set_data(x_mag, self.mag_abs_buf)
            self.ax_mag.set_xlim(0, self.max_points)

            y_min = min(self.mag_diff_buf.min(), self.mag_abs_buf.min())
            y_max = max(self.mag_diff_buf.max(), self.mag_abs_buf.max())
            if y_max > y_min:
                pad = 0.1 * (y_max - y_min + 1e-9)
                self.ax_mag.set_ylim(y_min - pad, y_max + pad)

            self.line_xy.set_data(self.I_diff_buf, self.Q_diff_buf)
            x_min, x_max = self.I_diff_buf.min(), self.I_diff_buf.max()
            y_min, y_max = self.Q_diff_buf.min(), self.Q_diff_buf.max()
            span = max(x_max - x_min, y_max - y_min, 1e-6)
            cx = 0.5 * (x_min + x_max)
            cy = 0.5 * (y_min + y_max)
            self.ax_xy.set_xlim(cx - 0.55 * span, cx + 0.55 * span)
            self.ax_xy.set_ylim(cy - 0.55 * span, cy + 0.55 * span)

            # Update raw data plot
            x_raw = np.arange(self.max_raw_samples)
            self.line_raw_exc.set_data(x_raw, self.raw_exc_buf)
            self.line_raw_diff.set_data(x_raw, self.raw_diff_buf)
            self.line_raw_abs.set_data(x_raw, self.raw_abs_buf)
            self.ax_raw.set_xlim(0, self.max_raw_samples)

            y_min_raw = min(
                self.raw_exc_buf.min(), self.raw_diff_buf.min(), self.raw_abs_buf.min()
            )
            y_max_raw = max(
                self.raw_exc_buf.max(), self.raw_diff_buf.max(), self.raw_abs_buf.max()
            )
            if y_max_raw > y_min_raw:
                pad_raw = 0.1 * (y_max_raw - y_min_raw + 1e-9)
                self.ax_raw.set_ylim(y_min_raw - pad_raw, y_max_raw + pad_raw)

            self.status_var.set(
                f"Running I fs={FS} (per channel) I f0={F0} I GUI={DISPLAY_RATE} pts/s"
            )

            self.canvas.draw_idle()

        self.after(UI_UPDATE_MS, self.update_ui)


# ===================
# Main glue: DAQ thread + DSP thread + Tkinter main thread
# ===================
def run():
    raw_queue = queue.Queue(maxsize=40)
    plot_queue = queue.Queue(maxsize=40)
    stop_flag = threading.Event()

    daq = MCCContinuousAI(
        board_num=BOARD_NUM,
        low_chan=LOW_CHAN,
        high_chan=HIGH_CHAN,
        fs=FS,
        ring_blocks=RING_BLOCKS,
        block_size=BLOCK_SIZE,
        ai_range=AI_RANGE,
    )
    daq.start()

    dsp = EddyCurrentDSP(
        fs=daq.fs, f0=F0, block_size=BLOCK_SIZE, lpf_fc=BASEBAND_FC, lpf_order=LP_ORDER
    )

    def daq_worker():
        try:
            while not stop_flag.is_set():
                data = daq.read_new()
                if data is None:
                    time.sleep(0.004)
                    continue
                try:
                    raw_queue.put(data, timeout=0.1)
                except queue.Full:
                    # Drop UI frames if overloaded; keep acquisition running
                    pass
        finally:
            daq.stop()

    def dsp_worker():
        acc = np.empty((0, NUM_CHANS), dtype=np.float64)
        while not stop_flag.is_set():
            try:
                chunk = raw_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            acc = np.vstack([acc, chunk])

            while acc.shape[0] >= BLOCK_SIZE:
                blk = acc[:BLOCK_SIZE, :]
                acc = acc[BLOCK_SIZE:, :]

                # Apply digital gains to each channel
                exc = blk[:, CH_EXC - LOW_CHAN] * GAIN_EXC
                diff = blk[:, CH_DIFF - LOW_CHAN] * GAIN_DIFF
                abs_ = blk[:, CH_ABS - LOW_CHAN] * GAIN_ABS

                I_d, Q_d, mag_d, I_a, Q_a, mag_a = dsp.process_block(exc, diff, abs_)

                # Send processed data along with a subset of raw data for display
                raw_display_len = min(500, len(exc))  # Send last 500 samples
                try:
                    plot_queue.put(
                        (
                            mag_d,
                            mag_a,
                            I_d,
                            Q_d,
                            exc[-raw_display_len:],
                            diff[-raw_display_len:],
                            abs_[-raw_display_len:],
                        ),
                        timeout=0.05,
                    )
                except queue.Full:
                    pass

    ti = threading.Thread(target=daq_worker, daemon=True)
    t2 = threading.Thread(target=dsp_worker, daemon=True)
    ti.start()
    t2.start()
    app = NDTApp()
    app.set_plot_queue(plot_queue)

    app.after(UI_UPDATE_MS, app.update_ui)

    try:
        app.mainloop()
    finally:
        stop_flag.set()
        time.sleep(0.2)


if __name__ == "__main__":
    run()
