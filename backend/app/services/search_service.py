import numpy as np
from sqlalchemy.orm import Session

from app.engine.predictor import reid_engine
from app.models.vehicle import VehicleFeature


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, img_path: str, top_k: int = 10):
        query_feat = self._extract_query_feature(img_path)
        gallery_data = self._fetch_gallery_data()
        results = self._calculate_similarity(query_feat, gallery_data)
        return results[:top_k]

    def _extract_query_feature(self, img_path):
        return reid_engine.extract_feature(img_path)

    def _fetch_gallery_data(self):
        records = self.db.query(VehicleFeature).all()

        features = []
        metadata = []
        for row in records:
            feat_vec = np.frombuffer(row.feature, dtype=np.float32)
            features.append(feat_vec)
            metadata.append(
                {
                    "vehicle_id": row.vehicle_id,
                    "cam_id": row.cam_id,
                    "capture_time": row.capture_time,
                    "img_path": row.img_path,
                }
            )

        return {"matrix": np.array(features), "meta": metadata}

    def _calculate_similarity(self, query_feat, gallery_data):
        gallery_matrix = gallery_data["matrix"]
        metadata = gallery_data["meta"]

        if len(gallery_matrix) == 0:
            return []

        query_norm = np.linalg.norm(query_feat)
        if query_norm > 0:
            query_feat = query_feat / query_norm

        gallery_norm = np.linalg.norm(gallery_matrix, axis=1, keepdims=True)
        gallery_matrix = gallery_matrix / (gallery_norm + 1e-12)

        sim_scores = np.dot(gallery_matrix, query_feat)
        sorted_indices = np.argsort(sim_scores)[::-1]

        results = []
        for idx in sorted_indices:
            score = float(sim_scores[idx])
            info = metadata[idx]
            results.append(
                {
                    "vehicle_id": info["vehicle_id"],
                    "cam_id": info["cam_id"],
                    "capture_time": info["capture_time"],
                    "img_path": info["img_path"],
                    "img_url": f"/static/{info['img_path'].lstrip('/')}",
                    "score": score,
                }
            )

        return results
