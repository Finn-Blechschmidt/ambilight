"""Frame sources. The pipeline only knows the `FrameSource` interface.

`V4L2Capture` runs `v4l2-ctl --stream-to=-` as a subprocess and reads raw UYVY frames from its stdout in a
reader thread. The thread keeps only the newest frame, so a slow consumer drops old frames instead of building
up latency. If the process ends (grabber unplugged, driver error) or stalls, it is restarted after a pause.
NOT verified on the real grabber yet (the Pi was not reachable when this was written).

`FileSource` replays recorded frames with synthetic timestamps, for tests and offline runs on any machine.
"""
from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from .config import Config

log = logging.getLogger(__name__)

NTSC_FPS = 30000 / 1001


@dataclass(frozen=True)
class Frame:
    data: bytes     # raw UYVY, width * height * 2 bytes
    t: float        # seconds on the source's clock
    seq: int        # 1, 2, 3, ... gaps mean dropped frames


class FrameSource(Protocol):
    finished: bool

    def read(self, timeout: float) -> Frame | None:
        """Newest frame not returned before, or None after `timeout` seconds."""

    def now(self) -> float:
        """Current time on the clock that `Frame.t` uses."""

    def close(self) -> None: ...


class FileSource:
    """Frames from a file of concatenated raw UYVY frames, with timestamps seq / fps."""

    def __init__(self, path: str, width: int, height: int, fps: float = NTSC_FPS):
        self.frame_bytes = width * height * 2
        self.fps = fps
        self._f = open(path, "rb")
        self._seq = 0
        self.finished = False

    def read(self, timeout: float) -> Frame | None:
        data = self._f.read(self.frame_bytes)
        if len(data) < self.frame_bytes:
            self.finished = True
            return None
        self._seq += 1
        return Frame(data, self._seq / self.fps, self._seq)

    def now(self) -> float:
        return self._seq / self.fps

    def close(self) -> None:
        self._f.close()


class V4L2Capture:
    def __init__(self, cfg: Config, setup_commands: list[list[str]] | None = None,
                 stream_command: list[str] | None = None, clock: Callable[[], float] = time.monotonic):
        reg, cap = cfg.regions, cfg.capture
        self.cfg = cfg
        self.frame_bytes = reg.frame_width * reg.frame_height * 2
        self._clock = clock
        self._setup = setup_commands if setup_commands is not None else [
            ["v4l2-ctl", "-d", cap.device, "-i", str(cap.input), "-s", cap.standard],
            ["v4l2-ctl", "-d", cap.device,
             f"--set-fmt-video=width={reg.frame_width},height={reg.frame_height},pixelformat=UYVY"],
        ]
        self._stream = stream_command or ["v4l2-ctl", "-d", cap.device, f"--stream-mmap={cap.buffers}", "--stream-to=-"]
        self._cond = threading.Condition()
        self._latest: Frame | None = None
        self._seq = 0
        self._returned = 0
        self._last_publish = clock()
        self._stop = threading.Event()
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self.restarts = 0
        self.dropped = 0
        self.finished = False

    # -- reader thread ---------------------------------------------------------------------------
    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="capture", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._open():
                self._pump()
            self._kill()
            if self._stop.wait(self.cfg.capture.restart_delay_s):
                break
            self.restarts += 1
            log.warning("capture restarted (%d)", self.restarts)

    def _open(self) -> bool:
        try:
            for cmd in self._setup:
                done = subprocess.run(cmd, capture_output=True, timeout=10)
                if done.returncode != 0:
                    log.error("%s failed: %s", cmd[0], done.stderr.decode(errors="replace").strip())
                    return False
            self._proc = subprocess.Popen(self._stream, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._last_publish = self._clock()
            return True
        except (OSError, subprocess.SubprocessError) as exc:
            log.error("cannot start capture: %s", exc)
            return False

    def _pump(self) -> None:
        proc = self._proc
        while not self._stop.is_set():
            data = proc.stdout.read(self.frame_bytes)       # blocks until a full frame or the process ends
            if len(data) < self.frame_bytes:
                return
            with self._cond:
                self._seq += 1
                self._latest = Frame(data, self._clock(), self._seq)
                self._last_publish = self._latest.t
                self._cond.notify_all()

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            proc.kill()
        if proc is not None:
            proc.wait()
            if proc.stdout:
                proc.stdout.close()

    # -- consumer side ---------------------------------------------------------------------------
    def read(self, timeout: float) -> Frame | None:
        self.start()
        with self._cond:
            self._cond.wait_for(lambda: self._seq > self._returned or self._stop.is_set(), timeout)
            if self._seq > self._returned:
                frame = self._latest
                self.dropped += frame.seq - self._returned - 1
                self._returned = frame.seq
                return frame
        stalled = self._clock() - self._last_publish > self.cfg.capture.stall_timeout_s
        if stalled and self._proc is not None and self._proc.poll() is None:
            log.warning("no frame for %.1f s, killing the capture process", self.cfg.capture.stall_timeout_s)
            self._proc.kill()                                  # unblocks the reader, which then restarts it
            self._last_publish = self._clock()
        return None

    def now(self) -> float:
        return self._clock()

    def close(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        proc = self._proc
        if proc is not None and proc.poll() is None:
            proc.kill()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._kill()
