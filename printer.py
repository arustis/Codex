"""TSPL puro y envío RAW a la cola de Windows, sin rasterizar ni reformatear."""
import sys

from config import LABEL, LabelConfig, validate_label
from reader import parse_card


class PrinterError(Exception):
    pass


def validate_layout(text: str, label: LabelConfig) -> None:
    parse_card(text)
    validate_label(label)
    # Dimensiones de las fuentes bitmap TSPL2 en puntos.
    fonts = {"1": (8, 12), "2": (12, 20), "3": (16, 24), "4": (24, 32),
             "5": (32, 48), "6": (14, 19), "7": (21, 27), "8": (14, 25)}
    char_width, char_height = fonts[label.font]
    dots_per_mm = 8 if label.dpi == 203 else 12
    if (label.x + len(text) * char_width * label.scale_x > int(label.width_mm * dots_per_mm)
            or label.y + char_height * label.scale_y > int(label.height_mm * dots_per_mm)):
        raise ValueError("El texto no cabe en la etiqueta. Reducí fuente/escala o X/Y y revisá ancho/alto en Configurar etiqueta.")


def build_tspl(text: str, label: LabelConfig = LABEL) -> bytes:
    validate_layout(text, label)  # También impide inyectar comandos TSPL.
    return (f"SIZE {label.width_mm:g} mm,{label.height_mm:g} mm\r\n"
            f"GAP {label.gap_mm:g} mm,0 mm\r\n"
            f"DIRECTION {label.direction},0\r\nREFERENCE 0,0\r\nSHIFT 0,0\r\nOFFSET 0 mm\r\nCLS\r\n"
            f'TEXT {label.x},{label.y},"{label.font}",0,{label.scale_x},{label.scale_y},"{text}"\r\n'
            "PRINT 1,1\r\n").encode("ascii")


def _backend():
    if sys.platform != "win32":
        raise PrinterError("La impresión por cola requiere Windows. Podés probar la vista previa sin impresora.")
    try:
        import win32print
        return win32print
    except ImportError as exc:
        raise PrinterError("Falta pywin32. Instalá las dependencias de requirements.txt.") from exc


def list_printers(backend=None) -> list[str]:
    api = backend if backend is not None else _backend()
    try:
        return sorted(p[2] for p in api.EnumPrinters(api.PRINTER_ENUM_LOCAL | api.PRINTER_ENUM_CONNECTIONS))
    except Exception as exc:
        raise PrinterError(f"No se pudieron consultar las impresoras: {exc}") from exc


def print_label(text: str, printer_name: str, label: LabelConfig = LABEL, backend=None) -> int:
    data = build_tspl(text, label)
    api = backend if backend is not None else _backend()
    if not printer_name or printer_name not in list_printers(api):
        raise PrinterError("No se detecta la impresora seleccionada. Instalá el driver y actualizá las colas.")
    handle = None
    active = False
    try:
        handle = api.OpenPrinter(printer_name)
        info = api.GetPrinter(handle, 2)
        # Estado conocido; algunas colas USB no informan desconexiones en tiempo real.
        if info.get("Status", 0) & (0x1 | 0x2 | 0x8 | 0x10 | 0x20 | 0x40 | 0x80 | 0x800 | 0x1000 | 0x100000):
            raise PrinterError("La cola informa un problema: revisá conexión, pausa, papel, tapa y ribbon.")
        job = api.StartDocPrinter(handle, 1, ("Etiqueta de tarjeta", None, "RAW"))
        active = True
        api.StartPagePrinter(handle)
        offset = 0
        while offset < len(data):
            written = api.WritePrinter(handle, data[offset:])
            if not isinstance(written, int) or not 0 < written <= len(data) - offset:
                raise PrinterError("Windows no aceptó todos los bytes de la etiqueta.")
            offset += written
        api.EndPagePrinter(handle)
        api.EndDocPrinter(handle)
        active = False
        return job
    except Exception as exc:
        if handle is not None and active:
            try:
                api.AbortPrinter(handle)
            except Exception:
                pass
        if isinstance(exc, PrinterError):
            raise
        raise PrinterError(f"Falló el envío de la etiqueta: {exc}. Revisá la cola antes de reintentar.") from exc
    finally:
        if handle is not None:
            try:
                api.ClosePrinter(handle)
            except Exception:
                pass
