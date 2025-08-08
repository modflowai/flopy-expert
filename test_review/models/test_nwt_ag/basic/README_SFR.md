# Making SFR Work with AG Package

## What SFR (Stream Flow Routing) Package Needs

To make the SFR package work properly with the AG package in MODFLOW-NWT, you need:

### 1. **Stream Network Definition**
- **Reach Data**: Defines individual stream cells
  - Layer, row, column location
  - Segment and reach numbers
  - Stream top elevation (must decrease downstream)
  - Stream bed properties (thickness, hydraulic conductivity)

### 2. **Segment Data**: 
- Defines connected stream segments
  - Segment connections (upstream/downstream)
  - Flow calculation method (icalc)
  - Channel geometry (width, roughness)
  - Inflow rates

### 3. **Critical Requirements**
- **Positive Slope**: Stream elevations MUST decrease downstream
- **No Constant Head Conflicts**: Streams shouldn't be in constant head cells
- **Proper Segment Numbering**: Sequential and logical

### 4. **For AG Package Integration**
The AG package uses SFR for:
- Surface water diversions for irrigation
- Return flows from irrigated areas
- Conjunctive use management (surface + groundwater)

## Common Issues and Solutions

### Issue 1: "SLOPE IS ZERO OR NEGATIVE"
**Cause**: Stream top elevations not decreasing downstream
**Solution**: Ensure each reach has lower elevation than upstream reach

### Issue 2: "STREAM CONNECTED TO CONSTANT HEAD CELL"
**Cause**: Stream reach in a cell with ibound = -1
**Solution**: Avoid placing streams in constant head boundary cells

### Issue 3: AG Package Not Creating File
**Cause**: AG package requires specific irrigation data structures
**Solution**: Provide proper irrigation diversion and well data

## Working Example Structure

```python
# 1. Create stream reaches avoiding boundaries
for row in range(1, nrow-1):  # Skip boundary rows
    reach_data.append([...])

# 2. Set decreasing elevations
strtop = starting_elevation - (reach_number * gradient)

# 3. Use proper SFR data structures
reach_data_rec = flopy.modflow.ModflowSfr2.get_empty_reach_data(nreaches)
segment_data = flopy.modflow.ModflowSfr2.get_empty_segment_data(nsegments)

# 4. Create SFR before AG
sfr = flopy.modflow.ModflowSfr2(mf, ...)
ag = flopy.modflow.ModflowAg(mf, ...)
```

## Key Insights

1. **SFR is Complex**: Requires careful setup of elevations and connections
2. **AG Dependency**: AG package REQUIRES SFR for surface water features
3. **NWT Solver**: Works best with Newton-Raphson solver for convergence
4. **Data Structures**: FloPy uses specific numpy record arrays for SFR/AG

## Practical Application

For real models:
- Use GIS data for stream networks
- Calculate slopes from DEM data
- Define irrigation districts with actual diversion points
- Include return flow fractions
- Model seasonal irrigation patterns

The test_nwt_ag model demonstrates that the AG package correctly requires SFR - this is not a bug but proper MODFLOW-NWT behavior for agricultural water management.