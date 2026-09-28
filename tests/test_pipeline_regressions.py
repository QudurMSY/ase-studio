#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Behnam Farnaghinejad <behnam.farnaghinejad@polito.it>
# SPDX-License-Identifier: GPL-2.0-only
"""Stable acceptance tests for ASE Studio's teaching pipeline."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


STUDIO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = Path(__file__).resolve().parent / "golden" / "exams"
SPEC = importlib.util.spec_from_file_location(
    "ase_studio_golden_backend", STUDIO_ROOT / "backend.py")
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


def normalized_csv(value: str) -> str:
    """Make checked-in LF files comparable with csv.writer's CRLF output."""
    return value.replace("\r\n", "\n")


class PipelineRegressionTests(unittest.TestCase):
    def test_no_forwarding_raw_wait_starts_after_decode(self):
        """A RAW consumer must enter D before waiting for register Writeback."""
        configuration = backend.DEFAULT_CONFIG.copy()
        configuration.update({
            "cpu": "in-order",
            "memoryMode": "direct",
            "forwarding": False,
            "instructionMemoryLatency": 1,
            "dataReadLatency": 1,
            "dataWriteLatency": 1,
        })
        rows = [
            {
                "address": "10000", "instruction": "addi x5, x0, 1",
                "cycles": {"1": "F", "2": "D", "3": "E", "4": "M", "5": "W"},
            },
            {
                "address": "10004", "instruction": "add x6, x5, x5",
                "cycles": {"2": "F", "3": "D", "4": "E", "5": "M", "6": "W"},
            },
        ]
        data = {
            "instructions": rows,
            "dynamicInstructions": rows,
            "jumps": [],
            "registerDeltas": {},
            "memoryDeltas": {},
            "pcDeltas": {},
        }

        self.assertTrue(
            backend.schedule_direct_in_order_pipeline(data, configuration))
        self.assertEqual(rows[1]["cycles"], {
            "2": "F", "3": "D", "4": "S", "5": "S",
            "6": "E", "7": "M", "8": "W",
        })

    def test_exam_pipeline_csv_matches_golden_values(self):
        """All frozen exam traces must retain their accepted pipeline tables."""
        cases = sorted(path for path in GOLDEN_ROOT.iterdir() if path.is_dir())
        self.assertTrue(cases, "No golden exam cases were found")
        saved_paths = (
            backend.ROOT, backend.PROGRAMS, backend.RESULTS,
            backend.ENVIRONMENT_CONFIG,
        )
        try:
            with tempfile.TemporaryDirectory(prefix="ase-golden-exams-") as temp:
                root = Path(temp)
                backend.ROOT = root
                backend.PROGRAMS = root / "programs"
                backend.RESULTS = root / "results"
                backend.ENVIRONMENT_CONFIG = root / ".ase-studio-env.json"

                for case in cases:
                    project = backend.PROGRAMS / case.name
                    result = backend.RESULTS / case.name
                    project.mkdir(parents=True)
                    result.mkdir(parents=True)
                    shutil.copyfile(case / "source.s", project / "main.s")
                    shutil.copyfile(case / "config.json",
                                    project / ".ase-studio.json")
                    shutil.copyfile(case / "program.dump", project / "main.dump")
                    shutil.copyfile(case / "trace.log",
                                    result / "gem5_inorder.log")

                for case in cases:
                    with self.subTest(exam=case.name):
                        expected_config = json.loads(
                            (case / "config.json").read_text())
                        actual_config = backend.project_config(
                            backend.PROGRAMS / case.name)
                        self.assertEqual(actual_config, expected_config)

                        data = backend.pipeline(case.name)
                        actual = normalized_csv(
                            backend.pipeline_csv(data, expand_loops=True))
                        expected = normalized_csv(
                            (case / "pipeline.csv").read_text())
                        if actual != expected:
                            expected_lines = expected.splitlines()
                            actual_lines = actual.splitlines()
                            mismatch = next(
                                (index for index, pair in enumerate(
                                    zip(expected_lines, actual_lines), 1)
                                 if pair[0] != pair[1]),
                                min(len(expected_lines), len(actual_lines)) + 1,
                            )
                            self.fail(
                                f"{case.name} pipeline CSV changed at line {mismatch}; "
                                f"expected sha256 "
                                f"{hashlib.sha256(expected.encode()).hexdigest()}, "
                                f"received "
                                f"{hashlib.sha256(actual.encode()).hexdigest()}")
        finally:
            (backend.ROOT, backend.PROGRAMS, backend.RESULTS,
             backend.ENVIRONMENT_CONFIG) = saved_paths


if __name__ == "__main__":
    unittest.main()
