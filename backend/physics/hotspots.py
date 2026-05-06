from __future__ import annotations

import torch

from backend.physics.drag import _central_difference


def compute_vorticity(velocity: torch.Tensor) -> torch.Tensor:
    vx = velocity[:, 0:1]
    vy = velocity[:, 1:2]
    vz = velocity[:, 2:3]
    dw_dy = _central_difference(vz, 1)
    dv_dz = _central_difference(vy, 2)
    du_dz = _central_difference(vx, 2)
    dw_dx = _central_difference(vz, 0)
    dv_dx = _central_difference(vy, 0)
    du_dy = _central_difference(vx, 1)
    curl_x = dw_dy - dv_dz
    curl_y = du_dz - dw_dx
    curl_z = dv_dx - du_dy
    return torch.sqrt(curl_x.square() + curl_y.square() + curl_z.square() + 1e-6)


def compute_hotspots(
    velocity: torch.Tensor,
    pressure: torch.Tensor,
    sdf: torch.Tensor,
    occupancy: torch.Tensor,
) -> torch.Tensor:
    pressure_grad = torch.sqrt(
        _central_difference(pressure, 0).square()
        + _central_difference(pressure, 1).square()
        + _central_difference(pressure, 2).square()
        + 1e-6
    )
    vorticity = compute_vorticity(velocity)
    surface_band = torch.exp(-torch.abs(sdf) * 12.0) * (1.0 - occupancy)
    combined = 0.6 * pressure_grad + 0.4 * vorticity
    combined = combined * surface_band
    peak = torch.amax(combined, dim=(-3, -2, -1), keepdim=True).clamp_min(1e-6)
    return combined / peak

