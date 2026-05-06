from __future__ import annotations

import torch


def _central_difference(field: torch.Tensor, axis: int) -> torch.Tensor:
    padded = torch.nn.functional.pad(field, (1, 1, 1, 1, 1, 1), mode="replicate")
    if axis == 0:
        return (padded[:, :, 2:, 1:-1, 1:-1] - padded[:, :, :-2, 1:-1, 1:-1]) * 0.5
    if axis == 1:
        return (padded[:, :, 1:-1, 2:, 1:-1] - padded[:, :, 1:-1, :-2, 1:-1]) * 0.5
    return (padded[:, :, 1:-1, 1:-1, 2:] - padded[:, :, 1:-1, 1:-1, :-2]) * 0.5


def surface_normals_from_sdf(sdf: torch.Tensor) -> torch.Tensor:
    grad_x = _central_difference(sdf, 0)
    grad_y = _central_difference(sdf, 1)
    grad_z = _central_difference(sdf, 2)
    normals = torch.cat([grad_x, grad_y, grad_z], dim=1)
    return torch.nn.functional.normalize(normals, dim=1, eps=1e-6)


def _dominant_axis(wind: torch.Tensor) -> int:
    return int(torch.argmax(torch.abs(wind)).item())


def _axis_extent(mask: torch.Tensor, axis: int) -> torch.Tensor:
    sizes = mask.shape[1:]
    index = torch.arange(sizes[axis], device=mask.device)
    if axis == 0:
        presence = mask.any(dim=(2, 3))
    elif axis == 1:
        presence = mask.any(dim=(1, 3))
    else:
        presence = mask.any(dim=(1, 2))
    min_index = torch.where(presence, index.unsqueeze(0), torch.full_like(index.unsqueeze(0), sizes[axis])).amin(dim=1)
    max_index = torch.where(presence, index.unsqueeze(0), torch.zeros_like(index.unsqueeze(0))).amax(dim=1)
    extent = (max_index - min_index + 1).clamp_min(1).float() / max(sizes[axis], 1)
    return extent


def geometry_drag_factor(occupancy: torch.Tensor, wind: torch.Tensor) -> torch.Tensor:
    mask = occupancy[:, 0] > 0.15
    dominant_axis = _dominant_axis(wind)
    if dominant_axis == 0:
        projected = mask.any(dim=1).float()
        stream_extent = _axis_extent(mask, 0)
        lateral_a = _axis_extent(mask, 1)
        lateral_b = _axis_extent(mask, 2)
    elif dominant_axis == 1:
        projected = mask.any(dim=2).float()
        stream_extent = _axis_extent(mask, 1)
        lateral_a = _axis_extent(mask, 0)
        lateral_b = _axis_extent(mask, 2)
    else:
        projected = mask.any(dim=3).float()
        stream_extent = _axis_extent(mask, 2)
        lateral_a = _axis_extent(mask, 0)
        lateral_b = _axis_extent(mask, 1)

    projection_ratio = projected.mean(dim=(1, 2))
    blockage_ratio = (lateral_a * lateral_b).clamp_min(1e-4)
    slenderness = stream_extent / torch.sqrt(blockage_ratio)
    bluffness = torch.sqrt(blockage_ratio) / stream_extent.clamp_min(1e-4)
    factor = 1.0 + 2.8 * projection_ratio + 1.1 * blockage_ratio + 0.55 * bluffness + 0.2 / slenderness.clamp_min(0.2)
    return factor.view(-1, 1, 1, 1, 1)


def compute_drag_map(
    pressure: torch.Tensor,
    sdf: torch.Tensor,
    occupancy: torch.Tensor,
    wind: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    normals = surface_normals_from_sdf(sdf)
    wind_unit = torch.nn.functional.normalize(wind.view(1, 3, 1, 1, 1), dim=1, eps=1e-6)
    frontality = torch.relu(torch.sum(-normals * wind_unit, dim=1, keepdim=True))
    surface_band = torch.exp(-torch.abs(sdf) * 14.0) * (1.0 - occupancy)
    drag_map = pressure * frontality * surface_band
    drag_map = drag_map * geometry_drag_factor(occupancy, wind)
    drag_score = drag_map.sum(dim=(-3, -2, -1)).mean()
    return drag_map, drag_score
