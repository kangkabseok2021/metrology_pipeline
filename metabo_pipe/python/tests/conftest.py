"""Shared fixtures: synthetic mzML generator and simple spectrum builders."""
from __future__ import annotations

import base64
from pathlib import Path

import numpy as np
import pytest

from metabopipe.reader import Spectrum

# ---------------------------------------------------------------------------
# Synthetic mzML helper
# ---------------------------------------------------------------------------

def _b64_float64(arr: np.ndarray) -> str:
    return base64.b64encode(arr.astype(np.float64).tobytes()).decode()


def _spectrum_xml(index: int, scan_id: int, rt_min: float, mz_arr: np.ndarray, int_arr: np.ndarray) -> str:
    n = len(mz_arr)
    mz_b64 = _b64_float64(mz_arr)
    in_b64 = _b64_float64(int_arr)
    return f"""      <spectrum index="{index}" id="scan={scan_id}" defaultArrayLength="{n}">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
        <scanList count="1">
          <cvParam cvRef="MS" accession="MS:1000795" name="no combination" value=""/>
          <scan>
            <cvParam cvRef="MS" accession="MS:1000016" name="scan start time"
                     value="{rt_min}" unitCvRef="UO" unitAccession="UO:0000031" unitName="minute"/>
          </scan>
        </scanList>
        <binaryDataArrayList count="2">
          <binaryDataArray encodedLength="{len(mz_b64)}">
            <cvParam cvRef="MS" accession="MS:1000514" name="m/z array" value=""/>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float" value=""/>
            <cvParam cvRef="MS" accession="MS:1000576" name="no compression" value=""/>
            <binary>{mz_b64}</binary>
          </binaryDataArray>
          <binaryDataArray encodedLength="{len(in_b64)}">
            <cvParam cvRef="MS" accession="MS:1000515" name="intensity array" value=""/>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float" value=""/>
            <cvParam cvRef="MS" accession="MS:1000576" name="no compression" value=""/>
            <binary>{in_b64}</binary>
          </binaryDataArray>
        </binaryDataArrayList>
      </spectrum>"""


def make_mzml(tmp_path: Path, n_scans: int = 20, target_mz: float = 180.063, peak_scan: int = 10) -> Path:
    """Generate a minimal valid mzML with a Gaussian peak at *peak_scan* for *target_mz*."""
    mz_arr = np.array([target_mz - 0.01, target_mz, target_mz + 0.01, 500.0])
    spectra_xml = []
    for i in range(n_scans):
        rt_min = (i + 1) * 0.05  # 3-second intervals
        sigma = 2.0
        gauss = 1e5 * np.exp(-0.5 * ((i - peak_scan) / sigma) ** 2)
        int_arr = np.array([0.0, gauss, 0.0, 100.0])
        spectra_xml.append(_spectrum_xml(i, i + 1, rt_min, mz_arr, int_arr))

    spectrum_block = "\n".join(spectra_xml)
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<mzML xmlns="http://psi.hupo.org/ms/mzml"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <cvList count="2">
    <cv id="MS" fullName="Proteomics Standards Initiative Mass Spectrometry Ontology"
        version="4.1.30" URI="https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo"/>
    <cv id="UO" fullName="Unit Ontology" version="09:04:2014"
        URI="https://raw.githubusercontent.com/bio-ontology-research-group/unit-ontology/master/unit.obo"/>
  </cvList>
  <fileDescription>
    <fileContent>
      <cvParam cvRef="MS" accession="MS:1000580" name="MSn spectrum" value=""/>
    </fileContent>
  </fileDescription>
  <softwareList count="1">
    <software id="MetaboPipe" version="1.0">
      <cvParam cvRef="MS" accession="MS:1000799" name="custom unreleased software tool" value="MetaboPipe"/>
    </software>
  </softwareList>
  <dataProcessingList count="1">
    <dataProcessing id="dp">
      <processingMethod order="0" softwareRef="MetaboPipe">
        <cvParam cvRef="MS" accession="MS:1000544" name="Conversion to mzML" value=""/>
      </processingMethod>
    </dataProcessing>
  </dataProcessingList>
  <run>
    <spectrumList count="{n_scans}" defaultDataProcessingRef="dp">
{spectrum_block}
    </spectrumList>
  </run>
</mzML>"""
    out = tmp_path / "test_run.mzML"
    out.write_text(xml, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_spectra() -> list[Spectrum]:
    """20 spectra with a Gaussian intensity peak at scan 10, m/z=180.063."""
    target_mz = 180.063
    spectra = []
    for i in range(20):
        rt_sec = (i + 1) * 3.0
        gauss = 1e5 * np.exp(-0.5 * ((i - 10) / 2.0) ** 2)
        spectra.append(
            Spectrum(
                rt=rt_sec,
                mz_array=np.array([target_mz, 500.0]),
                intensity_array=np.array([gauss, 50.0]),
            )
        )
    return spectra


@pytest.fixture
def mzml_file(tmp_path: Path) -> Path:
    return make_mzml(tmp_path, target_mz=180.063, peak_scan=10)
