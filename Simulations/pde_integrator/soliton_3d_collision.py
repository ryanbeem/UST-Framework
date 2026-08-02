import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ---------------------------------------------------------
# 1. Setup CSV Data Logger
# ---------------------------------------------------------
csv_filename = "soliton_collision_diagnostics.csv"
try:
    csv_file = open(csv_filename, mode='w', newline='')
    csv_writer = csv.writer(csv_file)
    # Header definition
    csv_writer.writerow([
        "Frame", "Time", 
        "X1", "Y1", "Z1", 
        "X2", "Y2", "Z2", 
        "Centroid_Distance", 
        "Peak_Energy_Density", 
        "Integrated_Slice_Energy", 
        "Action_Soliton_1", 
        "Action_Soliton_2", 
        "Total_Action", 
        "Collision_Phase_Stage"
    ])
    print(f"[Logger Initialized] Streaming simulation diagnostics to '{csv_filename}'...")
except Exception as e:
    print(f"[Error] Could not create CSV file: {e}")
    sys.exit(1)

# ---------------------------------------------------------
# 2. Simulation & Grid Parameters
# ---------------------------------------------------------
fps = 30
total_frames = 150

# Spatial grid (3D mid-plane slice)
grid_size = 80
x = np.linspace(-6, 6, grid_size)
y = np.linspace(-6, 6, grid_size)
dx = x[1] - x[0]
dy = y[1] - y[0]
X, Y = np.meshgrid(x, y)

# Physical constants
N_action = 2961  # Units of trapped phase action per particle
r_core = 1.2     # Soliton core torus radius
v0 = 0.08        # Approach velocity

# ---------------------------------------------------------
# 3. Kinematics & Energy Density Calculation
# ---------------------------------------------------------
def compute_positions(t):
    """
    Computes smooth, non-disjoint scattering trajectories for two colliding 
    3D Hopfion solitons based on non-linear substrate repulsion.
    """
    t0 = 50.0  # Impact center frame
    dt = t - t0
    
    # Smooth deflection offset building near impact point
    deflect_y = 0.8 * v0 * (12.0 * np.log(1.0 + np.exp(dt / 6.0)) - 12.0 * np.log(1.0 + np.exp(-t0 / 6.0)))
    deflect_x = -0.4 * v0 * (12.0 * np.log(1.0 + np.exp(dt / 6.0)) - 12.0 * np.log(1.0 + np.exp(-t0 / 6.0)))
    
    # Soliton 1 Trajectory
    x1 = -4.5 + v0 * t + deflect_x
    y1 = -0.8 + deflect_y
    z1 = 0.0
    
    # Soliton 2 Trajectory (Symmetric counter-rotor)
    x2 = -x1
    y2 = -y1
    z2 = 0.0
    
    return x1, y1, z1, x2, y2, z2

def compute_hopfion_energy_slice(x_c1, y_c1, x_c2, y_c2, t, col_phase):
    """Calculates mid-plane (z=0) hydrostatic energy density E(x,y)."""
    R1_sq = (X - x_c1)**2 + (Y - y_c1)**2
    R2_sq = (X - x_c2)**2 + (Y - y_c2)**2
    
    env1 = np.exp(-((np.sqrt(R1_sq) - r_core) / 0.6)**2)
    env2 = np.exp(-((np.sqrt(R2_sq) - r_core) / 0.6)**2)
    
    phase1 = np.sin(3.0 * np.arctan2(Y - y_c1, X - x_c1) - 1.5 * t)
    phase2 = np.sin(3.0 * np.arctan2(Y - y_c2, X - x_c2) - 1.5 * t + np.pi * col_phase)
    
    field1 = env1 * phase1
    field2 = env2 * phase2
    
    # Non-linear Skyrme field interaction term
    interaction = 1.8 * env1 * env2 * np.cos(3.0 * (X - x_c1) + 2.0 * t)
    total_energy = field1**2 + field2**2 + np.abs(interaction)
    return total_energy

# ---------------------------------------------------------
# 4. Matplotlib Dark-Theme Layout
# ---------------------------------------------------------
plt.style.use('dark_background')
fig = plt.figure(figsize=(14, 7))
fig.suptitle(r"UST 3D Soliton Collision: $N_1(2961) + N_2(2961) \to N_{\mathrm{total}}(5922)$ Action Budget", 
             fontsize=13, fontweight='bold', y=0.98)

# Left Panel: 3D Trajectory & Core Wireframes
ax3d = fig.add_subplot(1, 2, 1, projection='3d')
ax3d.set_xlim(-6, 6)
ax3d.set_ylim(-6, 6)
ax3d.set_zlim(-4, 4)

# Right Panel: Mid-Plane Phase Energy Density Heatmap (z = 0)
ax2d = fig.add_subplot(1, 2, 2)
ax2d.set_title(r"Mid-Plane Phase Energy Density $\mathcal{E}(x,y,z=0)$", fontsize=11, color='#00ff99', pad=10)
ax2d.set_xlabel("Substrate Axis X")
ax2d.set_ylabel("Substrate Axis Y")

