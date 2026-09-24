import os
from pathlib import Path

import pytest

from civilfem.fem import build_calculix_input, parse_frd_results, run_calculix


def test_build_calculix_input_contains_3d_model_sections(tmp_path):
    mesh = {
        "points": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]],
        "cells": [{"type": "tetra", "data": [[0, 1, 2, 3], [1, 2, 3, 4]]}],
    }
    inp = build_calculix_input(mesh, tmp_path / "beam.inp", youngs_modulus=206000, poisson_ratio=0.3)
    text = inp.read_text(encoding="ascii")
    assert "*NODE" in text
    assert "*ELEMENT, TYPE=C3D4" in text
    assert "*MATERIAL, NAME=STEEL" in text
    assert "*BOUNDARY" in text
    assert "*CLOAD" in text
    assert "*STATIC" in text


def test_build_calculix_input_distributes_bending_couple_in_two_directions(tmp_path):
    mesh = {
        "points": [[0, -1, -1], [0, 1, -1], [0, 0, 1], [1, -1, -1], [1, 1, -1], [1, 0, 1], [1, -1, 1], [1, 1, 1]],
        "cells": [{"type": "tetra", "data": [[0, 1, 2, 3], [3, 4, 5, 6]]}],
    }
    inp = build_calculix_input(mesh, tmp_path / "beam.inp", moment_x=1000)
    text = inp.read_text(encoding="ascii")
    assert ", 2, " in text
    assert ", 3, " in text


def test_parse_frd_results_extracts_displacement_and_stress(tmp_path):
    frd = tmp_path / "beam.frd"
    frd.write_text(
        """    1PSTEP\n -4  DISP\n -5 1 0 0 0\n -5 2 1.0 2.0 3.0\n -3\n -4 STRESS\n -5 1 10 20 30 4 5 6\n -5 2 20 10 0 0 0 0\n -3\n -1\n""",
        encoding="ascii",
    )
    result = parse_frd_results(frd)
    assert result["max_displacement"] == pytest.approx(3.741657, rel=1e-5)
    assert result["max_von_mises"] > 0
    assert result["displacement_units"] == "mm"
    assert result["stress_units"] == "MPa"


def test_run_calculix_missing_executable_is_explicit(tmp_path):
    result = run_calculix(tmp_path / "beam.inp", executable=str(tmp_path / "missing-ccx.exe"))
    assert result["status"] == "not_implemented"
