
# Example particle tracking visualization with FloPy plotting utilities

import matplotlib.pyplot as plt
import flopy
from flopy.plot.plotutil import to_mp7_pathlines, to_mp7_endpoints

# Load particle tracking results (after running MODPATH)
# pathlines = flopy.utils.PathlineFile("model.mppth").get_alldata()
# endpoints = flopy.utils.EndpointFile("model.mpend").get_alldata()

# Convert to standard format for plotting
# mp7_pathlines = to_mp7_pathlines(pathlines) 
# mp7_endpoints = to_mp7_endpoints(endpoints)

# Create visualization
# fig, ax = plt.subplots(figsize=(10, 8))

# Plot model grid
# modelmap = flopy.plot.PlotMapView(model=m, ax=ax)
# modelmap.plot_grid()

# Plot pathlines
# for particle_id in np.unique(mp7_pathlines['particleid']):
#     data = mp7_pathlines[mp7_pathlines['particleid'] == particle_id]
#     ax.plot(data['x'], data['y'], 'b-', alpha=0.7)

# Plot endpoints
# ax.scatter(mp7_endpoints['x'], mp7_endpoints['y'], c='red', s=50)

# plt.title("Particle Tracking Results")
# plt.xlabel("X Coordinate")
# plt.ylabel("Y Coordinate") 
# plt.show()
    