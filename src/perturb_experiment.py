"""Topic A - CP3: Sweep yaw, đo mismatch.

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
from starter.projection import perturb_extrinsic, project_velo_to_image


def count_points_in_box(uv, box2d):
    """Đếm số điểm rơi vào 1 box (x1, y1, x2, y2)."""
    if len(uv) == 0:
        return 0
    x1, y1, x2, y2 = box2d
    inside = (uv[:, 0] >= x1) & (uv[:, 0] <= x2) & (uv[:, 1] >= y1) & (uv[:, 1] <= y2)
    return int(inside.sum())


def evaluate(calib, points, image_shape, labels):
    """Đo 2 metric: % điểm trong FOV, % điểm trong 2D box."""
    uv, depth, mask = project_velo_to_image(points, calib, image_shape)
    n_total = len(mask)
    n_in_fov = int(mask.sum())
    pct_in_fov = 100.0 * n_in_fov / max(n_total, 1)

    n_in_box = sum(count_points_in_box(uv, obj.bbox) for obj in labels)
    pct_in_2dbox = 100.0 * n_in_box / max(n_total, 1)

    return {
        "n_points": n_total,
        "n_in_fov": n_in_fov,
        "pct_in_fov": round(pct_in_fov, 3),
        "n_in_2dbox": n_in_box,
        "pct_in_2dbox": round(pct_in_2dbox, 3),
        "n_objects": len(labels),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--frame", default="000011")
    ap.add_argument("--out-csv", default="results/yaw_perturb_sweep.csv")
    ap.add_argument("--perturb", choices=["yaw", "pitch", "roll", "tx", "ty", "tz"],
                    default="yaw")
    args = ap.parse_args()

    fr = load_frame(args.data_root, args.frame)
    print(f"Loaded {args.frame}: image={fr['image'].shape}, "
          f"points={fr['points'].shape}, labels={len(fr['labels'])}")

    # Các mức perturb
    if args.perturb == "yaw":
        levels = [0.0, 0.5, 1.0, 2.0, 3.0]
    elif args.perturb in ("pitch", "roll"):
        levels = [0.0, 0.5, 1.0, 2.0, 3.0]
    else:  # tx, ty, tz (mét)
        levels = [0.0, 0.02, 0.05, 0.10]

    rows = []
    for v in levels:
        if args.perturb == "yaw":
            calib = perturb_extrinsic(fr["calib"], yaw_deg=v)
        elif args.perturb == "pitch":
            calib = perturb_extrinsic(fr["calib"], pitch_deg=v)
        elif args.perturb == "roll":
            calib = perturb_extrinsic(fr["calib"], roll_deg=v)
        elif args.perturb == "tx":
            calib = perturb_extrinsic(fr["calib"], t_xyz_m=(v, 0, 0))
        elif args.perturb == "ty":
            calib = perturb_extrinsic(fr["calib"], t_xyz_m=(0, v, 0))
        elif args.perturb == "tz":
            calib = perturb_extrinsic(fr["calib"], t_xyz_m=(0, 0, v))

        m = evaluate(calib, fr["points"], fr["image"].shape, fr["labels"])
        row = {"perturb_type": args.perturb, "perturb_value": v, **m}
        rows.append(row)
        print(f"{args.perturb}={v:>5.2f} | in_fov={m['pct_in_fov']:>6.2f}% | "
              f"in_2dbox={m['pct_in_2dbox']:>6.2f}% | n_in_box={m['n_in_2dbox']}")

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
