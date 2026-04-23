from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Optional

from src.backend.core.monitoring import ping_once_windows
from config.logging import get_logger

log = get_logger("TRANSPORT")

# ── Matriz de credenciales por paso (dual login: pair_1 primario → pair_2 fallback) ──
#
# Paso esperado   | pair 1           | pair 2           | Si entra con pair 1    | Si entra con pair 2
# ----------------+------------------+------------------+------------------------+-------------------------
# Step 1 / Step 2 | root/admin_123   | root/adminHW     | estado normal 1-2      | Step 2 ya aplicado o parcial → reejecutar defensivamente
# Step 3          | root/admin       | root/admin_123   | estado normal post-2   | (raro) equipo regresó a estado previo
# Step 4          | root/adminHW     | root/admin       | estado normal post-3   | (raro) Step 3 no aplicó fully
#
# Usar `infer_step_from_credentials(transport)` para leer esta matriz de forma programática.

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
        self._credentials_used = None  # (username, password, pair_number)
        self._last_response: Optional[str] = None  # last send_command response

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
        Tracks which credentials were used in self._credentials_used.
        """
        try:
            self._do_login(credentials.username_1, credentials.password_1)
            self._credentials_used = (credentials.username_1, credentials.password_1, 1)
            log.debug("Logged in with credential pair 1 (%s)", credentials.username_1)
            return
        except RuntimeError as exc:
            log.debug("Credential pair 1 failed: %s — trying pair 2", exc)

        self._do_login(credentials.username_2, credentials.password_2)
        self._credentials_used = (credentials.username_2, credentials.password_2, 2)
        log.debug("Logged in with credential pair 2 (%s)", credentials.username_2)

    def _do_login(self, username: str, password: str) -> None:
        """Single login attempt. Raises RuntimeError on auth failure."""
        self._read_until_any(["login:", "Login:"], timeout_s=10.0)
        self._write(username + "\n")
        self._read_until_any(["Password:", "password:"], timeout_s=5.0)
        self._write(password + "\n")
        response = self._read_until_any(
            ["#", "$", ">", "WAP", "incorrect", "denied", "failed", "wrong"],
            timeout_s=10.0,
        )
        lower = response.lower()
        if any(k in lower for k in ("incorrect", "denied", "failed", "wrong")):
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
            response = self._read_until(expect, timeout_s=wait_s + 10.0)
        else:
            time.sleep(wait_s)
            response = self._read_available()
        self._last_response = response
        return response

    # =================================================================
    # TFTP
    # =================================================================

    def load_pack_by_tftp(
        self,
        server_ip: str,
        remote_file: str,
        expect: str,
        timeout_s: float = 120.0,
        progress_interval_s: float = 10.0,
    ) -> str:
        """
        Instruct the ONT to pull `remote_file` from a TFTP server at
        `server_ip`.  Blocks until `expect` string appears in the response.

        Prints progress every `progress_interval_s` seconds.
        Raises RuntimeError immediately if the ONT reports an error.
        Returns the full response text.
        """
        _TFTP_ERROR_MARKERS = [
            "failed", "timed out", "refused", "no such file", "cannot", "unreachable",
            "error::", "not existed", "not exist", "invalid command",
        ]
        cmd = f"load pack by tftp svrip {server_ip} remotefile {remote_file}"
        log.debug("TFTP: %s (expect=%r, timeout=%ss)", cmd, expect, timeout_s)
        self._write(cmd + "\n")

        deadline = time.time() + timeout_s
        last_progress = time.time()

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

            if expect in text:
                self._buf = b""
                self._last_response = text
                return text

            lower = text.lower()
            for err in _TFTP_ERROR_MARKERS:
                if err in lower:
                    self._buf = b""
                    self._last_response = text
                    raise RuntimeError(
                        f"TFTP falló — ONT respondió: {repr(text.strip()[:300])}"
                    )

            now = time.time()
            if now - last_progress >= progress_interval_s:
                elapsed = now - (deadline - timeout_s)
                partial = text.strip()[-200:] if text.strip() else "(sin respuesta aún)"
                print(f"[TRANSPORT] TFTP {elapsed:.0f}s/{timeout_s:.0f}s — ONT: {repr(partial)}")
                log.debug("TFTP progress %.0fs: %r", elapsed, partial)
                last_progress = now

        last_text = self._buf.decode("ascii", errors="replace")
        self._last_response = last_text
        raise TimeoutError(
            f"TFTP: '{expect}' no recibido en {timeout_s}s (host={self.host})\n"
            f"Último texto recibido: {repr(last_text.strip()[:300])}"
        )

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
                idx = text.find(marker)
                if idx != -1:
                    end = idx + len(marker)
                    self._buf = self._buf[end:]
                    return text[:end]

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


# =====================================================================
# State inference from successful Telnet credentials
# =====================================================================

def infer_step_from_credentials(transport: "HuaweiFullLockedTransport") -> dict:
    """
    Mapea la credencial Telnet que funcionó al paso más probable en el que
    está el ONT. Ver matriz arriba del módulo.

    Retorna dict con:
      - likely_step: int (1..4) o None si no hay info
      - confidence: 'high' | 'medium' | 'low'
      - note: explicación legible
      - credentials_used: (user, pass, pair_number) o None
    """
    used = transport._credentials_used
    if used is None:
        return {
            "likely_step": None,
            "confidence": "low",
            "note": "Aún no se hizo login — sin información de estado",
            "credentials_used": None,
        }

    user, password, pair = used
    key = (user, password)

    if key == ("root", "admin_123"):
        note = "pair 1 de Step 1/2 — equipo en estado normal pre/intra steps 1-2"
        likely, conf = 1, "high"
    elif key == ("root", "adminHW"):
        note = (
            "pair 2 de Step 1/2 (fallback) — Step 2 posiblemente ya aplicado o parcial; "
            "reejecutar Step 2 de forma defensiva"
        )
        likely, conf = 2, "medium"
    elif key == ("root", "admin"):
        note = "pair 1 de Step 3 — equipo en estado normal post-Step 2"
        likely, conf = 3, "high"
    else:
        note = f"credencial desconocida {user!r} — no se puede inferir paso"
        likely, conf = None, "low"

    return {
        "likely_step": likely,
        "confidence": conf,
        "note": note,
        "credentials_used": used,
    }
