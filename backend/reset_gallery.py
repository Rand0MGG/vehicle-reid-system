import os
import sys

from sqlalchemy import text

sys.path.append(os.getcwd())

from app.db.session import engine


TABLES = (
    "gallery_feature",
    "feature_build_task",
    "gallery_image",
    "camera",
    "vehicle_identity",
)


def reset_gallery_metadata() -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        try:
            for table in TABLES:
                conn.execute(text(f"TRUNCATE TABLE {table}"))
        finally:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    print("Gallery metadata has been cleared. Image files on disk were not deleted.")


if __name__ == "__main__":
    answer = input("This clears gallery image records and features, but not disk files. Continue? (y/n): ")
    if answer.strip().lower() == "y":
        reset_gallery_metadata()
    else:
        print("Cancelled.")
