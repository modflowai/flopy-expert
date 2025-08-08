#!/usr/bin/env python3
"""
Check which test models are missing MODFLOW output files (.hds, .cbc, .lst)
"""

import os
import glob

def check_model_outputs():
    models_dir = "/home/danilopezmella/flopy_expert/test_review/models"
    
    missing_outputs = []
    has_outputs = []
    no_model_output_dir = []
    
    # Find all basic directories
    for model_path in glob.glob(os.path.join(models_dir, "test_*/basic")):
        model_name = os.path.basename(os.path.dirname(model_path))
        output_dir = os.path.join(model_path, "model_output")
        
        if not os.path.exists(output_dir):
            # Check if there are subdirectories with output files
            subdir_found = False
            for subdir in os.listdir(model_path):
                subdir_path = os.path.join(model_path, subdir)
                if os.path.isdir(subdir_path) and subdir not in ['metadata.json', 'test_results.json']:
                    # Check if this subdirectory has output files
                    hds_files = glob.glob(os.path.join(subdir_path, "*.hds"))
                    lst_files = glob.glob(os.path.join(subdir_path, "*.lst")) + glob.glob(os.path.join(subdir_path, "*.list"))
                    if hds_files or lst_files:
                        subdir_found = True
                        break
            
            if not subdir_found:
                no_model_output_dir.append(model_name)
            continue
        
        # Check for output files
        hds_files = glob.glob(os.path.join(output_dir, "*.hds"))
        cbc_files = glob.glob(os.path.join(output_dir, "*.cbc"))  
        lst_files = glob.glob(os.path.join(output_dir, "*.lst")) + glob.glob(os.path.join(output_dir, "*.list"))
        
        hds_count = len(hds_files)
        cbc_count = len(cbc_files)
        lst_count = len(lst_files)
        
        if hds_count == 0 and lst_count == 0:
            missing_outputs.append((model_name, hds_count, cbc_count, lst_count))
        else:
            has_outputs.append((model_name, hds_count, cbc_count, lst_count))
    
    print("=== MODELS MISSING OUTPUT FILES ===")
    print(f"Total missing outputs: {len(missing_outputs)}")
    for model_name, hds, cbc, lst in missing_outputs:
        print(f"  {model_name}: hds={hds} cbc={cbc} lst={lst}")
    
    print(f"\n=== MODELS WITH OUTPUT FILES ===") 
    print(f"Total with outputs: {len(has_outputs)}")
    for model_name, hds, cbc, lst in has_outputs:
        print(f"  {model_name}: hds={hds} cbc={cbc} lst={lst}")
    
    print(f"\n=== MODELS WITHOUT model_output DIRECTORY ===")
    print(f"Total without model_output: {len(no_model_output_dir)}")
    for model_name in no_model_output_dir:
        print(f"  {model_name}")
    
    return missing_outputs, has_outputs, no_model_output_dir

if __name__ == "__main__":
    missing, has, no_dir = check_model_outputs()
    
    print(f"\n=== SUMMARY ===")
    print(f"Models missing outputs: {len(missing)}")
    print(f"Models with outputs: {len(has)}")
    print(f"Models without model_output dir: {len(no_dir)}")
    print(f"Total models: {len(missing) + len(has) + len(no_dir)}")