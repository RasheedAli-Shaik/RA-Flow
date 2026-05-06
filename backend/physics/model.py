from __future__ import annotations

import torch
from torch import nn


class SpectralConv3d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, modes: int) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.modes = modes
        scale = 1.0 / max(1, in_channels * out_channels)
        self.weights = nn.Parameter(
            scale
            * torch.randn(4, in_channels, out_channels, modes, modes, modes, dtype=torch.cfloat)
        )

    def compl_mul3d(self, inputs: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
        return torch.einsum("bixyz,ioxyz->boxyz", inputs, weights)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, _, size_x, size_y, size_z = x.shape
        x_ft = torch.fft.rfftn(x, dim=(-3, -2, -1))
        out_ft = torch.zeros(
            batch_size,
            self.out_channels,
            size_x,
            size_y,
            size_z // 2 + 1,
            dtype=torch.cfloat,
            device=x.device,
        )

        modes_x = min(self.modes, size_x)
        modes_y = min(self.modes, size_y)
        modes_z = min(self.modes, size_z // 2 + 1)

        out_ft[:, :, :modes_x, :modes_y, :modes_z] = self.compl_mul3d(
            x_ft[:, :, :modes_x, :modes_y, :modes_z],
            self.weights[0, :, :, :modes_x, :modes_y, :modes_z],
        )
        out_ft[:, :, -modes_x:, :modes_y, :modes_z] = self.compl_mul3d(
            x_ft[:, :, -modes_x:, :modes_y, :modes_z],
            self.weights[1, :, :, :modes_x, :modes_y, :modes_z],
        )
        out_ft[:, :, :modes_x, -modes_y:, :modes_z] = self.compl_mul3d(
            x_ft[:, :, :modes_x, -modes_y:, :modes_z],
            self.weights[2, :, :, :modes_x, :modes_y, :modes_z],
        )
        out_ft[:, :, -modes_x:, -modes_y:, :modes_z] = self.compl_mul3d(
            x_ft[:, :, -modes_x:, -modes_y:, :modes_z],
            self.weights[3, :, :, :modes_x, :modes_y, :modes_z],
        )
        return torch.fft.irfftn(out_ft, s=(size_x, size_y, size_z), dim=(-3, -2, -1))


class FNOBlock(nn.Module):
    def __init__(self, width: int, modes: int) -> None:
        super().__init__()
        self.spectral = SpectralConv3d(width, width, modes)
        self.pointwise = nn.Conv3d(width, width, kernel_size=1)
        self.norm = nn.InstanceNorm3d(width)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.spectral(x) + self.pointwise(x)
        x = self.norm(x)
        x = self.activation(x)
        return x + residual


class PhysicsNeMoSurrogate(nn.Module):
    def __init__(self, in_channels: int = 6, width: int = 24, modes: int = 10, depth: int = 4) -> None:
        super().__init__()
        torch.manual_seed(7)
        self.project_in = nn.Conv3d(in_channels, width, kernel_size=1)
        self.blocks = nn.ModuleList(FNOBlock(width, modes) for _ in range(depth))
        self.project_out = nn.Sequential(
            nn.Conv3d(width, width, kernel_size=1),
            nn.GELU(),
            nn.Conv3d(width, 4, kernel_size=1),
        )
        last = self.project_out[-1]
        if isinstance(last, nn.Conv3d):
            nn.init.zeros_(last.weight)
            nn.init.zeros_(last.bias)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        x = self.project_in(features)
        for block in self.blocks:
            x = block(x)
        return self.project_out(x)

