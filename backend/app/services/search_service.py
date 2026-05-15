import time

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.engine.predictor import reid_engine
from app.models.model_profile import ModelRevision
from app.models.vehicle import GalleryFeature, GalleryImage
from fastreid.evaluation.rerank import re_ranking


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        img_path: str,
        revision: ModelRevision,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        search_mode: str = "fast",
        deep_thinking: bool = False,
        deep_thinking_candidate_limit_min: int = 100,
        deep_thinking_candidate_limit_max: int = 500,
        max_deep_thinking_gallery_size: int = 5000,
    ):
        total_started = time.perf_counter()
        normalized_mode = self._normalize_mode(search_mode)
        reid_engine.configure(profile=revision, eager=reid_engine.initialized)

        extract_started = time.perf_counter()
        query_feat = self._extract_query_feature(img_path, normalized_mode)
        extract_seconds = time.perf_counter() - extract_started

        load_started = time.perf_counter()
        gallery_data = self._fetch_gallery_data(
            revision=revision,
            search_mode=normalized_mode,
        )
        load_gallery_seconds = time.perf_counter() - load_started

        if gallery_data["matrix"].shape[0] == 0:
            raise ValueError("该模型还没有可检索的图库特征，请先在后台为该模型构建特征。")

        if deep_thinking and gallery_data["matrix"].shape[0] > int(max_deep_thinking_gallery_size):
            raise ValueError(
                f"深度思考最多支持 {int(max_deep_thinking_gallery_size)} 张候选图库图片，"
                f"当前有 {gallery_data['matrix'].shape[0]} 张。"
            )

        results = self._calculate_similarity(
            query_feat,
            gallery_data,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            deep_thinking=deep_thinking,
            deep_thinking_candidate_limit_min=deep_thinking_candidate_limit_min,
            deep_thinking_candidate_limit_max=deep_thinking_candidate_limit_max,
        )
        deep_thinking_used = bool(deep_thinking and results["rerank_candidate_count"] > 0)
        timings = {
            "feature_extract_seconds": round(extract_seconds, 4),
            "load_gallery_seconds": round(load_gallery_seconds, 4),
            "similarity_seconds": round(results["timings"].get("similarity_seconds", 0.0), 4),
            "rerank_seconds": round(results["timings"].get("rerank_seconds", 0.0), 4),
            "total_seconds": round(time.perf_counter() - total_started, 4),
        }

        return {
            "results": results["items"][:top_k],
            "feature_dim": int(query_feat.size),
            "gallery_size": int(gallery_data["total_count"]),
            "rerank_candidate_count": int(results["rerank_candidate_count"]),
            "deep_thinking_used": deep_thinking_used,
            "sort_basis": "rerank_distance" if deep_thinking_used else "similarity",
            "timings": timings,
        }

    def _normalize_mode(self, search_mode: str) -> str:
        normalized_mode = str(search_mode or "fast").strip().lower()
        if normalized_mode not in {"fast", "pro"}:
            raise ValueError("search_mode 只能是 fast 或 pro。")
        return normalized_mode

    def _extract_query_feature(self, img_path: str, search_mode: str) -> np.ndarray:
        return reid_engine.extract_feature(img_path, search_mode=search_mode)

    def _fetch_gallery_data(
        self,
        revision: ModelRevision,
        search_mode: str,
    ):
        expected_full_dim = int(revision.full_feature_dim)
        expected_view_dim = int(revision.global_feature_dim if search_mode == "fast" else revision.full_feature_dim)
        total_count = (
            self.db.query(func.count(GalleryFeature.id))
            .filter(GalleryFeature.model_revision_id == revision.id)
            .scalar()
            or 0
        )

        query = (
            self.db.query(GalleryFeature)
            .join(GalleryImage, GalleryFeature.image_id == GalleryImage.id)
            .options(
                joinedload(GalleryFeature.image).joinedload(GalleryImage.vehicle_identity),
                joinedload(GalleryFeature.image).joinedload(GalleryImage.camera),
            )
            .filter(GalleryFeature.model_revision_id == revision.id)
        )

        records = query.order_by(GalleryFeature.id.asc()).all()

        features = []
        metadata = []
        for row in records:
            full_vec = np.frombuffer(row.feature, dtype=np.float32)
            if full_vec.size != expected_full_dim:
                raise ValueError(
                    f"图库特征维度为 {full_vec.size}，但模型版本期望 {expected_full_dim}。请重新构建该模型的图库特征。"
                )

            view_vec = full_vec[:expected_view_dim] if search_mode == "fast" else full_vec
            if view_vec.size != expected_view_dim:
                raise ValueError("图库特征视图维度与查询模式不一致，请重新构建该模型的图库特征。")

            image = row.image
            features.append(view_vec.astype(np.float32, copy=False))
            metadata.append(
                {
                    "image_id": image.id,
                    "vehicle_id": image.vehicle_id,
                    "cam_id": image.cam_id,
                    "capture_time": image.capture_time,
                    "img_path": image.img_path,
                }
            )

        matrix = np.vstack(features) if features else np.empty((0, expected_view_dim), dtype=np.float32)
        return {"matrix": matrix, "meta": metadata, "total_count": int(total_count)}

    def _calculate_similarity(
        self,
        query_feat: np.ndarray,
        gallery_data,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        deep_thinking: bool = False,
        deep_thinking_candidate_limit_min: int = 100,
        deep_thinking_candidate_limit_max: int = 500,
    ):
        gallery_matrix = gallery_data["matrix"]
        metadata = gallery_data["meta"]
        timings = {"similarity_seconds": 0.0, "rerank_seconds": 0.0}

        if gallery_matrix.shape[1] != query_feat.size:
            raise ValueError(f"查询特征维度 {query_feat.size} 与图库特征维度 {gallery_matrix.shape[1]} 不一致。")

        similarity_started = time.perf_counter()
        query_feat = self._normalize_vector(query_feat)
        gallery_matrix = self._normalize_matrix(gallery_matrix)
        sim_scores = np.dot(gallery_matrix, query_feat)
        sorted_indices = np.argsort(sim_scores)[::-1]
        timings["similarity_seconds"] = time.perf_counter() - similarity_started

        rerank_distances = None
        rerank_candidate_count = 0
        if deep_thinking:
            rerank_started = time.perf_counter()
            rerank_candidate_count = self._resolve_rerank_candidate_count(
                gallery_size=gallery_matrix.shape[0],
                top_k=top_k,
                min_limit=deep_thinking_candidate_limit_min,
                max_limit=deep_thinking_candidate_limit_max,
            )
            candidate_indices = sorted_indices[:rerank_candidate_count]
            candidate_matrix = gallery_matrix[candidate_indices]
            candidate_distances = self._calculate_rerank_distances(query_feat, candidate_matrix)
            rerank_distances = np.full(gallery_matrix.shape[0], np.nan, dtype=np.float32)
            rerank_distances[candidate_indices] = candidate_distances
            sorted_indices = candidate_indices[np.argsort(candidate_distances)]
            timings["rerank_seconds"] = time.perf_counter() - rerank_started

        results = []
        for idx in sorted_indices:
            score = float(sim_scores[idx])
            if score < similarity_threshold:
                continue

            info = metadata[idx]
            item = {
                "image_id": info["image_id"],
                "vehicle_id": info["vehicle_id"],
                "cam_id": info["cam_id"],
                "capture_time": info["capture_time"],
                "img_path": info["img_path"],
                "img_url": f"/api/v1/gallery/images/{info['image_id']}/file",
                "score": score,
            }
            if rerank_distances is not None:
                item["rerank_distance"] = float(rerank_distances[idx])
            results.append(item)

        return {"items": results, "rerank_candidate_count": rerank_candidate_count, "timings": timings}

    def _resolve_rerank_candidate_count(self, gallery_size: int, top_k: int, min_limit: int, max_limit: int) -> int:
        gallery_size = max(0, int(gallery_size))
        if gallery_size == 0:
            return 0
        safe_top_k = max(1, int(top_k or 1))
        safe_min = max(1, int(min_limit or 100))
        safe_max = max(safe_min, int(max_limit or safe_min))
        target_count = min(max(safe_top_k * 5, safe_min), safe_max)
        target_count = max(safe_top_k, target_count)
        return min(gallery_size, target_count)

    def _calculate_rerank_distances(self, query_feat: np.ndarray, gallery_matrix: np.ndarray) -> np.ndarray:
        query_matrix = query_feat.reshape(1, -1)
        q_g_dist = np.maximum(0.0, 1.0 - np.dot(query_matrix, gallery_matrix.T)).astype(np.float32)
        q_q_dist = np.zeros((1, 1), dtype=np.float32)
        g_g_dist = np.maximum(0.0, 1.0 - np.dot(gallery_matrix, gallery_matrix.T)).astype(np.float32)
        max_distance = max(
            float(q_g_dist.max()) if q_g_dist.size else 0.0,
            float(g_g_dist.max()) if g_g_dist.size else 0.0,
        )
        if max_distance == 0.0:
            q_g_dist = q_g_dist + 1e-12
            g_g_dist = g_g_dist + 1e-12
        return re_ranking(q_g_dist, q_q_dist, g_g_dist).reshape(-1)

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm <= 0:
            return vector.astype(np.float32, copy=False)
        return (vector / norm).astype(np.float32, copy=False)

    def _normalize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return (matrix / (norms + 1e-12)).astype(np.float32, copy=False)
