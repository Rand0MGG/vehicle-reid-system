import argparse
import os
import sys
from pathlib import Path

sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.services.model_profile_service import get_active_revision, get_public_profiles
from app.services.search_service import SearchService


def parse_args():
    parser = argparse.ArgumentParser(description="Run a local SearchService smoke test.")
    parser.add_argument(
        "--image",
        default="../datasets/gallery/0001_c001_20260124100000.jpg",
        help="Path to the query image, relative to backend/ by default.",
    )
    parser.add_argument("--profile-id", type=int, default=0, help="Explicit public model profile id to use.")
    parser.add_argument("--top-k", type=int, default=3, help="How many matches to print.")
    parser.add_argument(
        "--search-mode",
        choices=("fast", "pro"),
        default="fast",
        help="Feature view to use for the local search.",
    )
    parser.add_argument("--deep-thinking", action="store_true", help="Enable rerank-based sorting.")
    return parser.parse_args()


def resolve_revision(db, profile_id: int):
    profiles = get_public_profiles(db)
    if not profiles:
        raise RuntimeError("No public model profiles are available.")

    if profile_id:
        profile = next((item for item in profiles if int(item.id) == int(profile_id)), None)
        if profile is None:
            raise RuntimeError(f"Public model profile {profile_id} was not found.")
    else:
        profile = profiles[0]

    revision = get_active_revision(profile)
    if revision is None:
        raise RuntimeError(f"Profile {profile.name} does not have an active revision.")
    return profile, revision


def main():
    args = parse_args()
    print("Starting local vehicle search smoke test...")

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Missing query image: {image_path}")
        print("Pass --image with a real file path before retrying.")
        return 1

    db = SessionLocal()
    try:
        profile, revision = resolve_revision(db, args.profile_id)
        print(f"Using profile: {profile.name} (revision: {revision.revision_name})")
        print(f"Query image: {image_path.resolve()}")

        service = SearchService(db)
        payload = service.search(
            img_path=str(image_path),
            revision=revision,
            top_k=max(1, int(args.top_k)),
            search_mode=args.search_mode,
            deep_thinking=bool(args.deep_thinking),
        )

        results = payload["results"]
        print(
            f"\nSearch finished. Returned {len(results)} result(s); "
            f"feature_dim={payload['feature_dim']}, gallery_size={payload['gallery_size']}."
        )
        for index, item in enumerate(results, start=1):
            print(
                f"  [{index}] vehicle={item['vehicle_id']} "
                f"score={item['score']:.4f} cam={item['cam_id']} path={item['img_path']}"
            )
        return 0
    except Exception as exc:
        print(f"Local search smoke test failed: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
