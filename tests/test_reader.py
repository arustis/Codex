"""Ejercicio de los bucles reales de lectura con transportes simulados."""
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

from config import ReaderConfig
from reader import Reader


class ReaderLoopTests(unittest.TestCase):
    def setUp(self):
        self.config = ReaderConfig(vendor_id=1, product_id=2)
        self.events = []
        self.reader = Reader(self.config, self.collect)
        self.devices = {"hid": [], "serial": [], "errors": []}

    def collect(self, kind, value):
        self.events.append((kind, value))
        if kind == "card":
            self.reader.stop()

    def test_serial_reads_fragmented_card_and_closes(self):
        self.devices["serial"] = [dict(vendor_id=1, product_id=2, port="COM8")]
        source = Mock()
        source.read.side_effect = [b"01025:", b"65874\r\n"]
        serial = SimpleNamespace(Serial=Mock(return_value=source))
        with patch("reader.inventory", return_value=self.devices), patch.dict("sys.modules", serial=serial):
            self.reader._run()
        self.assertIn(("card", "01025:65874"), self.events)
        serial.Serial.assert_called_once_with("COM8", 9600, timeout=0.2)
        source.close.assert_called_once()

    def test_disconnect_is_friendly_and_closes(self):
        self.devices["serial"] = [dict(vendor_id=1, product_id=2, port="COM8")]
        source = Mock()
        source.read.side_effect = OSError("disconnected")
        with patch("reader.inventory", return_value=self.devices), patch.dict(
                "sys.modules", serial=SimpleNamespace(Serial=Mock(return_value=source))):
            self.reader._run()
        self.assertTrue(any(kind == "error" and "disconnected" in value for kind, value in self.events))
        source.close.assert_called_once()

    def test_bad_card_does_not_prevent_next_card(self):
        self.devices["serial"] = [dict(vendor_id=1, product_id=2, port="COM8")]
        source = Mock()
        source.read.side_effect = [b"bad:123\n", b"01025:65874\n"]
        with patch("reader.inventory", return_value=self.devices), patch.dict(
                "sys.modules", serial=SimpleNamespace(Serial=Mock(return_value=source))):
            self.reader._run()
        self.assertTrue(any(kind == "invalid" for kind, _ in self.events))
        self.assertIn(("card", "01025:65874"), self.events)

    def test_hid_report_offset_padding_and_framing(self):
        self.reader.config = replace(self.config, mode="hid_text", hid_payload_offset=1)
        self.devices["hid"] = [dict(vendor_id=1, product_id=2, usage_page=0xff00, usage=1, path="usb-path")]
        source = Mock()
        source.read.return_value = list(b"\x01" + b"01025:65874\r\n\x00\x00")
        with patch("reader.inventory", return_value=self.devices), patch.dict(
                "sys.modules", hid=SimpleNamespace(device=Mock(return_value=source))):
            self.reader._run()
        self.assertIn(("card", "01025:65874"), self.events)
        source.open_path.assert_called_once_with(b"usb-path")
        source.close.assert_called_once()

    def test_bad_and_good_card_in_same_serial_block(self):
        self.devices["serial"] = [dict(vendor_id=1, product_id=2, port="COM8")]
        source = Mock()
        source.read.return_value = b"bad:123\n01025:65874\n"
        with patch("reader.inventory", return_value=self.devices), patch.dict(
                "sys.modules", serial=SimpleNamespace(Serial=Mock(return_value=source))):
            self.reader._run()
        self.assertTrue(any(kind == "invalid" for kind, _ in self.events))
        self.assertIn(("card", "01025:65874"), self.events)

    def test_sdk_bridge_contract(self):
        self.reader.config = replace(self.config, mode="sdk", sdk_module="test_sdk_bridge")
        source = Mock()
        source.read_card.side_effect = [None, "01025:65874"]
        bridge = SimpleNamespace(open_reader=Mock(return_value=source))
        with patch("reader.inventory", return_value=self.devices), patch.dict(
                "sys.modules", test_sdk_bridge=bridge):
            self.reader._run()
        self.assertIn(("card", "01025:65874"), self.events)
        source.read_card.assert_called_with(timeout_ms=200)
        source.close.assert_called_once()

    def test_keyboard_removal_detected(self):
        self.devices["hid"] = [dict(vendor_id=1, product_id=2, usage_page=1, usage=6)]
        empty = dict(hid=[], serial=[], errors=[])
        with patch("reader.inventory", side_effect=[self.devices, empty]), patch.object(
                self.reader.stop_event, "wait", return_value=False):
            self.reader._run()
        self.assertEqual(self.events[0][0], "keyboard")
        self.assertEqual(self.events[-1][0], "error")


if __name__ == "__main__":
    unittest.main()
