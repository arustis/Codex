"""Validación, diagnóstico y adaptadores de lectura. Sin dependencias de Tkinter."""
import importlib
import re
import threading
from dataclasses import dataclass

from config import ReaderConfig


class ReaderError(Exception):
    pass


def parse_card(value: str) -> tuple[str, str]:
    """Validación estricta ASCII: conserva todos los ceros y rechaza espacios."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+:[0-9]+", value):
        raise ValueError("Formato inválido. Usá números separados por un único ':', por ejemplo 01025:65874.")
    return tuple(value.split(":"))


def decode_card(value: str) -> tuple[str, str]:
    """UID decimal uint32 -> bytes little endian -> dos palabras big endian.

    Ejemplo confirmado: 2518946491 -> BB 12 24 96 -> 47890:09366.
    Una entrada Site:Card se conserva literalmente, sin convertirla a entero.
    """
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,10}", value):
        number = int(value)
        if number > 0xFFFFFFFF:
            raise ValueError("El código decimal debe estar entre 0 y 4294967295 (UID de 32 bits).")
        uid = number.to_bytes(4, byteorder="little")
        site = int.from_bytes(uid[:2], byteorder="big")
        card = int.from_bytes(uid[2:], byteorder="big")
        return f"{site:05d}", f"{card:05d}"
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        raise ValueError("El código decimal admite hasta 10 dígitos y un máximo de 4294967295.")
    return parse_card(value)


def uid_hex(value: str) -> str:
    """Hexadecimal del UID en el orden usado para Site/Card, sin separadores.

    Site:Card no contiene el UID original; en ese caso no se muestra hexadecimal.
    """
    decode_card(value)
    if ":" in value:
        return ""
    return int(value).to_bytes(4, byteorder="little").hex().upper()


class TextFrames:
    """Tramas ASCII CR/LF; descarta una trama completa si excede el límite."""
    def __init__(self, limit=128):
        self.limit = limit
        self.buffer = bytearray()
        self.overflow = False

    def feed(self, data: bytes) -> list[str]:
        result = []
        for byte in data:
            if byte in (10, 13):
                if self.overflow:
                    self.buffer.clear()
                    self.overflow = False
                    raise ReaderError("Lectura demasiado larga; volvé a acercar la tarjeta.")
                if self.buffer:
                    frame = bytes(self.buffer)
                    self.buffer.clear()
                    try:
                        result.append(frame.decode("ascii"))
                    except UnicodeDecodeError as exc:
                        raise ReaderError("El lector no envía texto ASCII; verificá su protocolo o SDK.") from exc
            elif not self.overflow:
                self.buffer.append(byte)
                if len(self.buffer) > self.limit:
                    self.buffer.clear()
                    self.overflow = True
        return result


def inventory() -> dict:
    """Enumerar no abre dispositivos ni envía comandos de inicialización."""
    result = {"hid": [], "serial": [], "errors": []}
    try:
        import hid
        for device in hid.enumerate():
            result["hid"].append({
                key: (value.decode(errors="replace") if isinstance(value, bytes) else value)
                for key, value in device.items()
            })
    except Exception as exc:
        result["errors"].append(f"No se pudo enumerar HID: {exc}")
    try:
        from serial.tools import list_ports
        result["serial"] = [dict(port=p.device, description=p.description,
                                 vendor_id=p.vid, product_id=p.pid,
                                 serial_number=p.serial_number) for p in list_ports.comports()]
    except Exception as exc:
        result["errors"].append(f"No se pudo enumerar COM: {exc}")
    return result


@dataclass(frozen=True)
class Selection:
    mode: str
    device: dict | None = None


def select_reader(config: ReaderConfig, devices: dict) -> Selection:
    if config.mode == "keyboard":
        return Selection("keyboard")
    if config.mode == "manual":
        return Selection("manual")
    if config.mode == "sdk":
        if not config.sdk_module:
            raise ReaderError("Configurá el módulo puente del SDK Dahua en config.py.")
        return Selection("sdk")
    if config.mode not in {"auto", "keyboard", "serial", "hid_text"}:
        raise ReaderError("Modo de lector desconocido en config.py.")
    if config.vendor_id is None or config.product_id is None:
        raise ReaderError("Lector sin identificar: ejecutá --diagnose y configurá VID/PID. El modo manual está disponible.")
    def matches(d):
        return (d.get("vendor_id") == config.vendor_id and
                d.get("product_id") == config.product_id and
                (config.serial_number is None or d.get("serial_number") == config.serial_number))
    ports = [d for d in devices["serial"] if matches(d) and (not config.port or d["port"] == config.port)]
    hids = [d for d in devices["hid"] if matches(d) and
            (config.interface_number is None or d.get("interface_number") == config.interface_number)]
    keyboards = [d for d in hids if d.get("usage_page") == 1 and d.get("usage") == 6]
    candidates = []
    if config.mode in {"auto", "keyboard"}:
        candidates += [Selection("keyboard", d) for d in keyboards]
    if config.mode in {"auto", "serial"}:
        candidates += [Selection("serial", d) for d in ports]
    if config.mode == "hid_text":
        candidates += [Selection("hid_text", d) for d in hids if d not in keyboards]
    if len(candidates) > 1:
        raise ReaderError("Hay varias interfaces coincidentes. Elegí modo, serie, interfaz o puerto en config.py.")
    if not candidates:
        if hids:
            raise ReaderError("HID detectado sin interfaz de teclado compatible. Se necesita confirmar protocolo/SDK; no se abrirá como texto automáticamente.")
        detail = " ".join(devices.get("errors", []))
        raise ReaderError("No se detecta el lector configurado. Revisá USB, VID/PID y el modo. " + detail)
    return candidates[0]


class Reader:
    """El callback recibe (card|status|error, texto). Nunca toca widgets."""
    def __init__(self, config: ReaderConfig, callback):
        self.config = config
        self.callback = callback
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _emit_frame(self, frame):
        decode_card(frame)
        self.callback("card", frame)

    def _run(self):
        source = None
        try:
            # El modo teclado usa eventos de la ventana: no enumera ni abre USB.
            devices = {} if self.config.mode in {"keyboard", "manual", "sdk"} else inventory()
            selected = select_reader(self.config, devices)
            mode = selected.mode
            if mode == "manual":
                self.callback("status", "Modo manual: lector desactivado.")
                return
            if mode == "keyboard":
                self.callback("keyboard", "Entrada por teclado habilitada. Escaneá con el campo de lectura enfocado.")
                return
            if mode == "serial":
                import serial
                source = serial.Serial(selected.device["port"], self.config.baudrate, timeout=0.2)
            elif mode == "hid_text":
                import hid
                source = hid.device()
                path = selected.device["path"]
                source.open_path(path.encode() if isinstance(path, str) else path)
            else:
                module = importlib.import_module(self.config.sdk_module)
                source = module.open_reader(self.config)
            self.callback("status", f"Lector abierto ({mode}); esperando tarjeta.")
            frames = TextFrames(self.config.max_frame_length)
            while not self.stop_event.is_set():
                try:
                    if mode == "sdk":
                        frame = source.read_card(timeout_ms=200)
                        if frame is not None:
                            self._emit_frame(frame)
                        continue
                    if mode == "serial":
                        chunk = source.read(64)
                    else:
                        chunk = bytes(source.read(self.config.hid_report_size, 200))
                        # Solo para protocolos previamente confirmados como ASCII por reporte.
                        chunk = chunk[self.config.hid_payload_offset:].rstrip(b"\x00")
                    for frame in frames.feed(chunk):
                        try:
                            self._emit_frame(frame)
                        except ValueError as exc:
                            self.callback("invalid", str(exc))
                except (ValueError, ReaderError) as exc:
                    self.callback("invalid", str(exc))
        except Exception as exc:
            self.callback("error", f"No se pudo usar el lector: {exc}")
        finally:
            if source is not None:
                try:
                    source.close()
                except Exception:
                    pass
