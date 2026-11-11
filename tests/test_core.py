import unittest
from dataclasses import replace
from unittest.mock import Mock

from config import LabelConfig, ReaderConfig
from printer import PrinterError, build_tspl, print_label
from reader import ReaderError, TextFrames, decode_card, parse_card, select_reader, uid_hex


class CardTests(unittest.TestCase):
    def test_hex_uid_is_concatenated_and_retains_all_four_bytes(self):
        for value, expected in (("2518946491", "BB122496"), ("2519062667", "8BD82596"),
                                ("0", "00000000"), ("1", "01000000"),
                                ("4294967295", "FFFFFFFF"), ("01025:65874", "")):
            self.assertEqual(uid_hex(value), expected)
        for value in ("4294967296", "invalid", "1:2:3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                uid_hex(value)

    def test_decimal_uid_confirmed_by_user(self):
        self.assertEqual(decode_card("2518946491"), ("47890", "09366"))
        self.assertIn(b'"47890:09366"', build_tspl(":".join(decode_card("2518946491"))))

    def test_decimal_uid_from_screenshot(self):
        self.assertEqual(decode_card("2519062667"), ("35800", "09622"))

    def test_decimal_uid_bounds_and_padding(self):
        for value, expected in (("0", ("00000", "00000")), ("1", ("00256", "00000")),
                                ("0000000001", ("00256", "00000")),
                                ("4294967295", ("65535", "65535"))):
            self.assertEqual(decode_card(value), expected)
        for value in ("4294967296", "9999999999", "00000000000", "-1", " 2518946491", "BB122496", "١٢٣"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode_card(value)

    def test_formatted_codes_are_never_reinterpreted(self):
        self.assertEqual(decode_card("01025:65874"), ("01025", "65874"))
        self.assertEqual(decode_card("00001:0000002"), ("00001", "0000002"))

    def test_preserves_zeros(self):
        self.assertEqual(parse_card("01025:65874"), ("01025", "65874"))
        self.assertEqual(parse_card("000:000"), ("000", "000"))

    def test_invalid(self):
        for value in ("", ":", "1:", ":2", "1:2:3", " 1:2", "1:2\n", "١:٢", "1:a", "1:2\r\nPRINT 9", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_card(value)

    def test_fragmented_frames_and_crlf(self):
        frames = TextFrames()
        self.assertEqual(frames.feed(b"010"), [])
        self.assertEqual(frames.feed(b"25:65874\r\n001:002\n"), ["01025:65874", "001:002"])

    def test_overflow_does_not_accept_suffix(self):
        frames = TextFrames(4)
        frames.feed(b"xxxxx")
        with self.assertRaises(ReaderError):
            frames.feed(b"1:2\n")
        self.assertEqual(frames.feed(b"1:2\n"), ["1:2"])

    def test_non_ascii(self):
        with self.assertRaises(ReaderError):
            TextFrames().feed(b"\xff\n")


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = ReaderConfig(mode="auto", vendor_id=123, product_id=456)
        self.device = dict(vendor_id=123, product_id=456, usage_page=1, usage=6)
        self.inventory = dict(hid=[self.device], serial=[], errors=[])

    def test_keyboard(self):
        self.assertEqual(select_reader(self.cfg, self.inventory).mode, "keyboard")

    def test_unknown_device_is_not_a_reader(self):
        with self.assertRaises(ReaderError):
            select_reader(replace(self.cfg, vendor_id=999), self.inventory)

    def test_no_guessed_identity(self):
        with self.assertRaises(ReaderError):
            select_reader(ReaderConfig(mode="auto"), self.inventory)

    def test_generic_hid_requires_explicit_protocol(self):
        self.device["usage"] = 1
        with self.assertRaisesRegex(ReaderError, "protocolo/SDK"):
            select_reader(self.cfg, self.inventory)
        self.assertEqual(select_reader(replace(self.cfg, mode="hid_text"), self.inventory).mode, "hid_text")

    def test_ambiguous(self):
        self.inventory["hid"].append(dict(self.device))
        with self.assertRaises(ReaderError):
            select_reader(self.cfg, self.inventory)

    def test_serial(self):
        self.inventory["hid"] = []
        self.inventory["serial"] = [dict(self.device, port="COM3")]
        self.assertEqual(select_reader(self.cfg, self.inventory).mode, "serial")


class PrinterTests(unittest.TestCase):
    def backend(self):
        api = Mock(PRINTER_ENUM_LOCAL=2, PRINTER_ENUM_CONNECTIONS=4)
        api.EnumPrinters.return_value = [(0, "", "TSC TE200", "")]
        api.GetPrinter.return_value = {"Status": 0}
        api.StartDocPrinter.return_value = 7
        api.WritePrinter.side_effect = lambda handle, data: len(data)
        return api

    def test_exact_payload(self):
        data = build_tspl("01025:65874")
        self.assertEqual(data, b'SIZE 50 mm,30 mm\r\nGAP 2 mm,0 mm\r\nDIRECTION 1\r\nREFERENCE 0,0\r\nCLS\r\nTEXT 30,30,"3",0,1,1,"01025:65874"\r\nPRINT 1,1\r\n')

    def test_config_validation(self):
        for label in (LabelConfig(width_mm=0), LabelConfig(gap_mm=-1), LabelConfig(width_mm=float("nan")),
                      LabelConfig(font='3"\r\nPRINT 2'), LabelConfig(scale_x=0), LabelConfig(x=-1)):
            with self.subTest(label=label), self.assertRaises(ValueError):
                build_tspl("1:2", label)

    def test_raw_spooling_and_close(self):
        api = self.backend()
        self.assertEqual(print_label("01025:65874", "TSC TE200", backend=api), 7)
        self.assertEqual(api.StartDocPrinter.call_args.args[2][2], "RAW")
        self.assertEqual(api.WritePrinter.call_args.args[1], build_tspl("01025:65874"))
        api.EndDocPrinter.assert_called_once()
        api.ClosePrinter.assert_called_once()
        api.AbortPrinter.assert_not_called()

    def test_partial_writes(self):
        api = self.backend()
        api.WritePrinter.side_effect = lambda handle, data: min(7, len(data))
        print_label("1:2", "TSC TE200", backend=api)
        self.assertGreater(api.WritePrinter.call_count, 1)

    def test_failed_write_aborts(self):
        for behavior in (0, OSError("USB error")):
            api = self.backend()
            api.WritePrinter.side_effect = None
            if isinstance(behavior, Exception):
                api.WritePrinter.side_effect = behavior
            else:
                api.WritePrinter.return_value = behavior
            with self.assertRaises(PrinterError):
                print_label("1:2", "TSC TE200", backend=api)
            api.AbortPrinter.assert_called_once()
            api.ClosePrinter.assert_called_once()

    def test_missing_printer(self):
        api = self.backend()
        with self.assertRaises(PrinterError):
            print_label("1:2", "Other", backend=api)
        api.OpenPrinter.assert_not_called()

    def test_offline(self):
        api = self.backend()
        api.GetPrinter.return_value = {"Status": 0x80}
        with self.assertRaises(PrinterError):
            print_label("1:2", "TSC TE200", backend=api)
        api.StartDocPrinter.assert_not_called()
        api.ClosePrinter.assert_called_once()


if __name__ == "__main__":
    unittest.main()
