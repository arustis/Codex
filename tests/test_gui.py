"""Lógica de interfaz con variables Tcl reales; no requiere pantalla ni USB."""
import queue
import tkinter as tk
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gui import Application
from config import LABEL


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.tcl = tk.Tcl()
        self.app = SimpleNamespace(
            raw=tk.StringVar(self.tcl), hexadecimal=tk.StringVar(self.tcl), site=tk.StringVar(self.tcl),
            card=tk.StringVar(self.tcl), preview=tk.StringVar(self.tcl),
            message=tk.StringVar(self.tcl), printer_status=tk.StringVar(self.tcl),
            printer_name=tk.StringVar(self.tcl), label=LABEL, busy=False, closed=False,
            input=Mock(), print_button=Mock(), events=queue.Queue(),
            root=Mock(), poll=Mock(), printers={}, reader=None)
        self.app.raw.trace_add("write", lambda *_: Application.update_preview(self.app))

    def test_scan_updates_fields_without_enter_or_printer(self):
        self.app.raw.set("2518946491")
        self.assertEqual(self.app.site.get(), "47890")
        self.assertEqual(self.app.hexadecimal.get(), "BB122496")
        self.assertEqual(self.app.card.get(), "09366")
        self.assertEqual(self.app.preview.get(), "47890:09366")
        self.assertIn("Dato válido", self.app.message.get())

    def test_new_scan_replaces_previous_after_enter(self):
        self.app.raw.set("2518946491")
        Application.accept_input(self.app)
        self.app.input.selection_range.assert_called_with(0, tk.END)
        self.app.raw.set("2519062667")
        self.assertEqual(self.app.preview.get(), "35800:09622")
        self.assertEqual(self.app.hexadecimal.get(), "8BD82596")

    def test_invalid_scan_clears_previous_preview(self):
        self.app.raw.set("2518946491")
        self.app.raw.set("malformed")
        self.assertEqual(self.app.site.get(), "")
        self.assertEqual(self.app.card.get(), "")
        self.assertEqual(self.app.preview.get(), "")
        self.assertEqual(self.app.hexadecimal.get(), "")
        self.assertIn("Formato inválido", self.app.message.get())

    def test_clear_removes_hexadecimal_and_codes(self):
        self.app.raw.set("2518946491")
        Application.clear(self.app)
        for field in (self.app.raw, self.app.hexadecimal, self.app.site, self.app.card, self.app.preview):
            self.assertEqual(field.get(), "")

    def test_formatted_value_does_not_reuse_previous_uid_hex(self):
        self.app.raw.set("2518946491")
        self.app.raw.set("01025:65874")
        self.assertEqual(self.app.hexadecimal.get(), "")
        self.assertEqual(self.app.preview.get(), "01025:65874")

    def test_missing_printer_does_not_hide_valid_reading(self):
        self.app.raw.set("2518946491")
        self.app.events.put(("printers", []))
        Application.poll(self.app)
        self.assertIn("Sin impresoras", self.app.printer_status.get())
        self.assertIn("Dato válido", self.app.message.get())
        self.assertEqual(self.app.preview.get(), "47890:09366")
        with patch("gui.print_label") as print_label:
            Application.print_current(self.app)
        print_label.assert_not_called()
        self.assertFalse(self.app.busy)

    def test_print_uses_converted_text_instead_of_decimal_uid(self):
        self.app.raw.set("2518946491")
        self.app.printer_name.set("TSC TE200")
        with patch("gui.threading.Thread") as thread, patch("gui.print_label", return_value=12) as send:
            thread.side_effect = lambda **kwargs: SimpleNamespace(start=kwargs["target"])
            Application.print_current(self.app)
        send.assert_called_once_with("47890:09366", "TSC TE200", LABEL)
        self.assertIn("47890:09366", self.app.events.get_nowait()[1])

    def test_oversized_text_is_rejected_in_gui_without_starting_job(self):
        self.app.raw.set("2518946491")
        self.app.printer_name.set("TSC TE200")
        self.app.label = replace(LABEL, width_mm=10)
        with patch("gui.print_label") as send, patch("gui.threading.Thread") as thread:
            Application.print_current(self.app)
        send.assert_not_called()
        thread.assert_not_called()
        self.assertFalse(self.app.busy)
        self.assertIn("no cabe", self.app.message.get())

    def test_selected_stock_is_passed_to_spooler(self):
        self.app.raw.set("2518946491")
        self.app.printer_name.set("TSC TE200")
        self.app.label = replace(LABEL, width_mm=30, height_mm=15, gap_mm=3, x=16, y=16, font="2")
        with patch("gui.threading.Thread") as thread, patch("gui.print_label", return_value=12) as send:
            thread.side_effect = lambda **kwargs: SimpleNamespace(start=kwargs["target"])
            Application.print_current(self.app)
        send.assert_called_once_with("47890:09366", "TSC TE200", self.app.label)


if __name__ == "__main__":
    unittest.main()
