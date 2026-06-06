import math
import pytest

from app.ar_math import Vec3, project_anchor_from_orientation, yaw_billboard_angle


def test_forward_projection_at_zero_orientation():
    point = project_anchor_from_orientation(alpha=0, beta=0, gamma=0, distance_m=5)
    assert point.x == pytest.approx(0)
    assert point.y == pytest.approx(0)
    assert point.z == pytest.approx(-5)


def test_pitch_projects_upward():
    point = project_anchor_from_orientation(alpha=0, beta=30, gamma=0, distance_m=2)
    assert point.y == pytest.approx(1.0)
    assert point.z < 0


def test_roll_projects_laterally():
    point = project_anchor_from_orientation(alpha=0, beta=0, gamma=90, distance_m=3)
    assert point.x == pytest.approx(-3)
    assert abs(point.z) < 1e-9


def test_yaw_billboard_angle_faces_camera():
    angle = yaw_billboard_angle(Vec3(1, 0, -1), Vec3(0, 0, 0))
    assert angle == pytest.approx(math.atan2(-1, 1))


def test_rejects_non_positive_distance():
    with pytest.raises(ValueError):
        project_anchor_from_orientation(0, 0, 0, 0)
