# Analyze FloPy Test: test_formattedfile.py

## Test Code
```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes

from flopy.utils import FormattedHeadFile


@pytest.fixture
def freyberg_model_path(example_data_path):
    return example_data_path / "freyberg"


def test_headfile_build_index(example_data_path):
    # test low-level FormattedLayerFile._build_index() method
    pth = example_data_path / "mf2005_test" / "test1tr.githds"
    with FormattedHeadFile(pth) as hds:
        pass
    assert hds.nrow == 15
    assert hds.ncol == 10
    assert hds.nlay == 1
    assert not hasattr(hds, "nper")
    assert hds.totalbytes == 1613
    assert len(hds.recordarray) == 1
    assert type(hds.recordarray) == np.ndarray
    assert hds.recordarray.dtype == np.dtype(
        [
            ("kstp", "i4"),
            ("kper", "i4"),
            ("pertim", "f4"),
            ("totim", "f4"),
            ("text", "S16"),
            ("ncol", "i4"),
            ("nrow", "i4"),
            ("ilay", "i4"),
        ]
    )
    flt32time = np.float32(1577880000.0)
    assert hds.recordarray.tolist() == [
        (50, 1, float(flt32time), float(flt32time), b"HEAD", 10, 15, 1)
    ]
    assert hds.times == [flt32time]
    assert hds.kstpkper == [(50, 1)]
    np.testing.assert_array_equal(hds.iposarray, [98])
    assert hds.iposarray.dtype == np.int64
    with pytest.deprecated_call(match="use headers instead"):
        assert hds.list_records() is None
    pd.testing.assert_frame_equal(
        hds.headers,
        pd.DataFrame(
            [
                {
                    "kstp": np.int32(50),
                    "kper": np.int32(1),
                    "pertim": flt32time,
                    "totim": flt32time,
                    "text": "HEAD",
                    "ncol": np.int32(10),
                    "nrow": np.int32(15),
                    "ilay": np.int32(1),
                }
            ],
            index=[98],
        ),
    )


def test_formattedfile_reference(example_data_path):
    h = FormattedHeadFile(example_data_path / "mf2005_test" / "test1tr.githds")
    assert isinstance(h, FormattedHeadFile)
    h.mg.set_coord_info(xoff=1000.0, yoff=200.0, angrot=15.0)

    assert isinstance(h.plot(masked_values=[6999.000]), Axes)
    plt.close()


def test_formattedfile_read(function_tmpdir, example_data_path):
    mf2005_model_path = example_data_path / "mf2005_test"
    h = FormattedHeadFile(mf2005_model_path / "test1tr.githds")
    assert isinstance(h, FormattedHeadFile)

    # check number of records
    assert len(h) == 1
    with pytest.deprecated_call():
        assert h.get_nrecords() == 1
    assert not hasattr(h, "nrecords")

    times = h.get_times()
    assert np.isclose(times[0], 1577880064.0)

    kstpkper = h.get_kstpkper()
    assert kstpkper[0] == (49, 0), "kstpkper[0] != (49, 0)"

    h0 = h.get_data(totim=times[0])
    h1 = h.get_data(kstpkper=kstpkper[0])
    h2 = h.get_data(idx=0)
    assert np.array_equal(h0, h1), (
    ...  # Truncated for brevity
```

## Task: Extract Metadata AND Generate Standalone Model

Analyze this test and provide BOTH:
1. Metadata for semantic search database
2. Standalone, runnable FloPy model(s)

### Part 1: METADATA EXTRACTION

Extract the following for database/search:

1. **Test Analysis**:
   - `true_purpose`: What is this test ACTUALLY testing?
   - `is_useful_example`: Would this make a good example? (true/false)
   - `example_demonstrates`: One-line description of what it shows

2. **Documentation**:
   - `purpose`: Clear 1-2 sentence description for users
   - `key_concepts`: List of concepts demonstrated
   - `questions_answered`: 3-5 specific questions this example answers
   - `common_use_cases`: Real-world scenarios where this applies

3. **Classification**:
   - `primary_phase`: Which of the 7 phases is PRIMARY (1-7)
   - `secondary_phases`: Other phases involved
   - `modflow_version`: mf6/mf2005/mfnwt/mfusg/mt3d
   - `packages_used`: List all FloPy packages/modules used

4. **Search Metadata**:
   - `keywords`: 5-10 search terms
   - `embedding_string`: ~150 word description combining purpose + questions + concepts

### Part 2: STANDALONE MODEL GENERATION

Create runnable FloPy model(s):

1. **Model Requirements**:
   - Only create multiple models if test actually tests different discretizations
   - For example, test_binaryfile_reverse tests dis/disv/disu, so create 3 models
   - Most tests will only need 1 model

2. **Phase Organization** - Structure following the 7 phases:
   - Phase 1: Discretization (DIS/DISV/DISU, TDIS)
   - Phase 2: Properties (NPF, STO)
   - Phase 3: Initial Conditions (IC)
   - Phase 4: Boundary Conditions (CHD, WEL, etc.)
   - Phase 5: Solver Configuration (IMS)
   - Phase 6: Observations (optional)
   - Phase 7: Post-processing

3. **Code Quality**:
   - Remove all test assertions and pytest code
   - Add clear phase comments
   - Must be runnable standalone
   - Include basic verification

Return EXACTLY this JSON structure:
{
  "metadata": {
    "purpose": "Brief description of what this example demonstrates",
    "primary_phase": 1-7,
    "modflow_version": "mf6" or "mf2005", 
    "packages_used": ["list", "of", "packages"],
    "keywords": ["relevant", "keywords"]
  },
  "models": [
    {
      "name": "model_name",
      "description": "What this model demonstrates", 
      "code": "complete_python_code_here"
    }
  ]
}
