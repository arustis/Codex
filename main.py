"""Inicio GUI y diagnóstico sin impresión."""
import argparse
import json
from config import APP_NAME


def self_test():
    """Comprobar el bundle instalado sin lector ni impresion fisica."""
    import tkinter as tk
    import win32print  # noqa: F401 - comprobar que PyInstaller incluye la extension
    import hid  # noqa: F401
    import serial.tools.list_ports  # noqa: F401
    from gui import Application

    root = tk.Tk()
    root.withdraw()
    app = Application(root, manual=True)
    app.raw.set("2518946491")
    root.update()
    if (app.hexadecimal.get(), app.preview.get()) != ("BB122496", "47890:09366"):
        raise RuntimeError("La conversion no coincide en el ejecutable instalado.")
    root.deiconify()
    root.update()
    app.configure_label()
    root.update()
    for window in root.winfo_children():
        if isinstance(window, tk.Toplevel):
            window.destroy()
    app.close()


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME}: lectura de tarjetas e impresión de etiquetas TSPL")
    parser.add_argument("--diagnose", action="store_true", help="Listar HID y COM sin abrirlos")
    parser.add_argument("--manual", action="store_true", help="Iniciar sin lector")
    parser.add_argument("--list-printers", action="store_true", help="Listar las colas Windows")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.diagnose:
        from reader import inventory
        print(json.dumps(inventory(), ensure_ascii=False, indent=2))
        return
    if args.list_printers:
        from printer import PrinterError, list_printers
        try:
            print("\n".join(list_printers()) or "No se detectan impresoras.")
        except PrinterError as exc:
            parser.exit(1, f"{exc}\n")
        return
    import tkinter as tk
    from gui import Application
    root = tk.Tk()
    Application(root, manual=args.manual)
    root.mainloop()


if __name__ == "__main__":
    main()
