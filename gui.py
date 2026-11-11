"""Interfaz Tkinter. Trabajos de E/S en hilos y resultados por Queue."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from config import PRINTER_NAME, READER
from printer import list_printers, print_label
from reader import Reader, decode_card


class Application(ttk.Frame):
    def __init__(self, root, reader_config=READER, manual=False):
        super().__init__(root, padding=18)
        self.root = root
        self.reader_config = reader_config
        self.events = queue.Queue()
        self.reader = None
        self.busy = False
        self.closed = False
        self.raw = tk.StringVar()
        self.site = tk.StringVar()
        self.card = tk.StringVar()
        self.preview = tk.StringVar()
        self.reader_status = tk.StringVar(value="Preparando entrada…")
        self.printer_status = tk.StringVar(value="Consultando impresoras…")
        self.message = tk.StringVar(value="Acercá una tarjeta o ingresá un valor de prueba.")
        self.printer_name = tk.StringVar(value=PRINTER_NAME)
        self.manual = tk.BooleanVar(value=manual or reader_config.mode == "manual")
        self.grid(sticky="nsew")
        self.columnconfigure(1, weight=1)
        root.title("Tarjetas · Dahua ASM100 / TSC TE200")
        root.minsize(650, 430)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        ttk.Label(self, text="Entrada de tarjetas").grid(row=0, column=0, sticky="w")
        ttk.Label(self, textvariable=self.reader_status, wraplength=460).grid(row=0, column=1, sticky="w", pady=8)
        ttk.Label(self, text="Lectura / valor manual").grid(row=2, column=0, sticky="w", pady=10)
        self.input = ttk.Entry(self, textvariable=self.raw)
        self.input.grid(row=2, column=1, sticky="ew")
        self.input.bind("<Return>", self.accept_input)
        self.input.bind("<KP_Enter>", self.accept_input)
        self.input.bind("<Tab>", self.accept_input)
        for row, label, variable in ((3, "Site Code", self.site), (4, "Card Code", self.card),
                                      (5, "Vista previa", self.preview)):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=6)
            ttk.Entry(self, textvariable=variable, state="readonly").grid(row=row, column=1, sticky="ew")
        ttk.Label(self, text="Impresora Windows").grid(row=6, column=0, sticky="w", pady=10)
        self.printers = ttk.Combobox(self, textvariable=self.printer_name, state="readonly")
        self.printers.grid(row=6, column=1, sticky="ew")
        actions = ttk.Frame(self)
        ttk.Label(self, text="Estado impresora").grid(row=7, column=0, sticky="w")
        ttk.Label(self, textvariable=self.printer_status, wraplength=460).grid(row=7, column=1, sticky="w")
        actions.grid(row=8, column=0, columnspan=2, sticky="w", pady=10)
        self.print_button = ttk.Button(actions, text="Imprimir", command=self.print_current)
        self.print_button.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Limpiar", command=self.clear).pack(side="left", padx=8)
        ttk.Button(actions, text="Actualizar impresoras", command=self.refresh_printers).pack(side="left", padx=8)
        ttk.Button(actions, text="Preparar lectura", command=self.prepare_input).pack(side="left", padx=8)
        ttk.Label(self, textvariable=self.message, wraplength=600).grid(row=9, column=0, columnspan=2, sticky="w", pady=10)
        ttk.Label(self, text="Mantené esta ventana activa y el campo de lectura enfocado. También podés escribir o pegar un valor.",
                  wraplength=600).grid(row=10, column=0, columnspan=2, sticky="w")
        self.raw.trace_add("write", self.update_preview)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.restart_reader()
        self.refresh_printers()
        self.input.focus_set()
        self.poll_id = root.after(100, self.poll)

    def update_preview(self, *_):
        try:
            site, card = decode_card(self.raw.get())
        except ValueError as exc:
            site = card = ""
            if not self.busy and self.raw.get():
                self.message.set(str(exc))
        self.site.set(site)
        self.card.set(card)
        self.preview.set(f"{site}:{card}" if site else "")
        if not self.busy:
            if site:
                self.message.set("Dato válido. Revisá la vista previa y presioná Imprimir.")

    def prepare_input(self):
        self.input.focus_set()
        self.input.selection_range(0, tk.END)

    def accept_input(self, event=None):
        try:
            decode_card(self.raw.get())
            self.message.set("Dato válido. Revisá la vista previa y presioná Imprimir.")
            self.input.selection_range(0, tk.END)
        except ValueError as exc:
            self.message.set(str(exc))
        return "break"

    def clear(self):
        self.raw.set("")
        self.message.set("Listo para otra tarjeta.")
        self.input.focus_set()

    def restart_reader(self):
        if self.reader:
            self.reader.stop()
            if self.reader.thread and self.reader.thread.is_alive():
                self.reader_status.set("Cerrando conexión anterior…")
                self.root.after(100, self.restart_reader)
                return
        # Los eventos pendientes del lector anterior se ignoran por identidad.
        self.reader = None
        if self.manual.get():
            self.reader_status.set("Modo manual: no se requiere lector.")
        else:
            reader = Reader(self.reader_config, lambda kind, value: self.events.put(("reader", reader, kind, value)))
            self.reader = reader
            self.reader_status.set("Preparando entrada…")
            reader.start()
        self.input.focus_set()

    def refresh_printers(self):
        def work():
            try:
                self.events.put(("printers", list_printers()))
            except Exception as exc:
                self.events.put(("printer_status", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def print_current(self):
        if self.busy:
            return
        text = self.raw.get()
        try:
            site, card = decode_card(text)
        except ValueError as exc:
            self.message.set(str(exc))
            return
        text = f"{site}:{card}"
        name = self.printer_name.get()
        if not name:
            self.printer_status.set("Elegí una impresora para imprimir. Podés seguir probando la lectura sin impresora.")
            return
        self.busy = True
        self.print_button.configure(state="disabled")
        self.message.set("Enviando etiqueta a Windows…")
        def work():
            try:
                job = print_label(text, name)
                self.events.put(("printed", f"Windows aceptó el trabajo {job}: {text}. Verificá la salida en la impresora."))
            except Exception as exc:
                self.events.put(("printed", str(exc)))
        threading.Thread(target=work, daemon=True).start()
        self.input.focus_set()
        self.input.selection_range(0, tk.END)

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "reader":
                    _, reader, kind, value = event
                    if reader is not self.reader:
                        continue
                    if kind == "card":
                        self.raw.set(value)
                        self.accept_input()
                    elif kind == "invalid":
                        self.raw.set("")
                        self.message.set(value)
                    else:
                        self.reader_status.set(value)
                        if kind == "error":
                            self.message.set(value)
                        if kind == "keyboard":
                            self.input.focus_set()
                elif event[0] == "printers":
                    names = event[1]
                    self.printers["values"] = names
                    if self.printer_name.get() not in names:
                        self.printer_name.set("")
                        tsc = [n for n in names if "TE200" in n.upper()]
                        if len(tsc) == 1:
                            self.printer_name.set(tsc[0])
                    if not names:
                        self.printer_status.set("Sin impresoras instaladas. Podés seguir probando la lectura.")
                    else:
                        self.printer_status.set("Elegí la cola TSC TE200 cuando quieras imprimir.")
                elif event[0] == "printer_status":
                    self.printer_status.set(event[1])
                elif event[0] == "printed":
                    self.busy = False
                    self.print_button.configure(state="normal")
                    self.message.set(event[1])
                else:
                    self.message.set(event[1])
        except queue.Empty:
            pass
        self.poll_id = self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            self.message.set("Esperá a que termine el envío a Windows antes de cerrar.")
            return
        self.closed = True
        if self.reader:
            self.reader.stop()
        self.root.after_cancel(self.poll_id)
        self.root.destroy()