im_slice = ax2d.imshow(np.zeros((grid_size, grid_size)), extent=[-6, 6, -6, 6], 
                       origin='lower', cmap='magma', vmin=0, vmax=3.8)
cbar = fig.colorbar(im_slice, ax=ax2d, shrink=0.8)
cbar.set_label("Hydrostatic Energy Density", fontsize=9)

# Dynamic Info Overlay Text
text_stats = ax2d.text(0.03, 0.78, '', transform=ax2d.transAxes, fontsize=8.8,
                       bbox=dict(boxstyle='round', facecolor='#1e1e1e', alpha=0.85, edgecolor='#00ff99'))

# ---------------------------------------------------------
# 5. Dynamic Animation & Logging Frame Loop
# ---------------------------------------------------------
def animate(frame):
    ax3d.clear()
    ax3d.set_xlim(-6, 6)
    ax3d.set_ylim(-6, 6)
    ax3d.set_zlim(-4, 4)
    ax3d.set_title("3D Topological Core Trajectories ($Q_H = 1 + Q_H = 1$)", fontsize=11, color='#00d2ff', pad=10)
    ax3d.set_xlabel("Substrate X")
    ax3d.set_ylabel("Substrate Y")
    ax3d.set_zlabel("Substrate Z")

    t = float(frame)
    x1, y1, z1, x2, y2, z2 = compute_positions(t)
    centroid_dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

    # Dynamic distance-based stage classification
    if centroid_dist > 3.2 and t < 50:
        stage_str = "1. Pre-Collision Approach"
        col_phase = 0.0
    elif centroid_dist <= 3.2:
        stage_str = "2. Resonant Overlap & Phase Interference"
        col_phase = (3.2 - centroid_dist) / 2.0
    else:
        stage_str = "3. Post-Scattering Trajectories"
        col_phase = 1.0

    # Field calculations & diagnostics
    E_slice = compute_hopfion_energy_slice(x1, y1, x2, y2, t * 0.1, col_phase)
    peak_energy = np.max(E_slice)
    integrated_energy = np.sum(E_slice) * dx * dy

    # Record frame row to CSV
    csv_writer.writerow([
        frame, round(t * 0.1, 3),
        round(x1, 4), round(y1, 4), round(z1, 4),
        round(x2, 4), round(y2, 4), round(z2, 4),
        round(centroid_dist, 4),
        round(peak_energy, 4),
        round(integrated_energy, 4),
        N_action, N_action, 2 * N_action,
        stage_str
    ])
    csv_file.flush()

    # Draw 3D Toroidal Core Wireframes
    theta = np.linspace(0, 2 * np.pi, 25)
    phi = np.linspace(0, 2 * np.pi, 12)
    TH, PH = np.meshgrid(theta, phi)

    # Soliton 1 Torus
    X1_3d = x1 + (r_core + 0.4 * np.cos(PH)) * np.cos(TH)
    Y1_3d = y1 + (r_core + 0.4 * np.cos(PH)) * np.sin(TH)
    Z1_3d = z1 + 0.4 * np.sin(PH)
    ax3d.plot_wireframe(X1_3d, Y1_3d, Z1_3d, color='#00d2ff', alpha=0.5, lw=0.8)

    # Soliton 2 Torus
    X2_3d = x2 + (r_core + 0.4 * np.cos(PH)) * np.cos(TH)
    Y2_3d = y2 + (r_core + 0.4 * np.cos(PH)) * np.sin(TH)
    Z2_3d = z2 + 0.4 * np.sin(PH)
    ax3d.plot_wireframe(X2_3d, Y2_3d, Z2_3d, color='#ff3366', alpha=0.5, lw=0.8)

    # Draw Centroid Points
    ax3d.scatter([x1], [y1], [z1], color='#00d2ff', s=50, label=r"Soliton 1 ($N_1 = 2961$)")
    ax3d.scatter([x2], [y2], [z2], color='#ff3366', s=50, label=r"Soliton 2 ($N_2 = 2961$)")
    ax3d.legend(loc='upper right', fontsize=8)

    # Update Heatmap
    im_slice.set_array(E_slice)

    # Update On-Screen Text Box
    text_stats.set_text(
        f"Frame: {frame}/{total_frames}\n" +
        f"Centroid Separation: {centroid_dist:.3f}\n" +
        f"Peak Energy Density: {peak_energy:.3f}\n" +
        f"Integrated Slice Energy: {integrated_energy:.3f}\n" +
        f"Total Action: {2*N_action} units\n" +
        f"Stage: {stage_str}"
    )

    return [im_slice]

# ---------------------------------------------------------
# 6. Execute Animation & Close Log
# ---------------------------------------------------------
plt.tight_layout()
anim = FuncAnimation(fig, animate, frames=total_frames, interval=1000/fps, blit=False, repeat=False)

plt.show()

# Flush and close CSV on exit
csv_file.close()
print(f"[Done] Complete simulation dataset saved to '{csv_filename}'.")