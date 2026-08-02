import csv
import sys
import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ---------------------------------------------------------
# 1. Device Selection (AMD GPU / ROCm / CUDA / CPU)
# ---------------------------------------------------------
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[PyTorch Engine Active] Running on device: {device}")

# ---------------------------------------------------------
# 2. Domain & Physical Constants
# ---------------------------------------------------------
N = 160          # Grid resolution (160x160)
L = 10.0         # Spatial domain [-L, L]
steps = 240      # Micro-step iterations
fps = 30

x = torch.linspace(-L, L, N, device=device)
y = torch.linspace(-L, L, N, device=device)
dx = (x[1] - x[0]).item()
dy = (y[1] - y[0]).item()
Y, X = torch.meshgrid(y, x, indexing='ij')

c = 1.0
dt = 0.22 * dx / c
v_init = 0.50    # Approach velocity
m_sq = 1.44      # Mass potential term (stabilizes core against radial expansion)

# PyTorch 2D Convolutional Laplacian Kernel for 3-Component Vector
laplacian_kernel = torch.tensor([
    [0.0,  1.0, 0.0],
    [1.0, -4.0, 1.0],
    [0.0,  1.0, 0.0]
], device=device).unsqueeze(0).unsqueeze(0) / (dx**2)

kernel_3d = laplacian_kernel.repeat(3, 1, 1, 1)

# Edge Damping Mask
edge_mask = torch.exp(-((X/L)**8 + (Y/L)**8))
mask_3d = edge_mask.unsqueeze(0)

# ---------------------------------------------------------
# 3. Initialize Topologically Protected Skyrmions (S^2)
# ---------------------------------------------------------
def create_skyrmion(x0, y0, Q=1, phi0=0.0, R_core=1.2):
    r = torch.sqrt((X - x0)**2 + (Y - y0)**2) + 1e-6
    theta = torch.atan2(Y - y0, X - x0)
    
    # Profile function f(0)=pi, f(inf)=0
    f = 2.0 * torch.atan((R_core / r)**1.5)
    
    n1 = torch.sin(f) * torch.cos(Q * theta + phi0)
    n2 = torch.sin(f) * torch.sin(Q * theta + phi0)
    n3 = torch.cos(f)
    return torch.stack([n1, n2, n3], dim=0)

# Create two topological Skyrmion cores (Q = 1)
s1 = create_skyrmion(-3.5, -0.5, Q=1, phi0=0.0, R_core=1.2)
s2 = create_skyrmion(3.5, 0.5, Q=1, phi0=np.pi, R_core=1.2)

# Combined field normalized to S^2 unit sphere (|n| = 1)
n = s1 + s2
n[2, :, :] -= 1.0
norm = torch.sqrt(torch.sum(n**2, dim=0, keepdim=True))
n = n / norm

# Initial boost velocity d_t n = -v * d_x n
dn1_dx = (torch.roll(s1, -1, dims=2) - torch.roll(s1, 1, dims=2)) / (2 * dx)
dn2_dx = (torch.roll(s2, -1, dims=2) - torch.roll(s2, 1, dims=2)) / (2 * dx)

d_t_n = -v_init * dn1_dx + v_init * dn2_dx
n_old = n - dt * d_t_n
n_old = n_old / torch.sqrt(torch.sum(n_old**2, dim=0, keepdim=True))

# ---------------------------------------------------------
# 4. CSV Diagnostic Setup
# ---------------------------------------------------------
csv_filename = "skyrmion_pde_diagnostics.csv"
csv_file = open(csv_filename, mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["Step", "Time", "Peak_Energy_Density", "Integrated_Field_Energy"])

# ---------------------------------------------------------
# 5. Live Visualization Layout
# ---------------------------------------------------------
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(8, 7))
fig.suptitle("Topologically Stabilized Skyrmion PDE Collision Engine", 
             fontsize=12, fontweight='bold', color='#00d2ff')

im = ax.imshow(np.zeros((N, N)), extent=[-L, L, -L, L], cmap='magma', origin='lower', vmin=0, vmax=6.0)
cbar = fig.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label("Topological Energy Density E(x,y)", fontsize=9)

ax.set_xlabel("Substrate Axis X")
ax.set_ylabel("Substrate Axis Y")

text_overlay = ax.text(0.03, 0.88, '', transform=ax.transAxes, fontsize=9,
                       bbox=dict(boxstyle='round', facecolor='#1e1e1e', alpha=0.85, edgecolor='#00ff99'))

# ---------------------------------------------------------
# 6. PDE Integration Loop
# ---------------------------------------------------------
def step_pde():
    global n, n_old
    
    # 1. 3-Component Vector Laplacian via PyTorch Conv2d
    n_pad = F.pad(n.unsqueeze(0), (1,1,1,1), mode='replicate')
    lap = F.conv2d(n_pad, kernel_3d, groups=3).squeeze(0)
    
    # 2. Non-linear force with mass potential
    force = lap - m_sq * n
    
    # 3. Project force orthogonal to n (enforces S^2 constraint)
    n_dot_force = torch.sum(n * force, dim=0, keepdim=True)
    force_proj = force - n * n_dot_force
    
    # 4. Time Step Integration
    n_new = 2 * n - n_old + (dt**2) * force_proj
    
    # 5. Re-normalize to unit sphere |n| = 1
    norm = torch.sqrt(torch.sum(n_new**2, dim=0, keepdim=True))
    n_new = n_new / norm
    
    # 6. Apply boundary absorption
    n_new = n_new * mask_3d
    n_new[2, :, :] += (1.0 - mask_3d[0, :, :])
    
    # 7. Compute Energy Density
    dt_n = (n_new - n_old) / (2 * dt)
    dx_n = (torch.roll(n_new, -1, dims=2) - torch.roll(n_new, 1, dims=2)) / (2 * dx)
    dy_n = (torch.roll(n_new, -1, dims=1) - torch.roll(n_new, 1, dims=1)) / (2 * dy)
    
    E_density = 0.5 * torch.sum(dt_n**2 + dx_n**2 + dy_n**2, dim=0) + m_sq * (1.0 - n_new[2, :, :])
    
    n_old = n
    n = n_new
    
    return E_density

def animate(frame):
    for _ in range(2):
        E_tensor = step_pde()
        
    E_np = E_tensor.cpu().numpy()
    peak_E = float(torch.max(E_tensor).item())
    total_E = float(torch.sum(E_tensor).item() * dx * dy)
    
    csv_writer.writerow([frame * 2, round(frame * 2 * dt, 4), round(peak_E, 4), round(total_E, 4)])
    csv_file.flush()
    
    im.set_array(E_np)
    text_overlay.set_text(
        f"Step: {frame * 2}/{steps}\n"
        f"Device: {device}\n"
        f"Peak Energy Density: {peak_E:.3f}\n"
        f"Integrated Energy: {total_E:.3f}"
    )
    return [im]

# ---------------------------------------------------------
# 7. Render Animation
# ---------------------------------------------------------
plt.tight_layout()
anim = FuncAnimation(fig, animate, frames=int(steps//2), interval=1000/fps, blit=False, repeat=False)
plt.show()

csv_file.close()
print(f"[Done] Skyrmion PDE Execution Complete. Diagnostics saved to '{csv_filename}'.")