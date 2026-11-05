"""Inicio GUI y diagnóstico sin impresión."""
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Lectura de tarjetas y etiquetas TSPL")
    parser.add_argument("--diagnose", action="store_true", help="Listar HID y COM sin abrirlos")
    parser.add_argument("--manual", action="store_true", help="Iniciar sin lector")
    parser.add_argument("--list-printers", action="store_true", help="Listar las colas Windows")
    args = parser.parse_args()
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
