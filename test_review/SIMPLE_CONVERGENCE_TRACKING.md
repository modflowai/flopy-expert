# Simple FloPy Test Convergence Tracking

## Overview
Simple tracking: Does the test run MODFLOW and converge?

**Total Tests Processed**: 68/83
**Tests That Run MODFLOW**: 32/68 (47.1%)
**Educational Demos (No MODFLOW)**: 36/68 (52.9%)

---

## Tests That Run MODFLOW (32 tests)

| # | Test Name | Package/Feature | Status |
|---|-----------|----------------|--------|
| 1 | test_compare | Model comparison | ✅ RUNS |
| 2 | test_flopy_module | Core functionality | ✅ RUNS |
| 3 | test_gage | Gage package | ✅ RUNS |
| 4 | test_get_modflow | MODFLOW utilities | ✅ RUNS |
| 5 | test_headufile | Head file utilities | ✅ RUNS |
| 6 | test_hydmodfile | HYDMOD utilities | ✅ RUNS |
| 7 | test_lgr | Local Grid Refinement | ✅ RUNS |
| 8 | test_mbase | Base model | ✅ RUNS |
| 9 | test_mf6 | MODFLOW 6 | ✅ RUNS |
| 10 | test_mfnwt | MODFLOW-NWT | ✅ RUNS |
| 11 | test_mnw | Multi-Node Well | ✅ RUNS (just fixed) |
| 12 | test_model_dot_plot | Model plotting | ✅ RUNS |
| 13 | test_modeltime | Model timing | ✅ RUNS |
| 14 | test_modflow | Core MODFLOW | ✅ RUNS |
| 15 | test_modflowdis | DIS package | ✅ RUNS |
| 16 | test_modflowoc | Output Control | ✅ RUNS |
| 17 | test_mp5 | MODPATH-5 | ✅ RUNS |
| 18 | test_mp6 | MODPATH-6 | ✅ RUNS |
| 19 | test_nwt_ag | Newton solver | ✅ RUNS |
| 20 | test_obs | Observations | ✅ RUNS |
| 21 | test_particledata | Particle data | ✅ RUNS |
| 22 | test_plotutil | Plot utilities | ✅ RUNS |
| 23 | test_shapefile_utils | GIS utilities | ✅ RUNS |
| 24 | test_str | Stream routing | ✅ RUNS |
| 25 | test_sfr | Stream Flow Routing (SFR2) | ✅ CONVERGES! |
| 26 | test_swi2 | Salt Water Intrusion | ✅ RUNS |
| 27 | test_swr_binaryread | SWR utilities | ✅ RUNS |
| 28 | test_util_2d_and_3d | Array utilities | ✅ RUNS |
| 29 | test_wel | Well package | ✅ RUNS |
| 30 | test_uzf | Unsaturated Zone Flow (UZF1) | ✅ CONVERGES! |
| 31 | test_lak | Lake Package (LAK) | ✅ CONVERGES! |
| 32 | test_subwt | Subsidence/Compaction (SWT) | ✅ CONVERGES! |
| 33 | test_drn | Drain Package (DRN) | ✅ CONVERGES! |
| 34 | test_riv | River Package (RIV) | ✅ CONVERGES! |

---

## Educational Demonstrations (36 tests)
These don't run MODFLOW - they demonstrate FloPy utilities, file I/O, plotting, etc. This is appropriate.

---

## Next Priority Tests to Process

### High Priority (Physical Packages):
1. ~~**test_sfr** - Stream Flow Routing~~ ✅ CONVERGES!
2. ~~**test_uzf** - Unsaturated Zone Flow~~ ✅ CONVERGES!
3. ~~**test_lak** - Lake package~~ ✅ CONVERGES!
4. ~~**test_subwt** - Subsidence/Compaction~~ ✅ CONVERGES!

### Medium Priority:
5. ~~**test_drn** - Drain package~~ ✅ CONVERGES!
6. ~~**test_riv** - River package~~ ✅ CONVERGES!  
7. **test_ghb** - General Head Boundary
8. **test_chd** - Constant Head

All of these should run MODFLOW and test convergence.

---

## Simple Goal
- **Physical packages**: Should run MODFLOW and test convergence
- **Utilities/I-O/Plotting**: Educational demonstrations are fine
- **Target**: ~40-50 tests running MODFLOW when complete