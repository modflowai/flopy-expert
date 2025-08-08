#!/bin/bash
# Batch fix workspace directories for all models

models=(
    test_dis_cases
    test_example_notebooks
    test_flopy_io
    test_flopy_module
    test_formattedfile
    test_gage
    test_geospatial_util
    test_grid
    test_grid_cases
    test_gridgen
    test_gridintersect
    test_gridutil
    test_headufile
    test_hydmodfile
    test_lake_connections
    test_lgrutil
    test_listbudget
    test_mbase
    test_mf6
    test_mfnwt
    test_mfreadnam
    test_mfsimlist
    test_modflowdis
    test_modflowoc
    test_modpathfile
    test_mp5
    test_mp6
    test_mp7
    test_mp7_cases
    test_mt3d
    test_nwt_ag
    test_obs
    test_plotutil
    test_swi2
    test_wel
)

for model in "${models[@]}"; do
    model_py="/home/danilopezmella/flopy_expert/test_review/models/$model/basic/model.py"
    
    if [ -f "$model_py" ]; then
        echo "Fixing $model..."
        
        # Fix workspace paths
        sed -i "s/ws = '.*'/ws = '.\/model_output'/g" "$model_py"
        sed -i "s/workspace = '.*'/workspace = '.\/model_output'/g" "$model_py"
        sed -i "s/model_ws = '.*'/model_ws = '.\/model_output'/g" "$model_py"
        sed -i "s/sim_ws = '.*'/sim_ws = '.\/model_output'/g" "$model_py"
        
        # Fix common non-standard paths
        sed -i "s/ws = \".*\"/ws = \".\/model_output\"/g" "$model_py"
        sed -i "s/workspace = \".*\"/workspace = \".\/model_output\"/g" "$model_py"
        sed -i "s/model_ws = \".*\"/model_ws = \".\/model_output\"/g" "$model_py"
        
        echo "  ✓ Fixed workspace paths for $model"
    else
        echo "  ⚠ Model file not found: $model_py"
    fi
done

echo "Batch workspace fix complete!"