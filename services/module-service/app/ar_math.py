from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float


def deg_to_rad(value: float) -> float:
    return value * math.pi / 180.0


def project_anchor_from_orientation(alpha: float, beta: float, gamma: float, distance_m: float) -> Vec3:
    """Project a reticle tap into local ENU-ish coordinates using the WebAR 3DOF+ approximation.

    alpha is yaw/azimuth, beta pitch, gamma roll in degrees. The simplified anchor equation
    is intentionally independent of alpha for the local reticle vector, matching the Phase 5
    spatial-memory baseline: x=-d*sin(gamma)*cos(beta), y=d*sin(beta), z=-d*cos(gamma)*cos(beta).
    """
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")
    beta_r = deg_to_rad(beta)
    gamma_r = deg_to_rad(gamma)
    return Vec3(
        x=-distance_m * math.sin(gamma_r) * math.cos(beta_r),
        y=distance_m * math.sin(beta_r),
        z=-distance_m * math.cos(gamma_r) * math.cos(beta_r),
    )


def yaw_billboard_angle(anchor: Vec3, camera: Vec3 | None = None) -> float:
    camera = camera or Vec3(0, 0, 0)
    return math.atan2(camera.x - anchor.x, camera.z - anchor.z)
