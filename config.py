"""Valores predeterminados y ajustes de etiqueta guardados por usuario."""
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import tempfile

APP_NAME = "Tarjetas y Etiquetas"
APP_VERSION = "1.1.0"


@dataclass(frozen=True)
class ReaderConfig:
    mode: str = "keyboard"  # keyboard no busca USB. Otros: auto, serial, hid_text, sdk, manual
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
    width_mm: float = 25
    height_mm: float = 12
    gap_mm: float = 3
    x: int = 34  # Puntos: centra 11 caracteres de fuente 2 en 25 mm, TE200 203 dpi
    y: int = 38
    font: str = "2"  # Fuentes bitmap TSPL: 1..8
    scale_x: int = 1
    scale_y: int = 1
    dpi: int = 203
    direction: int = 0


def validate_label(label: LabelConfig) -> None:
    for value in (label.width_mm, label.height_mm, label.gap_mm):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Las medidas deben ser números finitos.")
    if label.width_mm <= 0 or label.height_mm <= 0 or label.gap_mm < 0:
        raise ValueError("Ancho y alto deben ser positivos; separación no negativa.")
    if label.font not in tuple(str(i) for i in range(1, 9)):
        raise ValueError("Elegí una fuente del 1 al 8.")
    if any(type(v) is not int or v < 0 for v in (label.x, label.y)):
        raise ValueError("Las posiciones X/Y deben ser enteros no negativos.")
    if any(type(v) is not int or not 1 <= v <= 10 for v in (label.scale_x, label.scale_y)):
        raise ValueError("Las escalas deben ser enteros entre 1 y 10.")
    if type(label.dpi) is not int or label.dpi not in (203, 300):
        raise ValueError("La resolución debe ser 203 o 300 dpi.")
    if type(label.direction) is not int or label.direction not in (0, 1):
        raise ValueError("La orientación debe ser 0 o 1.")


def label_from_fields(values: dict) -> LabelConfig:
    """Convertir los campos del diálogo; admitir coma decimal en milímetros."""
    converted = {}
    for key, value in values.items():
        if key == "font":
            converted[key] = str(value)
        elif key in {"width_mm", "height_mm", "gap_mm"}:
            converted[key] = float(str(value).replace(",", "."))
        else:
            converted[key] = int(value)
    label = LabelConfig(**converted)
    validate_label(label)
    return label


def label_settings_path() -> Path:
    base = Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else Path.home() / ".config"
    return base / "TarjetasYEtiquetas" / "label.json"


def load_label(path: Path | None = None) -> LabelConfig:
    path = path if path is not None else label_settings_path()
    if not path.exists():
        return LABEL
    try:
        label = LabelConfig(**json.loads(path.read_text(encoding="utf-8")))
        validate_label(label)
        return label
    except (ValueError, TypeError, OSError) as exc:
        raise ValueError(f"No se pudieron cargar los ajustes de etiqueta: {exc}") from exc


def save_label(label: LabelConfig, path: Path | None = None) -> None:
    validate_label(label)
    path = path if path is not None else label_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            json.dump(asdict(label), handle, indent=2)
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


READER = ReaderConfig()
LABEL = LabelConfig()
PRINTER_NAME = ""  # Nombre exacto de la cola; vacío permite elegir en la GUI
