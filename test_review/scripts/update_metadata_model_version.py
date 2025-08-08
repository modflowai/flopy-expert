#!/usr/bin/env python3

"""
Update all metadata.json files to include model_version field
indicating which MODFLOW version is being used (mf6, mf2005, mfnwt, mfusg)
"""

import json
from pathlib import Path

def determine_model_version(metadata):
    """
    Determine MODFLOW version based on packages used.
    """
    packages = metadata.get('packages', [])
    package_names = [p.get('package', '') for p in packages]
    package_files = [p.get('file', '') for p in packages]
    
    # Check for MF6 packages
    if any('flopy.mf6' in f for f in package_files):
        return 'mf6'
    
    # Check for MFNWT-specific packages
    if any('NWT' in p for p in package_names):
        return 'mfnwt'
    
    # Check for MFUSG-specific packages
    if any(p in ['DISU', 'SMS'] for p in package_names):
        return 'mfusg'
    
    # Check for MF2005/MF2000 packages
    if any('flopy.modflow' in f for f in package_files):
        # More specific checks
        if 'UPW' in package_names:
            return 'mfnwt'  # UPW is typically MFNWT
        elif 'LPF' in package_names or 'BCF' in package_names:
            return 'mf2005'  # Default to MF2005 for standard packages
        else:
            return 'mf2005'
    
    # Default to mf2005 if unclear
    return 'mf2005'

def update_metadata_files():
    """
    Update all metadata.json files with model_version field.
    """
    models_dir = Path('/home/danilopezmella/flopy_expert/test_review/models')
    
    updated_count = 0
    
    # Find all metadata.json files
    for metadata_file in models_dir.rglob('metadata.json'):
        try:
            # Load existing metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Skip if already has model_version
            if 'model_version' in metadata:
                print(f"✓ Already has model_version: {metadata_file.parent.name}")
                continue
            
            # Determine model version
            model_version = determine_model_version(metadata)
            
            # Special cases based on test name or path
            parent_dir = metadata_file.parent.name
            test_dir = metadata_file.parent.parent.name
            
            # Override based on specific tests
            if 'mfnwt' in test_dir.lower():
                model_version = 'mfnwt'
            elif 'mf6' in test_dir.lower():
                model_version = 'mf6'
            elif 'mnw' in test_dir.lower():
                # MNW1 and MNW2 are MF2005 packages
                model_version = 'mf2005'
            elif 'usg' in test_dir.lower():
                model_version = 'mfusg'
            
            # Add model_version as second field (after source_test)
            updated_metadata = {
                'source_test': metadata.get('source_test'),
                'model_version': model_version
            }
            
            # Add remaining fields in order
            for key, value in metadata.items():
                if key != 'source_test':
                    updated_metadata[key] = value
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(updated_metadata, f, indent=2)
            
            updated_count += 1
            print(f"✅ Updated {test_dir}/{parent_dir}: {model_version}")
            
        except Exception as e:
            print(f"❌ Error updating {metadata_file}: {e}")
    
    print(f"\n✅ Updated {updated_count} metadata files")

if __name__ == "__main__":
    update_metadata_files()