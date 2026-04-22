from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Optional

from src.backend.core.monitoring import ping_once_windows
from config.logging import get_logger

log = get_logger("TRANSPORT")

# ── Telnet control bytes ─────────────────────────────────────────────
_IAC  = 255
_DO   = 253
_DONT = 254
_WILL = 251
_WONT = 252
_SB   = 250
_SE   = 240


@dataclass
class HuaweiTelnetCredentials:
    username_1: str
    password_1: str
    username_2: str
    password_2: str


class HuaweiFullLockedTransport:
    """
    Raw TCP/Telnet transport for Huawei ONT full-locked unlock flow.

    Responsibilities:
      - Open/close a TCP connection to the ONT Telnet port
      - Authenticate with dual-credential fallback
      - Send shell commands and capture responses
      - Issue TFTP load commands and wait for ONT confirmation
      - Trigger reboot and wait for device recovery

    Does NOT know about steps, orchestration, Selenium, or business logic.
    """

    def __init__(
        self,
        host: str,
        port: int = 23,
        timeout_s: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self._sock: Optional[socket.socket] = None
        self._buf = b""

    # =================================================================
    # Connection
    # =================================================================

    def connect(self) -> None:
        """Establish TCP connection to the ONT Telnet port."""
        log.debug("Connecting to %s:%d", self.host, self.port)
        self._sock = socket.create_connection(
            (self.host, self.port), timeout=self.timeout_s
        )
        self._buf = b""
        log.debug("Connected to %s:%d", self.host, self.port)

    def close(self) -> None:
        """Close connection (idempotent)."""
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
            log.debug("Connection closed")

    # =================================================================
    # Authentication
    # =================================================================

    def login(self, credentials: HuaweiTelnetCredentials) -> None:
        """
        Dual-credential login. Tries pair 1 first; falls back to pair 2.
        Raises RuntimeError if both pairs fail.
        """
        try:
            self._do_login(credentials.username_1, credentials.password_1)
            log.debug("Logged in with credential pair 1 (%s)", credentials.username_1)
            return
        except RuntimeError as exc:
            log.debug("Credential pair 1 failed: %s — trying pair 2", exc)

        self._do_login(credentials.username_2, credentials.password_2)
        log.debug("Logged in with credential pair 2 (%s)", credentials.username_2)

    def _do_login(self, username: str, password: str) -> None:
        """Single login attempt. Raises RuntimeError on auth failure."""
        self._read_until("login:", timeout_s=10.0)
        self._write(username + "\n")
        self._read_until("Password:", timeout_s=5.0)
        self._write(password + "\n")
        response = self._read_until_any(
            ["#", "$", ">", "incorrect", "denied", "failed"],
            timeout_s=5.0,
        )
        lower = response.lower()
        if "incorrect" in lower or "denied" in lower or "failed" in lower:
            raise RuntimeError(
                f"Authentication failed for user '{username}'"
            )

    # =================================================================
    # Commands
    # =================================================================

    def send_command(
        self,
        command: str,
        expect: Optional[str] = None,
        wait_s: float = 0.3,
    ) -> str:
        """
        Send a shell command.
        If `expect` is provided, block until that string appears in the response.
        Otherwise, wait `wait_s` seconds and return whatever was received.
        """
        log.debug("send_command: %r", command)
        self._write(command + "\n")
        if expect:
            return self._read_until(expect, timeout_s=wait_s + 10.0)
        time.sleep(wait_s)
        return self._read_available()

    # =================================================================
    # TFTP
    # =================================================================

    def load_pack_by_tftp(
        self,
        server_ip: str,
        remote_file: str,
        expect: str,
    ) -> str:
        """
        Instruct the ONT to pull `remote_file` from a TFTP server at
        `server_ip`.  Blocks until `expect` string appears in the response
        (up to 120 s — firmware transfers are slow).

        Returns the full response text.
        """
        cmd = f"load_pack_by_tftp {server_ip} {remote_file}"
        log.debug("TFTP: %s (expect=%r)", cmd, expect)
        self._write(cmd + "\n")
        return self._read_until(expect, timeout_s=120.0)

    # =================================================================
    # Reset / reboot
    # =================================================================

    def send_reset(self) -> None:
        """
        Send reboot command. The socket may drop immediately — that is
        expected, so socket errors are silently swallowed.
        """
        log.debug("Sending reset")
        try:
            self._write("send reset\n")
        except Exception:
            pass

    def wait_for_reboot(
        self,
        down_timeout_s: float = 15.0,
        up_timeout_s: float = 90.0,
    ) -> None:
        """
        Wait for the device to go offline then come back online.

        Phase DOWN: poll ping until it stops responding (max `down_timeout_s`).
        Phase UP:   poll ping until it responds again (max `up_timeout_s`).
        Raises TimeoutError if the device does not recover in time.
        """
        log.debug("Waiting for reboot (down≤%ss, up≤%ss)", down_timeout_s, up_timeout_s)

        # Phase DOWN — wait until device stops responding
        start = time.time()
        while time.time() - start < down_timeout_s:
            if not ping_once_windows(self.host):
                log.debug("Device went offline (%.1fs)", time.time() - start)
                break
            time.sleep(1.0)

        # Phase UP — wait until device responds again
        start = time.time()
        while time.time() - start < up_timeout_s:
            if ping_once_windows(self.host):
                log.debug("Device back online (%.1fs)", time.time() - start)
                return
            time.sleep(2.0)

        raise TimeoutError(
            f"Device at {self.host} did not come back within {up_timeout_s}s"
        )

    # =================================================================
    # Internal I/O helpers
    # =================================================================

    def _write(self, text: str) -> None:
        if self._sock is None:
            raise RuntimeError("Transport not connected — call connect() first")
        self._sock.sendall(text.encode("ascii", errors="replace"))

    def _read_available(self, timeout_s: float = 0.3) -> str:
        """Read whatever is in the socket buffer right now."""
        if self._sock is None:
            raise RuntimeError("Transport not connected")
        self._sock.settimeout(timeout_s)
        try:
            chunk = self._sock.recv(4096)
            self._buf += chunk
        except socket.timeout:
            pass
        text, self._buf = _strip_iac(self._buf)
        return text.decode("ascii", errors="replace")

    def _read_until(self, marker: str, timeout_s: float = 10.0) -> str:
        return self._read_until_any([marker], timeout_s=timeout_s)

    def _read_until_any(
        self, markers: list[str], timeout_s: float = 10.0
    ) -> str:
        """
        Read from socket until one of `markers` appears in accumulated text.
        Returns the full accumulated text (including the marker).
        Raises TimeoutError if no marker appears within `timeout_s`.
        """
        if self._sock is None:
            raise RuntimeError("Transport not connected")

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            remaining = max(0.01, deadline - time.time())
            self._sock.settimeout(min(remaining, 0.5))
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                self._buf += chunk
            except socket.timeout:
                pass

            self._buf, replies = _process_iac(self._buf)
            if replies and self._sock:
                try:
                    self._sock.sendall(replies)
                except Exception:
                    pass

            text = self._buf.decode("ascii", errors="replace")
            for marker in markers:
                if marker in text:
                    self._buf = b""
                    return text

        raise TimeoutError(
            f"Expected one of {markers!r} not seen within {timeout_s}s "
            f"(host={self.host})"
        )


# =====================================================================
# Telnet IAC negotiation helpers (module-level, no state)
# =====================================================================

def _strip_iac(buf: bytes) -> tuple[bytes, bytes]:
    """Remove IAC sequences from buffer without generating replies."""
    cleaned, _ = _process_iac(buf)
    return cleaned, b""


def _process_iac(buf: bytes) -> tuple[bytes, bytes]:
    """
    Walk `buf`, strip Telnet IAC sequences, and produce minimal refusal
    replies (WONT for DO, DONT for WILL).

    Returns (clean_bytes, reply_bytes).
    """
    output = bytearray()
    replies = bytearray()
    i = 0
    while i < len(buf):
        b = buf[i]
        if b != _IAC:
            output.append(b)
            i += 1
            continue

        # Need at least 2 bytes for a complete IAC command
        if i + 1 >= len(buf):
            output.extend(buf[i:])  # Keep incomplete IAC for next read
            break

        cmd = buf[i + 1]

        if cmd in (_DO, _DONT):
            if i + 2 < len(buf):
                opt = buf[i + 2]
                replies.extend([_IAC, _WONT, opt])  # Refuse all options
                i += 3
            else:
                output.extend(buf[i:])
                break

        elif cmd in (_WILL, _WONT):
            if i + 2 < len(buf):
                opt = buf[i + 2]
                replies.extend([_IAC, _DONT, opt])  # Refuse all options
                i += 3
            else:
                output.extend(buf[i:])
                break

        elif cmd == _SB:
            # Subnegotiation — skip until IAC SE
            end = buf.find(bytes([_IAC, _SE]), i + 2)
            if end != -1:
                i = end + 2
            else:
                output.extend(buf[i:])  # Keep incomplete SB
                break

        elif cmd == _IAC:
            output.append(_IAC)  # Escaped IAC → literal 255
            i += 2

        else:
            i += 2  # Unknown 2-byte sequence — skip

    return bytes(output), bytes(replies)
