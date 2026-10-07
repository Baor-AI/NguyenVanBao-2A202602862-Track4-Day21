"""Topic A - CP3: Sweep yaw/pitch/roll/translation, đo mismatch.

Chạy:
    python src/perturb_experiment.py --data-root data/kitti_mini --frame 000011
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from starter.datasets import load_frame
from starter.projection import (perturb_extrinsic, project_velo_to_image,
                                 velo_to_cam, cam_to_image)


def count_points_in_box(uv, box2d):
    """Đếm số điểm rơi vào 2D box (x1, y1, x2, y2)."""
    if len(uv) == 0:
        return 0
    x1, y1, x2, y2 = box2d
    inside = (uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2)
    return int(inside.sum())


def evaluate(calib, points, image_shape, labels):
    """Chiếu điểm và đo 2 metric:
      - pct_in_fov: % điểm nằm trong ảnh
      - pct_in_2dbox: % điểm rơi vào 2D box của bất kỳ object nào
    """
    uv, depth, mask = project_velo_to_image(points, calib, image_shape)
    n_total = len(mask)
    n_in_fov = int(mask.sum())
    pct_in_fov = 100.0 * n_in_fov / max(n_total, 1)

    # Đếm điểm rơi vào 2D box (union)
    n_in_box = 0
    for obj in labels:
        n_in_box += count_points_in_box(uv, obj.bbox)
    pct_in_2dbox = 100.0 * n_in_box / max(n_total, 1)

    return {
        "n_points": n_total,
        "n_in_fov": n_in_fov,
        "pct_in_fov": pct_in_fov,
        "n_in_2dbox": n_in_box,
        "pct_in_2dbox": pct_in_2dbox,
        "n_objects": len(labels),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--frame", default="000011")
    ap.add_argument("--out-csv", default="results/yaw_perturb_sweep.csv")
    args = ap.parse_args()

    fr = load_frame(args.data_root, args.frame)
    print(f"Loaded {args.frame}: image={fr['image'].shape}, points={fr['points'].shape}, "
          f"labels={len(fr['labels'])}")

    # Các mức yaw cần sweep (độ)
    yaw_levels = [0.0, 0.5, 1.0, 2.0, 3.0]
    rows = []
    for yaw in yaw_levels:
        calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw)
        m = evaluate(calib, fr["points"], fr["image"].shape, fr["labels"])
        row = {"perturb_type": "yaw", "perturb_value": yaw, **m}
        rows.append(row)
        print(f"yaw={yaw:>4.1f}° | in_fov={m['pct_in_fov']:>5.2f}% | "
              f"in_2dbox={m['pct_in_2dbox']:>5.2f}% | points_in_box={m['n_in_2dbox']}")

    # Ghi CSV
    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nĐã ghi: {out}")


if __name__ == "__main__":
    main()
