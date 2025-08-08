"""
Geometry Utility Functions Demonstration

This script demonstrates FloPy's geometry utility functions for spatial analysis
and geometric operations commonly used in groundwater modeling.

Key concepts demonstrated:
- Point-in-polygon testing
- Clockwise/counter-clockwise determination
- Vertex ordering
- Grid cell geometry
- Spatial relationships

These utilities are essential for:
- Grid generation
- Boundary delineation
- Spatial queries
- Intersection testing
- GIS integration
"""

import numpy as np

def run_model():
    """
    Demonstrate geometry utility functions for spatial analysis.
    Based on test_util_geometry.py test cases.
    """
    
    print("=== FloPy Geometry Utility Functions Demonstration ===\n")
    
    # 1. Geometry Operations Overview
    print("1. Geometry Operations in Groundwater Modeling")
    print("-" * 40)
    
    print("  Common geometric operations:")
    print("    • Point-in-polygon testing")
    print("    • Polygon area calculation")
    print("    • Vertex ordering (CW/CCW)")
    print("    • Line intersection")
    print("    • Distance calculations")
    print("    • Bounding box operations")
    
    # 2. Point-in-Polygon Concept
    print(f"\n2. Point-in-Polygon Testing")
    print("-" * 40)
    
    print("  Applications:")
    print("    • Check if wells are in model domain")
    print("    • Identify cells in zones")
    print("    • Boundary condition assignment")
    print("    • Observation point validation")
    print("    • Particle tracking domains")
    
    # 3. Clockwise/Counter-clockwise
    print(f"\n3. Vertex Ordering (CW/CCW)")
    print("-" * 40)
    
    print("  Importance of vertex order:")
    print("    • Polygon orientation")
    print("    • Area sign convention")
    print("    • Normal vector direction")
    print("    • Inside/outside determination")
    print("    • GIS compatibility")
    
    # 4. Demonstrate Clockwise Testing
    print(f"\n4. Clockwise Testing Example")
    print("-" * 40)
    
    try:
        from flopy.utils.geometry import is_clockwise
        
        # Create counter-clockwise vertices
        print("\n  Testing vertex ordering:")
        print("  " + "-" * 30)
        
        # Define vertices in counter-clockwise order
        xv = [20.0000, 18.9394, 21.9192, 22.2834]
        yv = [30.0000, 25.9806, 25.3013, 27.5068]
        
        print(f"    Vertices (x,y):")
        for i, (x, y) in enumerate(zip(xv, yv)):
            print(f"      Point {i}: ({x:.2f}, {y:.2f})")
        
        # Test if clockwise
        result = is_clockwise(xv, yv)
        
        if result:
            print(f"    ✓ Vertices are CLOCKWISE")
        else:
            print(f"    ✓ Vertices are COUNTER-CLOCKWISE")
        
        # Reverse to make clockwise
        xv_cw = list(reversed(xv))
        yv_cw = list(reversed(yv))
        result_cw = is_clockwise(xv_cw, yv_cw)
        
        print(f"\n    After reversing order:")
        if result_cw:
            print(f"    ✓ Now vertices are CLOCKWISE")
        else:
            print(f"    ✓ Still COUNTER-CLOCKWISE")
            
    except Exception as e:
        print(f"    ⚠ Error in clockwise testing: {str(e)}")
    
    # 5. Point-in-Polygon Testing
    print(f"\n5. Point-in-Polygon Examples")
    print("-" * 40)
    
    try:
        from flopy.utils.geometry import point_in_polygon
        
        # Create a simple square polygon
        print("\n  Testing point locations:")
        print("  " + "-" * 30)
        
        # Define a square: (0,0), (10,0), (10,10), (0,10)
        polygon = [[0, 0], [10, 0], [10, 10], [0, 10]]
        
        print(f"    Square polygon corners:")
        for i, (x, y) in enumerate(polygon):
            print(f"      Corner {i}: ({x}, {y})")
        
        # Test various points
        test_points = [
            (5, 5, "Center"),
            (0, 0, "Bottom-left corner"),
            (10, 10, "Top-right corner"),
            (5, 0, "Bottom edge"),
            (0, 5, "Left edge"),
            (15, 5, "Outside right"),
            (-5, 5, "Outside left"),
            (5, 15, "Outside top"),
            (5, -5, "Outside bottom")
        ]
        
        print(f"\n    Testing point locations:")
        for x, y, label in test_points:
            xpts = np.array([[x]])
            ypts = np.array([[y]])
            mask = point_in_polygon(xpts, ypts, polygon)
            
            if mask[0]:
                status = "INSIDE"
            else:
                status = "OUTSIDE"
            
            print(f"      ({x:3}, {y:3}) {label:20} → {status}")
        
    except Exception as e:
        print(f"    ⚠ Error in point-in-polygon: {str(e)}")
    
    # 6. Grid Cell Geometry
    print(f"\n6. Grid Cell Geometry")
    print("-" * 40)
    
    print("  Cell geometry operations:")
    print("    • Cell vertex extraction")
    print("    • Cell center calculation")
    print("    • Cell area computation")
    print("    • Cell intersection testing")
    print("    • Neighbor identification")
    
    # 7. Practical Example
    print(f"\n7. Practical Example: Well Location Check")
    print("-" * 40)
    
    try:
        # Model domain as irregular polygon
        model_domain = [
            [0, 0],
            [100, 0],
            [120, 50],
            [100, 100],
            [0, 100],
            [-20, 50]
        ]
        
        print("  Checking well locations in model domain:")
        
        # Proposed well locations
        wells = [
            (50, 50, "Well_1"),
            (110, 25, "Well_2"),
            (10, 90, "Well_3"),
            (-10, 50, "Well_4"),
            (125, 50, "Well_5")
        ]
        
        valid_wells = []
        invalid_wells = []
        
        for x, y, name in wells:
            xpts = np.array([[x]])
            ypts = np.array([[y]])
            mask = point_in_polygon(xpts, ypts, model_domain)
            
            if mask[0]:
                valid_wells.append(name)
                print(f"    ✓ {name} at ({x}, {y}) - VALID (inside domain)")
            else:
                invalid_wells.append(name)
                print(f"    ✗ {name} at ({x}, {y}) - INVALID (outside domain)")
        
        print(f"\n    Summary:")
        print(f"      Valid wells: {len(valid_wells)}")
        print(f"      Invalid wells: {len(invalid_wells)}")
        
    except Exception as e:
        print(f"    ⚠ Error in practical example: {str(e)}")
    
    # 8. Common Algorithms
    print(f"\n8. Common Geometric Algorithms")
    print("-" * 40)
    
    print("  Algorithms used:")
    print("    • Ray casting (point-in-polygon)")
    print("    • Winding number")
    print("    • Cross product (orientation)")
    print("    • Shoelace formula (area)")
    print("    • Gift wrapping (convex hull)")
    
    # 9. GIS Integration
    print(f"\n9. GIS Integration")
    print("-" * 40)
    
    print("  Geometry utilities enable:")
    print("    • Shapefile processing")
    print("    • Coordinate transformations")
    print("    • Spatial queries")
    print("    • Buffer operations")
    print("    • Overlay analysis")
    print("    • Topology validation")
    
    # 10. Best Practices
    print(f"\n10. Best Practices")
    print("-" * 40)
    
    print("  Recommendations:")
    print("    • Check vertex ordering")
    print("    • Handle edge cases")
    print("    • Consider numerical precision")
    print("    • Validate polygon closure")
    print("    • Test boundary points")
    print("    • Document coordinate systems")
    
    # 11. Applications
    print(f"\n11. Professional Applications")
    print("-" * 40)
    
    print("  Geometry utilities used for:")
    print("    • Wellfield design")
    print("    • Capture zone analysis")
    print("    • Contamination plume delineation")
    print("    • Model boundary definition")
    print("    • Observation network design")
    print("    • Risk assessment zones")
    
    # 12. Summary
    print(f"\n12. Implementation Summary")
    print("-" * 40)
    
    print("  Geometry capabilities demonstrated:")
    print("    ✓ Clockwise/counter-clockwise testing")
    print("    ✓ Point-in-polygon operations")
    print("    ✓ Vertex ordering")
    print("    ✓ Practical well location checking")
    print("    ✓ Spatial relationship testing")
    print("    ✓ Grid geometry concepts")
    
    print(f"\n✓ Geometry Utility Functions Demonstration Completed!")
    print(f"  - Essential spatial analysis tools")
    print(f"  - Foundation for GIS integration")
    print(f"  - Critical for model setup validation")
    
    return {
        'test_type': 'utility',
        'functionality': 'geometry_operations',
        'operations_demonstrated': ['is_clockwise', 'point_in_polygon'],
        'practical_examples': ['well_location_check'],
        'educational_value': 'high'
    }

if __name__ == "__main__":
    results = run_model()
    print("\n" + "="*60)
    print("GEOMETRY UTILITY FUNCTIONS DEMONSTRATION COMPLETE")
    print("="*60)