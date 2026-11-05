"""Configuración local. Reiniciar la aplicación después de editarla."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReaderConfig:
    mode: str = "auto"  # auto, keyboard, serial, hid_text, sdk, manual
    vendor_id: int | None = None  # Obtener con python main.py --diagnose
    product_id: int | None = None
    serial_number: str | None = None
    interface_number: int | None = None
    port: str = ""  # p. ej. COM3, solo si Windows expone un puerto serie
    baudrate: int = 9600  # Confirmar con documentación del dispositivo
    hid_report_size: int = 64
    hid_payload_offset: int = 0  # Incluye report ID si corresponde
    sdk_module: str = ""  # Módulo puente propio; contrato documentado en README
    max_frame_length: int = 128


@dataclass(frozen=True)
class LabelConfig:
    width_mm: float = 50
    height_mm: float = 30
    gap_mm: float = 2
    x: int = 30  # Puntos, TE200: 203 dpi
    y: int = 30
    font: str = "3"  # Fuentes bitmap TSPL: 1..8
    scale_x: int = 1
    scale_y: int = 1


READER = ReaderConfig()
LABEL = LabelConfig()
PRINTER_NAME = ""  # Nombre exacto de la cola; vacío permite elegir en la GUI
