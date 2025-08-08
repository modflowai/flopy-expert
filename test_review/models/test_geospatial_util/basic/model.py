import numpy as np
import flopy
from flopy.utils.geometry import (
    Point, LineString, Polygon, MultiPoint, 
    MultiLineString, MultiPolygon, Collection
)
from flopy.utils.geospatial_utils import GeoSpatialUtil, GeoSpatialCollection

# Phase 1: Create basic MODFLOW 6 model for spatial context
name = 'geospatial_demo'
sim = flopy.mf6.MFSimulation(sim_name=name, sim_ws='.', exe_name='/home/danilopezmella/flopy_expert/bin/mf6')

# Time discretization
tdis = flopy.mf6.ModflowTdis(sim, nper=1, perioddata=[(1.0, 1, 1.0)])

# Create groundwater flow model
gwf = flopy.mf6.ModflowGwf(sim, modelname=name)

# Discretization - aligned with real coordinates
dis = flopy.mf6.ModflowGwfdis(
    gwf,
    nlay=1,
    nrow=10, 
    ncol=10,
    delr=100.0,
    delc=100.0,
    top=10.0,
    botm=0.0,
    xorigin=-121.4,  # Longitude origin
    yorigin=38.54     # Latitude origin
)

# Phase 2: Node property flow
npf = flopy.mf6.ModflowGwfnpf(gwf, k=10.0)

# Phase 3: Initial conditions
ic = flopy.mf6.ModflowGwfic(gwf, strt=5.0)

# Phase 4: Add CHD boundary
chd = flopy.mf6.ModflowGwfchd(gwf, stress_period_data=[[(0, 0, 0), 4.5]])

# Phase 5: Solver
ims = flopy.mf6.ModflowIms(sim)

# Phase 6: Output control
oc = flopy.mf6.ModflowGwfoc(gwf, 
    head_filerecord='geospatial_demo.hds',
    saverecord=[('HEAD', 'ALL')])

# Phase 7: Demonstrate geospatial utilities
print('\n=== FloPy Geospatial Utilities Demo ===')
print('\nPhase 7: Post-processing with Geospatial Features\n')

# Create Point geometry
point = Point(-121.358560, 38.567760)
print(f'Point: {point.type} at ({point.x}, {point.y})')

# Create LineString geometry
line_coords = [
    (-121.360899, 38.563478),
    (-121.358161, 38.566511),
    (-121.355936, 38.564727),
    (-121.354738, 38.567047)
]
linestring = LineString(line_coords)
print(f'LineString: {linestring.type} with {len(linestring.coords)} vertices')

# Create Polygon geometry
poly_coords = [
    (-121.389308, 38.560816),
    (-121.385435, 38.555018),
    (-121.370609, 38.557232),
    (-121.369932, 38.560575),
    (-121.359327, 38.562767),
    (-121.358641, 38.565972),
    (-121.363391, 38.568835),
    (-121.389308, 38.560816)
]
polygon = Polygon(poly_coords)
print(f'Polygon: {polygon.type} with {len(polygon.exterior)} vertices')

# Create Polygon with hole
outer_ring = [
    (-121.383097, 38.565764),
    (-121.382318, 38.562934),
    (-121.379047, 38.559053),
    (-121.358295, 38.561163),
    (-121.323309, 38.578953),
    (-121.342739, 38.578995),
    (-121.342866, 38.579086),
    (-121.383097, 38.565764)
]
inner_ring = [
    (-121.367281, 38.567214),
    (-121.352168, 38.572258),
    (-121.345857, 38.570301),
    (-121.362633, 38.562622),
    (-121.367281, 38.567214)
]
poly_with_hole = Polygon(outer_ring, [inner_ring])
print(f'Polygon with hole: {len(poly_with_hole.interiors)} holes')

# Create MultiPoint geometry
multipoint_coords = [
    Point(-121.366489, 38.565485),
    Point(-121.365405, 38.563835),
    Point(-121.363352, 38.566422)
]
multipoint = MultiPoint(multipoint_coords)
print(f'MultiPoint: MultiPoint with {len(multipoint_coords)} points')

# Create MultiPolygon geometry
poly1 = Polygon([
    (-121.433775, 38.544254),
    (-121.422917, 38.540376),
    (-121.424263, 38.547474),
    (-121.433775, 38.544254)
])
poly2 = Polygon([
    (-121.456113, 38.552220),
    (-121.459991, 38.541350),
    (-121.440053, 38.537820),
    (-121.440092, 38.548303),
    (-121.456113, 38.552220)
])
multipolygon = MultiPolygon([poly1, poly2])
print(f'MultiPolygon: MultiPolygon with 2 polygons')

# Create MultiLineString geometry
line1 = LineString([(-121.36, 38.56), (-121.35, 38.57)])
line2 = LineString([(-121.34, 38.55), (-121.33, 38.56)])
multilinestring = MultiLineString([line1, line2])
print(f'MultiLineString: MultiLineString with 2 lines')

# Demonstrate GeoSpatialUtil
print('\n--- GeoSpatialUtil Features ---')
gsu = GeoSpatialUtil(polygon)
print(f'GeoSpatialUtil shape type: {gsu.shapetype}')

# Convert to GeoJSON
geojson = polygon.__geo_interface__
print(f'GeoJSON type: {geojson["type"]}')
print(f'Coordinates count: {len(geojson["coordinates"][0])}')

# Create GeoSpatialCollection
print('\n--- GeoSpatialCollection ---')
shapes = [point, linestring, polygon]
collection = GeoSpatialCollection(shapes)
print(f'Collection contains {len(shapes)} shapes')
for i, shape in enumerate(shapes):
    print(f'  Shape {i+1}: {type(shape).__name__}')

# Demonstrate Collection geometry
geom_collection = Collection([point, linestring, polygon])
print(f'\nGeometry Collection: Collection')
print(f'Contains 3 geometries')

# Write and run the model
print('\n--- Running MODFLOW 6 Model ---')
sim.write_simulation()
success, _ = sim.run_simulation(silent=True)

if success:
    print('Model ran successfully!')
    
    # Read heads for spatial analysis
    head = gwf.output.head().get_data()
    print(f'Head array shape: {head.shape}')
    print(f'Min head: {head.min():.2f}, Max head: {head.max():.2f}')
    
    # Demonstrate how spatial features could be used with model
    print('\n--- Spatial Analysis Integration ---')
    print('Geometric features can be used to:')
    print('  - Define model boundaries from shapefiles')
    print('  - Extract model results at specific locations (points)')
    print('  - Create observation networks (multipoints)')
    print('  - Define river reaches (linestrings)')
    print('  - Delineate zones for parameter estimation (polygons)')
    print('  - Handle complex boundaries (polygons with holes)')
    print('  - Manage multi-part features (multipolygons, multilinestrings)')
else:
    print('Model failed to run')

print('\n=== Geospatial Utilities Demo Complete ===')