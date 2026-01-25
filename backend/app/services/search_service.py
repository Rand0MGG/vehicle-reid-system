# backend/app/services/search_service.py

import numpy as np
from sqlalchemy.orm import Session
from app.models.vehicle import VehicleFeature
from app.engine.predictor import reid_engine
from datetime import datetime

class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, img_path: str, top_k: int = 10):
        """
        主入口函数：像指挥官一样，只负责下令，不负责具体干活
        """
        # 1. 指挥 AI 引擎干活
        query_feat = self._extract_query_feature(img_path)

        # 2. 指挥 数据库 干活
        gallery_data = self._fetch_gallery_data()

        # 3. 指挥 CPU (Numpy) 干活
        results = self._calculate_similarity(query_feat, gallery_data)

        # 4. 格式化输出
        return results[:top_k]

    # --- 下面是具体的干活工人的逻辑 (私有方法) ---

    def _extract_query_feature(self, img_path):
        """步骤 1: 封装 AI 调用"""
        return reid_engine.extract_feature(img_path)

    def _fetch_gallery_data(self):
        """步骤 2: 封装数据库查询与解包"""
        # 从数据库取出所有记录
        # 注意：实际生产中如果数据量大，这里不能一次性取全表，但毕设几千张图没问题
        records = self.db.query(VehicleFeature).all()
        
        # 将 BLOB 还原为 Numpy 矩阵，同时保留 ID 信息
        features = []
        metadata = []
        for row in records:
            # 假设存储时是 float32 的 bytes
            feat_vec = np.frombuffer(row.feature, dtype=np.float32)
            features.append(feat_vec)
            metadata.append({
                "vehicle_id": row.vehicle_id,
                "cam_id": row.cam_id,
                "capture_time": row.capture_time,
                "img_path": row.img_path
            })
            
        return {"matrix": np.array(features), "meta": metadata}

    def _calculate_similarity(self, query_feat, gallery_data):
        """步骤 3 & 4: 封装数学计算与排序 (含归一化)"""
        gallery_matrix = gallery_data["matrix"]
        metadata = gallery_data["meta"]
        
        if len(gallery_matrix) == 0:
            return []

        # --- 【新增】 L2 归一化逻辑 ---
        # 1. 对查询向量归一化 (Query Normalization)
        # norm 计算向量长度，keepdims=True 保持维度以便相除
        query_norm = np.linalg.norm(query_feat)
        if query_norm > 0:
            query_feat = query_feat / query_norm

        # 2. 对底库矩阵归一化 (Gallery Normalization)
        # axis=1 表示按行计算每张图片的特征长度
        gallery_norm = np.linalg.norm(gallery_matrix, axis=1, keepdims=True)
        # 避免除以 0
        gallery_matrix = gallery_matrix / (gallery_norm + 1e-12)
        # ---------------------------

        # 矩阵乘法计算余弦相似度
        # 归一化后，点积 (Dot Product) 等价于余弦相似度 (Cosine Similarity)
        # 范围理论上在 [-1, 1] 之间
        sim_scores = np.dot(gallery_matrix, query_feat)

        # 获得排序后的索引 (从大到小)
        sorted_indices = np.argsort(sim_scores)[::-1]

        # 组装结果
        results = []
        for idx in sorted_indices:
            score = float(sim_scores[idx])
            info = metadata[idx]
            
            # --- 修改点：拼接图片 URL ---
            # 假设 img_path 是 "gallery/xxx.jpg"
            # 拼接后变成 "http://localhost:8000/static/gallery/xxx.jpg"
            # 注意：这里硬编码了 localhost，生产环境通常配置在 config.py 里，但在毕设里这样写没问题
            info["img_url"] = f"http://localhost:8000/static/{info['img_path']}"
            info["score"] = score 
            # -------------------------
            
            results.append(info)
            
        return results