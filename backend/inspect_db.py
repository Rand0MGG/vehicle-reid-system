import os
import sys

sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.model_profile import ModelProfile, ModelRevision
from app.models.user import User
from app.models.vehicle import GalleryFeature, GalleryImage


def inspect_data() -> None:
    session = SessionLocal()
    try:
        users = session.query(User).order_by(User.id.asc()).all()
        images = session.query(GalleryImage).order_by(GalleryImage.id.asc()).limit(20).all()
        profile_count = session.query(ModelProfile).count()
        revision_count = session.query(ModelRevision).count()
        feature_count = session.query(GalleryFeature).count()

        print("\nUsers")
        print("=" * 72)
        if not users:
            print("sys_user is empty.")
        for user in users:
            created = user.create_time.strftime("%Y-%m-%d %H:%M:%S") if user.create_time else "-"
            print(f"{user.id:<4} {user.username:<20} {user.role:<10} {created}")

        print("\nGallery")
        print("=" * 72)
        print(f"images={session.query(GalleryImage).count()} features={feature_count}")
        for image in images:
            vehicle_code = image.vehicle_identity.vehicle_code if image.vehicle_identity else "-"
            camera_code = image.camera.camera_code if image.camera else "-"
            print(f"{image.id:<4} {vehicle_code:<16} {camera_code:<10} {image.img_path}")

        print("\nModels")
        print("=" * 72)
        print(f"profiles={profile_count} revisions={revision_count}")
    except Exception as exc:
        print(f"Inspect failed: {exc}")
    finally:
        session.close()


if __name__ == "__main__":
    inspect_data()
