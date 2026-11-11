import json
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from config import LABEL, LabelConfig, label_from_fields, load_label, save_label
from printer import build_tspl, print_label


class LabelSettingsTests(unittest.TestCase):
    def test_settings_survive_restart(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / "preferences" / "label.json"
            label = LabelConfig(width_mm=30, height_mm=15, gap_mm=3, x=16, y=16, font="2")
            self.assertEqual(load_label(path), LABEL)
            save_label(label, path)
            self.assertEqual(load_label(path), label)
            self.assertEqual(json.loads(path.read_text())["height_mm"], 15)

    def test_corrupt_and_invalid_settings_are_not_silently_used(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = Path(directory) / "label.json"
            for contents in ("not json", '{"dpi": 0}', '{"height_mm": -1}', '{"unexpected": 1}'):
                path.write_text(contents)
                with self.subTest(contents=contents), self.assertRaises(ValueError):
                    load_label(path)

    def test_dialog_accepts_decimal_comma_and_rejects_invalid_values(self):
        values = {key: str(value) for key, value in asdict(LABEL).items()}
        values["gap_mm"] = "2,5"
        self.assertEqual(label_from_fields(values).gap_mm, 2.5)
        for field, value in (("height_mm", "0"), ("dpi", "600"), ("direction", "2"),
                             ("x", "1.5"), ("width_mm", "nan"), ("scale_y", "0")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                label_from_fields(dict(values, **{field: value}))

    def test_real_stock_and_explicit_origin_in_tspl(self):
        label = LabelConfig(width_mm=30, height_mm=15, gap_mm=3, x=16, y=16, font="2")
        data = build_tspl("47890:09366", label)
        self.assertIn(b"SIZE 30 mm,15 mm\r\nGAP 3 mm,0 mm", data)
        self.assertIn(b"DIRECTION 0,0\r\nREFERENCE 0,0\r\nSHIFT 0,0\r\nOFFSET 0 mm", data)
        self.assertIn(b'TEXT 16,16,"2",0,1,1,"47890:09366"', data)
        self.assertEqual(data.count(b"PRINT 1,1"), 1)

    def test_clipped_layout_is_rejected_before_any_spooler_call(self):
        for label in (replace(LABEL, width_mm=15), replace(LABEL, height_mm=4),
                      replace(LABEL, scale_x=10), replace(LABEL, x=400)):
            api = Mock()
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "no cabe"):
                print_label("47890:09366", "TSC TE200", label, backend=api)
            api.OpenPrinter.assert_not_called()
            api.StartDocPrinter.assert_not_called()

    def test_resolution_changes_bounds_without_changing_content(self):
        label = LabelConfig(width_mm=20, height_mm=10, x=0, y=0, dpi=300, font="3")
        self.assertIn(b'"47890:09366"', build_tspl("47890:09366", label))
        with self.assertRaisesRegex(ValueError, "no cabe"):
            build_tspl("47890:09366", replace(label, dpi=203))
