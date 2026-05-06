from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh


@dataclass(slots=True)
class ShapeProposal:
    mesh: trimesh.Trimesh
    score_hint: float
    label: str


class DiffusionShapeStub:
    """A lightweight placeholder for future latent shape generation.

    The current implementation emits smooth stochastic variants that can be
    ranked by the optimization engine or a future learned prior.
    """

    def __init__(self, seed: int = 11) -> None:
        self.rng = np.random.default_rng(seed)

    def propose(self, mesh: trimesh.Trimesh, proposals: int = 3) -> list[ShapeProposal]:
        candidates: list[ShapeProposal] = []
        for index in range(proposals):
            candidate = mesh.copy()
            jitter = self.rng.normal(0.0, 0.008 + index * 0.002, size=candidate.vertices.shape)
            candidate.vertices = candidate.vertices + jitter
            trimesh.smoothing.filter_laplacian(candidate, lamb=0.24, iterations=2 + index)
            candidates.append(
                ShapeProposal(
                    mesh=candidate,
                    score_hint=float(1.0 - 0.1 * index),
                    label=f"diffusion-proposal-{index + 1}",
                )
            )
        return candidates


diffusion_shape_stub = DiffusionShapeStub()
