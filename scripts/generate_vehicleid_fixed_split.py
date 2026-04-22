#!/usr/bin/env python
# encoding: utf-8
"""Generate deterministic VehicleID query/gallery split files."""

import argparse
import random
from collections import defaultdict
from pathlib import Path


SPLITS = [
    ("test_list_800.txt", "test_list_800_query.txt", "test_list_800_gallery.txt"),
    ("test_list_1600.txt", "test_list_1600_query.txt", "test_list_1600_gallery.txt"),
    ("test_list_2400.txt", "test_list_2400_query.txt", "test_list_2400_gallery.txt"),
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", default="datasets/vehicleid", help="Path to VehicleID dataset root.")
    parser.add_argument("--seed", type=int, default=5, help="Seed used to create the fixed split.")
    parser.add_argument(
        "--output-dir",
        default="train_test_split/fixed_split_seed5",
        help="Output directory, relative to dataset root unless absolute.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing split files.")
    return parser.parse_args()


def read_list(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        imgid, vid = line.split()[:2]
        rows.append((imgid, vid))
    return rows


def build_fixed_split(rows, rng):
    shuffled = list(rows)
    rng.shuffle(shuffled)

    seen = set()
    query = []
    gallery = []
    for imgid, vid in shuffled:
        if vid in seen:
            query.append((imgid, vid))
        else:
            seen.add(vid)
            gallery.append((imgid, vid))

    return query, gallery


def write_list(path, rows, force=False):
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Pass --force to overwrite it.")
    path.write_text("".join(f"{imgid} {vid}\n" for imgid, vid in rows), encoding="utf-8")


def validate_split(source_rows, query, gallery):
    source_by_id = defaultdict(int)
    gallery_by_id = defaultdict(int)
    query_by_id = defaultdict(int)

    for _, vid in source_rows:
        source_by_id[vid] += 1
    for _, vid in gallery:
        gallery_by_id[vid] += 1
    for _, vid in query:
        query_by_id[vid] += 1

    if len(query) + len(gallery) != len(source_rows):
        raise ValueError("query + gallery size does not match source size")
    if any(count != 1 for count in gallery_by_id.values()):
        raise ValueError("each gallery identity must appear exactly once")
    if set(gallery_by_id) != set(source_by_id):
        raise ValueError("gallery identities do not match source identities")
    for vid, count in source_by_id.items():
        if query_by_id[vid] + gallery_by_id[vid] != count:
            raise ValueError(f"identity {vid} has inconsistent split count")


def main():
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    split_root = dataset_root / "train_test_split"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = dataset_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    print(f"VehicleID root: {dataset_root}")
    print(f"Output dir: {output_dir}")
    print(f"Seed: {args.seed}")

    for source_name, query_name, gallery_name in SPLITS:
        source_path = split_root / source_name
        source_rows = read_list(source_path)
        query, gallery = build_fixed_split(source_rows, rng)
        validate_split(source_rows, query, gallery)

        query_path = output_dir / query_name
        gallery_path = output_dir / gallery_name
        write_list(query_path, query, force=args.force)
        write_list(gallery_path, gallery, force=args.force)

        print(
            f"{source_name}: total={len(source_rows)} query={len(query)} gallery={len(gallery)} "
            f"ids={len(gallery)}"
        )


if __name__ == "__main__":
    main()
