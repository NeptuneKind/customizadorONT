from __future__ import annotations

import re
from typing import Tuple

# Result: (is_valid, error_message). Empty string → considered "incomplete", valid=True so no error shown.

ValidationResult = Tuple[bool, str]

_HUAWEI_SPECIALS = set(r"""@#$%^&*()-_=+\|[]{};:'"<,.>/?`~!""")


def validate_alphanumeric(value: str) -> ValidationResult:
    if not value:
        return True, ""
    if not re.fullmatch(r"[A-Za-z0-9]+", value):
        return False, "Solo letras y números (A-Z, a-z, 0-9)."
    return True, ""


def validate_wifi_password_zte(value: str, username: str = "") -> ValidationResult:
    """Reglas ZTE: 8+ chars, debe contener dígitos, letras y símbolos, sin contexto con usuario."""
    if not value:
        return True, ""
    if len(value) < 8:
        return False, "Mínimo 8 caracteres."
    has_digit = any(c.isdigit() for c in value)
    has_alpha = any(c.isalpha() for c in value)
    has_special = any(not c.isalnum() for c in value)
    if not (has_digit and has_alpha and has_special):
        return False, "Debe incluir dígitos, letras y símbolos."
    if username:
        lowered = value.lower()
        u = username.lower()
        if u and (u in lowered or u[::-1] in lowered):
            return False, "No debe contener el usuario ni su inverso."
    return True, ""


def validate_huawei_password(value: str, username: str = "") -> ValidationResult:
    """Reglas Huawei: 8+ chars, al menos 2 tipos {dígitos, mayúsc, minúsc, símbolos}, no igual/inverso del usuario."""
    if not value:
        return True, ""
    if len(value) < 8:
        return False, "Mínimo 8 caracteres."
    has_digit = any(c.isdigit() for c in value)
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    has_special = any(c in _HUAWEI_SPECIALS for c in value)
    # Cualquier carácter que no sea alfanumérico y no esté en specials permitidos
    for c in value:
        if not c.isalnum() and c not in _HUAWEI_SPECIALS:
            return False, f"Carácter no permitido: '{c}'."
    type_count = sum((has_digit, has_upper, has_lower, has_special))
    if type_count < 2:
        return False, "Incluye al menos 2 de: dígitos, mayúsc, minúsc, símbolos."
    if username:
        if value == username or value == username[::-1]:
            return False, "No puede ser el usuario ni su inverso."
    return True, ""


def validate_ipv4(value: str) -> ValidationResult:
    if not value:
        return True, ""
    if not re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", value):
        return False, "Formato inválido. Usa X.X.X.X."
    octets = [int(x) for x in value.split(".")]
    for o in octets:
        if o < 0 or o > 255:
            return False, "Octetos entre 0 y 255."

    a, b = octets[0], octets[1]
    # 0.0.0.0/8 — "this network"
    if a == 0:
        return False, "Reservada (0.0.0.0/8)."
    # 127.0.0.0/8 — loopback
    if a == 127:
        return False, "Loopback reservada (127.0.0.0/8)."
    # 169.254.0.0/16 — link-local
    if a == 169 and b == 254:
        return False, "Link-local reservada (169.254.0.0/16)."
    # 224.0.0.0/4 — multicast (clase D)
    if 224 <= a <= 239:
        return False, "Multicast reservada (clase D)."
    # 240.0.0.0/4 — clase E reservada / broadcast
    if 240 <= a <= 255:
        return False, "Reservada (clase E)."
    return True, ""
