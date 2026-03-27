# Vehicle ReID System

➡️ **Jump to Chinese / 跳转到中文：** [中文 / Chinese](#中文--chinese)

## Executive Summary

Vehicle ReID System is an end-to-end **vehicle re-identification** demo system that combines:

- **Backend (FastAPI)** for authentication, gallery feature ingestion, and query-time retrieval APIs.
- **ReID inference engine** (bridged behind `reid_engine.extract_feature(...)`) for fixed-length feature extraction.
- **MySQL** as a feature store (image metadata + serialized feature vectors).
- **Frontend (Vue3 + Vite)** as a lightweight UI (UNSPECIFIED: exact UI implementation details depend on `frontend/` contents).
- **FastReID** vendored under `fastreid/` for training / evaluation and (optionally) inference.

It supports a practical workflow:

1. Put gallery images under `datasets/gallery/` using a naming convention.
2. Trigger gallery sync/rebuild → features are extracted and stored to MySQL.
3. Upload a query image → backend extracts feature → computes cosine similarity against DB features → returns ranked results including image URLs.

> **Status:** This project is under active development and not final (see the note at the end).

---

## System Architecture

```mermaid
flowchart LR
  U[User] -->|Browser| FE[Frontend (Vue3)]
  FE -->|HTTP| BE[Backend (FastAPI)]

  subgraph Backend
    AUTH[Auth API\nJWT]
    ADMIN[Admin API\nUsers/Logs/Config/Gallery]
    SEARCH[Search API\nUpload -> Top-K]
    SVC1[SearchService\nCosine similarity]
    SVC2[GalleryService\nScan & ingest gallery]
    STATIC[Static Server\n/static -> datasets/]
  end

  BE --> AUTH
  BE --> ADMIN
  BE --> SEARCH
  BE --> STATIC

  SEARCH --> SVC1
  ADMIN --> SVC2

  SVC1 --> ENGINE[ReID Engine\nreid_engine.extract_feature]
  SVC2 --> ENGINE

  SVC1 --> DB[(MySQL\nvehicle_feature/sys_user/sys_log)]
  SVC2 --> DB

  SVC2 --> FS[(datasets/gallery\nimages)]
  STATIC --> FS
```

---

## Repository Layout

> Paths are relative to the repo root.

| Path | What it contains | Notes |
|---|---|---|
| `backend/` | FastAPI service + business logic | Run dev server from this directory (recommended). |
| `backend/app/api/endpoints/` | HTTP endpoints | Includes `auth.py`, `search.py`, `admin_api.py`. |
| `backend/app/services/` | Core workflows | `search_service.py` and `gallery_service.py`. |
| `backend/app/db/` | DB init + SQLAlchemy session | `init.sql` creates tables; `session.py` connects using `SQLALCHEMY_DATABASE_URI`. |
| `backend/app/models/` | SQLAlchemy ORM models | `sys_user`, `vehicle_feature`, `sys_log`. |
| `backend/app/core/` | Backend config & security helpers | `config.example.py` must be copied to `config.py`. |
| `backend/app/engine/` | ReID inference bridge | Contains `predictor.py` (UNSPECIFIED: tool could not fetch file contents at generation time). |
| `configs/` | ReID model/training config | Provides `vehicle_reid.yml`. |
| `fastreid/` | FastReID source code | Vendored library used for training/eval and possibly inference. |
| `frontend/` | Web UI | Expected Vue3 + Vite (UNSPECIFIED: verify via `frontend/package.json`). |
| `requirements.txt` | Backend Python deps | Note: PyTorch/Detectron2 are not pinned here. |
| `check_env.py` | Environment checker | Imports `fastreid`, `detectron2`, checks CUDA availability. |

---

## Data Model and Storage

### Database schema

The backend expects a MySQL database named `vehicle_reid_db` with 3 core tables created by:

- `backend/app/db/init.sql`

```mermaid
erDiagram
  sys_user {
    INT id PK
    VARCHAR username "unique"
    VARCHAR password "hashed"
    VARCHAR role
    DATETIME create_time
  }

  vehicle_feature {
    INT id PK
    VARCHAR vehicle_id
    VARCHAR cam_id
    DATETIME capture_time
    VARCHAR img_path
    LONGBLOB feature "serialized float32 vector"
    DATETIME create_time
  }

  sys_log {
    INT id PK
    INT user_id "nullable"
    VARCHAR operation
    BOOLEAN status
    DATETIME exec_time
  }

  sys_user ||--o{ sys_log : "user_id (ondelete=SET NULL)"
```

### Feature format

- Features are stored as **raw bytes** via `vector_numpy.tobytes()` in `gallery_service.py`.
- Retrieval reconstructs vectors using `np.frombuffer(row.feature, dtype=np.float32)` in `search_service.py`.
- Similarity is computed as **cosine similarity** using L2-normalized dot products.

---

## Configuration

### Backend static configuration (`backend/app/core/config.py`)

A `config.py` file is required but **not committed**. Create it by copying `config.example.py`:

- Source template: `backend/app/core/config.example.py`
- Target: `backend/app/core/config.py`

Key options:

| Key | Default in example | Meaning |
|---|---:|---|
| `PROJECT_NAME` | `Vehicle ReID System` | FastAPI project title. |
| `API_V1_STR` | `/api/v1` | API prefix used by routers (UNSPECIFIED: confirm exact router mounting in `backend/main.py`). |
| `MODEL_CONFIG_FILE` | `../configs/vehicle_reid.yml` | ReID config YAML passed to the inference engine. |
| `MODEL_WEIGHTS_FILE` | `../outputs/model_final.pth` | ReID weights used for inference. **Note:** training config outputs to `./outputs/vehicle_reid/` by default, so you may need to update this path. |
| `DEVICE` | `cpu` | `cpu` or `cuda`. |
| `SQLALCHEMY_DATABASE_URI` | `mysql+pymysql://root:******@localhost:3306/vehicle_reid_db` | DB connection string. |

### Runtime (in-memory) admin configuration (`admin_api.py`)

`backend/app/api/endpoints/admin_api.py` defines a `dynamic_config` dictionary which can be read/updated via admin endpoints:

| Key | Default | Notes |
|---|---:|---|
| `model_device` | `cpu` | In-memory only. (UNSPECIFIED: whether it is actually applied to inference in current code.) |
| `similarity_threshold` | `0.5` | In-memory only. (UNSPECIFIED: whether applied in `SearchService`.) |
| `max_results` | `50` | In-memory only. (UNSPECIFIED: whether applied in `SearchService`.) |
| `log_level` | `INFO` | In-memory only. |

---

## Dataset Preparation

This repo uses the term “dataset” in **two different contexts**:

1. **Runtime gallery/query images** used by the web system.
2. **Training dataset** used by `fastreid/` for model training.

### Runtime gallery (for the web system)

Create the following structure under repo root:

```text
datasets/
  gallery/
    <vehicle_id>_<cam_id>_<YYYYmmddHHMMSS>.jpg
```

**Filename parsing rules** (implemented in `backend/app/services/gallery_service.py`):

- `vehicle_id` = first segment before `_`
- `cam_id` = second segment
- `capture_time`:
  - if a third segment exists and has **14 digits**, parsed as `%Y%m%d%H%M%S`
  - otherwise uses current time

Example:

- `0001_c001_20260124100000.jpg`

### Runtime query images

Query images can be anywhere (uploaded via API/UI). For local testing, you may optionally create:

```text
datasets/
  query/
    any_name.jpg
```

(UNSPECIFIED: whether `datasets/query/` is used by the frontend; backend accepts uploads directly via API.)

### Training dataset (FastReID)

The provided training config is `configs/vehicle_reid.yml` and sets:

- `DATASETS.NAMES=("veri",)`
- `HEADS.NUM_CLASSES=576`

This is commonly aligned with the VeRi-776 training split (576 training IDs). If you are using a different dataset, you must adjust dataset registration and config accordingly.

**UNSPECIFIED:** Exact dataset folder layout expected by the vendored `fastreid/` in this repo (verify `fastreid/data/datasets/` in your local checkout).

---

## Model Architecture

Model/training hyperparameters are defined in `configs/vehicle_reid.yml`.

The config describes a **Baseline** meta-architecture consisting of:

- **Backbone:** ResNet-50 (`DEPTH: 50x`), `LAST_STRIDE: 1`, optional IBN/SE disabled.
- **Head:** `EmbeddingHead`
  - Pooling: `GeneralizedMeanPooling`
  - Neck feature: `after`
  - Classification layer: `CircleSoftmax` (`SCALE: 64`, `MARGIN: 0.35`)
- Input size: `256 x 256` (train & test)
- Test metric: cosine similarity

```mermaid
flowchart LR
  IN[Input Image\n256x256] --> BB[Backbone\nResNet-50]
  BB --> POOL[Pooling\nGeM]
  POOL --> NECK[Neck\n(NECK_FEAT=after)]
  NECK --> EMB[Embedding Feature\n(embedding vector)]
  EMB -->|train only| CLS[CircleSoftmax\nclassification]
  EMB -->|inference| SIM[Cosine similarity\nSearchService]
```

---

## Installation

### Backend (FastAPI)

> Recommended: create a virtual environment.

```bash
git clone https://github.com/Rand0MGG/vehicle-reid-system.git
cd vehicle-reid-system

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
```

#### Deep Learning dependencies (required for inference/training)

`requirements.txt` does **not** pin the deep learning stack. You will likely need:

- PyTorch (CPU/CUDA build)
- TorchVision
- Detectron2 (required by FastReID in many setups)
- Any additional CUDA runtime libraries (if using GPU)

Run the checker:

```bash
python check_env.py
```

If `check_env.py` fails, install missing packages according to your platform.

**UNSPECIFIED:** Exact versions that are known-good for this repo. Align versions across PyTorch / CUDA / Detectron2.

### Database (MySQL 8.0 recommended)

1. Create schema & tables:

```bash
# Example on Linux/macOS:
mysql -u root -p < backend/app/db/init.sql
```

2. Create `backend/app/core/config.py` and set:

- `SQLALCHEMY_DATABASE_URI`

3. Create an admin account with a **bcrypt-hashed password**:

```bash
cd backend
python create_admin.py
```

Notes:
- `create_admin.py` creates `admin` with password `123456` (hashed).
- `backend/app/db/init.sql` inserts a default admin row (`admin / admin123`) **in plaintext**. That plaintext value will **not** pass bcrypt verification in `auth.py`. Prefer `create_admin.py` (or replace the SQL insert with a bcrypt hash).

### Frontend (Vue3 + Vite)

```bash
cd frontend
npm install
npm run dev
```

- Default dev port is commonly `5173` for Vite (UNSPECIFIED: confirm in your `frontend/` config).

---

## Training and Evaluation

Training is handled via the vendored `fastreid/` library and `configs/vehicle_reid.yml`.

### Train

A common FastReID training command looks like:

```bash
python fastreid/tools/train_net.py --config-file configs/vehicle_reid.yml
```

Expected outputs (typical FastReID behavior):

- Logs to stdout
- TensorBoard logs (if enabled)
- Checkpoints under the configured `OUTPUT_DIR` (from YAML):
  - `./outputs/vehicle_reid/`
  - final weights often saved as `model_final.pth`

**UNSPECIFIED:** The exact checkpoint naming and evaluation schedule in this repo’s `fastreid/` version.

### Evaluate (eval-only)

```bash
python fastreid/tools/train_net.py \
  --config-file configs/vehicle_reid.yml \
  --eval-only \
  MODEL.WEIGHTS ./outputs/vehicle_reid/model_final.pth
```

Common ReID metrics (depending on dataset/evaluator):

- mAP
- CMC Rank-1 / Rank-5 / Rank-10

**UNSPECIFIED:** Exact evaluator outputs without running the code on a configured dataset.

---

## Running the System

### Start backend API server

Run from `backend/` so imports like `from app...` resolve correctly:

```bash
cd backend

# Make sure backend/app/core/config.py exists and DB is reachable
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger UI (typical FastAPI): `http://localhost:8000/docs` (UNSPECIFIED: confirm in `backend/main.py` if docs are enabled/disabled).
- Static files are mounted under `/static` and served from `datasets/` (the backend uses this to expose gallery images by URL).

### Build the gallery feature database

There are two ways:

#### Option A: Admin API (recommended)

1) Upload gallery images into `datasets/gallery/`

2) Trigger rebuild:

- `POST /gallery/rebuild` (prefix may vary; see below)

You can also call:
- `POST /gallery/sync` (incremental)
- `POST /gallery/clear` (truncate table)
- `GET /gallery/status` (progress logs)
- `GET /gallery/stats` (counts)

**UNSPECIFIED:** The exact router prefix (e.g., `/api/v1/admin/...`) depends on how routers are included in `backend/main.py`.

#### Option B: Local script

```bash
cd backend
python reset_gallery.py
```

(UNSPECIFIED: the exact behavior of `reset_gallery.py` is determined by its implementation; verify if it calls the same ingestion pipeline.)

### Query search (Top-K)

The search API accepts:

- `file`: uploaded image (multipart form)
- `top_k`: integer form field, default 10

Typical request flow is:

```mermaid
sequenceDiagram
  participant C as Client
  participant A as Auth API
  participant S as Search API
  participant E as ReID Engine
  participant D as MySQL

  C->>A: POST /auth/login (username, password)
  A-->>C: {access_token, role}

  C->>S: POST /search (file, top_k, Bearer token)
  S->>E: extract_feature(query)
  S->>D: SELECT * FROM vehicle_feature
  S->>S: L2 normalize + cosine similarity + sort
  S-->>C: ranked results (img_url, score, metadata)
```

---

## API Examples and Expected Outputs

> Paths below assume `API_V1_STR=/api/v1` and common router prefixes. If your routing differs, treat these as **placeholders** and update accordingly.

### Login

`auth.py` uses `OAuth2PasswordRequestForm`, so the body must be `application/x-www-form-urlencoded`.

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=123456"
```

Example response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "admin"
}
```

### Search

```bash
TOKEN="REPLACE_WITH_ACCESS_TOKEN"

curl -X POST "http://127.0.0.1:8000/api/v1/search" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@../datasets/query/example.jpg" \
  -F "top_k=10"
```

Example response (shape matches `search.py`):

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "time_cost": 0.1532,
    "total_found": 3,
    "results": [
      {
        "vehicle_id": "0001",
        "cam_id": "c001",
        "capture_time": "2026-01-24T10:00:00",
        "img_path": "gallery/0001_c001_20260124100000.jpg",
        "img_url": "http://localhost:8000/static/gallery/0001_c001_20260124100000.jpg",
        "score": 0.9987
      }
    ]
  }
}
```

Notes:
- `img_url` is currently built using a **hardcoded** `http://localhost:8000` in `search_service.py`. If you deploy elsewhere, adjust the code accordingly.

### Admin: rebuild gallery

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/gallery/rebuild" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Admin: gallery status

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/admin/gallery/status" \
  -H "Authorization: Bearer ${TOKEN}"
```

Expected response shape:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "is_running": false,
    "logs": [
      "[12:01:03] 开始扫描底库目录: .../datasets/gallery",
      "[12:01:04] 发现 120 张图像，准备执行高维特征提取",
      "[12:01:05] 底层落盘成功 [1]: 0001_c001_20260124100000.jpg"
    ]
  }
}
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Most backend scripts assume you run from `backend/` so `app/` is on the Python path.

Fix:

```bash
cd backend
python create_admin.py
```

(or set `PYTHONPATH` accordingly.)

### Login fails even though `admin` exists

If the `sys_user.password` field stores plaintext (e.g., inserted by `init.sql`), bcrypt verification will fail.

Fix:
- Run `backend/create_admin.py` to create/update a bcrypt-hashed password, or
- Replace the SQL insert with a bcrypt hash.

### Search returns empty results

Reasons:
- Gallery table is empty (`vehicle_feature` has 0 rows).
- Gallery sync was not executed or failed.

Fix:
- Place images under `datasets/gallery/`
- Trigger gallery `rebuild` or run the local ingestion script
- Check `/gallery/status` logs and DB contents

### Image URLs in results are wrong

`SearchService` currently hardcodes:

- `http://localhost:8000/static/<img_path>`

If you run on another host/port, update the URL construction logic (UNSPECIFIED: no config key currently wired for this).

### `detectron2` / CUDA-related import errors

`check_env.py` imports `detectron2` and checks CUDA. If it fails:

- Install a compatible PyTorch build (CPU or matching your CUDA)
- Install Detectron2 for that PyTorch/CUDA combination
- Re-run `python check_env.py`

**UNSPECIFIED:** Exact versions are environment-dependent.

### Gallery sync is blocked with “is_running=true”

The gallery sync uses a global `sync_status`. If the process was interrupted, you may need to restart the backend service.

---

## Project Status

This repository is **under active development**. Interfaces, configuration keys, and module boundaries may change, and some items in this README are explicitly marked as **UNSPECIFIED** where the repo does not pin or fully define behavior. Please verify and refine as you iterate.

---

# 中文 / Chinese

➡️ **跳转到英文 / Jump to English：** [English](#vehicle-reid-system)

## 执行摘要

Vehicle ReID System 是一个端到端 **车辆重识别** 演示系统，组合了：

- **后端（FastAPI）**：提供认证、底库特征入库、查询检索 API。
- **ReID 推理引擎**（通过 `reid_engine.extract_feature(...)` 封装）：负责定长特征提取。
- **MySQL**：作为特征库（图像元数据 + 序列化特征向量）。
- **前端（Vue3 + Vite）**：提供轻量 UI（UNSPECIFIED：具体实现以 `frontend/` 实际内容为准）。
- **FastReID**：以源码形式放在 `fastreid/` 下，用于训练/评估，并可能用于推理。

系统支持的典型流程：

1. 将底库图片放到 `datasets/gallery/`，并遵循命名规范。
2. 触发底库同步/重建 → 提取特征并写入 MySQL。
3. 上传查询图片 → 后端提取特征 → 与 DB 中特征做余弦相似度排序 → 返回结果（含图片 URL）。

> **状态：** 本项目仍在持续开发中，尚未定稿（详见文末说明）。

---

## 系统架构

```mermaid
flowchart LR
  U[User] -->|Browser| FE[Frontend (Vue3)]
  FE -->|HTTP| BE[Backend (FastAPI)]

  subgraph Backend
    AUTH[Auth API\nJWT]
    ADMIN[Admin API\nUsers/Logs/Config/Gallery]
    SEARCH[Search API\nUpload -> Top-K]
    SVC1[SearchService\nCosine similarity]
    SVC2[GalleryService\nScan & ingest gallery]
    STATIC[Static Server\n/static -> datasets/]
  end

  BE --> AUTH
  BE --> ADMIN
  BE --> SEARCH
  BE --> STATIC

  SEARCH --> SVC1
  ADMIN --> SVC2

  SVC1 --> ENGINE[ReID Engine\nreid_engine.extract_feature]
  SVC2 --> ENGINE

  SVC1 --> DB[(MySQL\nvehicle_feature/sys_user/sys_log)]
  SVC2 --> DB

  SVC2 --> FS[(datasets/gallery\nimages)]
  STATIC --> FS
```

---

## 仓库结构

> 路径相对于仓库根目录。

| 路径 | 内容 | 说明 |
|---|---|---|
| `backend/` | FastAPI 服务与业务逻辑 | 推荐从该目录启动后端与运行脚本。 |
| `backend/app/api/endpoints/` | HTTP 接口实现 | 包含 `auth.py`、`search.py`、`admin_api.py`。 |
| `backend/app/services/` | 核心工作流 | `search_service.py` 与 `gallery_service.py`。 |
| `backend/app/db/` | 数据库初始化与连接 | `init.sql` 建表；`session.py` 使用 `SQLALCHEMY_DATABASE_URI` 连接。 |
| `backend/app/models/` | SQLAlchemy ORM 模型 | `sys_user`、`vehicle_feature`、`sys_log`。 |
| `backend/app/core/` | 后端配置与安全组件 | `config.example.py` 需要复制为 `config.py`。 |
| `backend/app/engine/` | ReID 推理桥接层 | 包含 `predictor.py`（UNSPECIFIED：生成时工具无法抓取该文件正文）。 |
| `configs/` | ReID 配置/训练配置 | 提供 `vehicle_reid.yml`。 |
| `fastreid/` | FastReID 源码 | 用于训练/评估，可能也用于推理。 |
| `frontend/` | Web UI | 预期为 Vue3 + Vite（UNSPECIFIED：以实际 `frontend/package.json` 为准）。 |
| `requirements.txt` | 后端 Python 依赖 | 注意：未固定 PyTorch/Detectron2 版本。 |
| `check_env.py` | 环境检查脚本 | 导入 `fastreid`/`detectron2` 并检查 CUDA。 |

---

## 数据模型与存储

### 数据库结构

后端默认使用 `vehicle_reid_db`，核心 3 张表由以下脚本创建：

- `backend/app/db/init.sql`

```mermaid
erDiagram
  sys_user {
    INT id PK
    VARCHAR username "unique"
    VARCHAR password "hashed"
    VARCHAR role
    DATETIME create_time
  }

  vehicle_feature {
    INT id PK
    VARCHAR vehicle_id
    VARCHAR cam_id
    DATETIME capture_time
    VARCHAR img_path
    LONGBLOB feature "serialized float32 vector"
    DATETIME create_time
  }

  sys_log {
    INT id PK
    INT user_id "nullable"
    VARCHAR operation
    BOOLEAN status
    DATETIME exec_time
  }

  sys_user ||--o{ sys_log : "user_id (ondelete=SET NULL)"
```

### 特征存储格式

- 入库时通过 `vector_numpy.tobytes()` 将特征序列化为原始字节（见 `gallery_service.py`）。
- 检索时通过 `np.frombuffer(row.feature, dtype=np.float32)` 还原为向量（见 `search_service.py`）。
- 相似度使用 **余弦相似度**，通过 L2 归一化后的点积计算。

---

## 配置说明

### 后端静态配置（`backend/app/core/config.py`）

仓库中没有提交 `config.py`，需要自行创建：

- 模板：`backend/app/core/config.example.py`
- 目标：`backend/app/core/config.py`

关键配置项：

| Key | 示例默认值 | 含义 |
|---|---:|---|
| `PROJECT_NAME` | `Vehicle ReID System` | FastAPI 项目标题。 |
| `API_V1_STR` | `/api/v1` | API 前缀（UNSPECIFIED：实际路由挂载方式以 `backend/main.py` 为准）。 |
| `MODEL_CONFIG_FILE` | `../configs/vehicle_reid.yml` | 推理引擎使用的配置 YAML。 |
| `MODEL_WEIGHTS_FILE` | `../outputs/model_final.pth` | 推理权重路径。**注意：**训练配置默认输出到 `./outputs/vehicle_reid/`，可能需要改路径或复制文件。 |
| `DEVICE` | `cpu` | `cpu` 或 `cuda`。 |
| `SQLALCHEMY_DATABASE_URI` | `mysql+pymysql://root:******@localhost:3306/vehicle_reid_db` | 数据库连接串。 |

### 运行时（内存）管理员配置（`admin_api.py`）

`backend/app/api/endpoints/admin_api.py` 中有 `dynamic_config`，支持通过管理员接口读取/更新：

| Key | 默认值 | 说明 |
|---|---:|---|
| `model_device` | `cpu` | 仅内存生效。（UNSPECIFIED：当前代码是否真正影响推理设备。） |
| `similarity_threshold` | `0.5` | 仅内存生效。（UNSPECIFIED：是否在 `SearchService` 中应用。） |
| `max_results` | `50` | 仅内存生效。（UNSPECIFIED：是否在 `SearchService` 中应用。） |
| `log_level` | `INFO` | 仅内存生效。 |

---

## 数据集准备

本仓库中的“dataset”有两类含义：

1. **系统运行时**的底库/查询图片数据。
2. **训练阶段**用于 FastReID 的训练数据集。

### 运行时底库（Web 系统使用）

在仓库根目录创建结构：

```text
datasets/
  gallery/
    <vehicle_id>_<cam_id>_<YYYYmmddHHMMSS>.jpg
```

**文件名解析规则**（见 `backend/app/services/gallery_service.py`）：

- `vehicle_id`：第 1 段（下划线 `_` 前）
- `cam_id`：第 2 段
- `capture_time`：
  - 若第 3 段存在且为 **14 位数字**，按 `%Y%m%d%H%M%S` 解析
  - 否则使用当前时间

示例：

- `0001_c001_20260124100000.jpg`

### 运行时查询图片

查询图片可放在任意位置（通过 API/UI 上传）。本地测试可选创建：

```text
datasets/
  query/
    any_name.jpg
```

（UNSPECIFIED：前端是否使用 `datasets/query/`；后端接口支持直接上传文件。）

### 训练数据集（FastReID）

训练配置为 `configs/vehicle_reid.yml`，其中设置：

- `DATASETS.NAMES=("veri",)`
- `HEADS.NUM_CLASSES=576`

这通常与 VeRi-776 的训练划分（576 个训练 ID）一致。如使用其它数据集，需要自行调整数据集注册与配置。

**UNSPECIFIED：**本仓库 `fastreid/` 版本对数据集目录结构的具体要求（请在本地查看 `fastreid/data/datasets/`）。

---

## 模型结构

模型/训练超参数在 `configs/vehicle_reid.yml` 中定义。

配置描述了一个 **Baseline** 架构，主要包括：

- **Backbone：**ResNet-50（`DEPTH: 50x`），`LAST_STRIDE: 1`，IBN/SE 关闭
- **Head：**`EmbeddingHead`
  - Pooling：`GeneralizedMeanPooling`
  - Neck feature：`after`
  - 分类层：`CircleSoftmax`（`SCALE: 64`，`MARGIN: 0.35`）
- 输入：训练/测试均为 `256 x 256`
- 测试相似度度量：cosine

```mermaid
flowchart LR
  IN[Input Image\n256x256] --> BB[Backbone\nResNet-50]
  BB --> POOL[Pooling\nGeM]
  POOL --> NECK[Neck\n(NECK_FEAT=after)]
  NECK --> EMB[Embedding Feature\n(embedding vector)]
  EMB -->|train only| CLS[CircleSoftmax\nclassification]
  EMB -->|inference| SIM[Cosine similarity\nSearchService]
```

---

## 安装部署

### 后端（FastAPI）

> 推荐创建虚拟环境。

```bash
git clone https://github.com/Rand0MGG/vehicle-reid-system.git
cd vehicle-reid-system

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
```

#### 深度学习依赖（推理/训练必需）

`requirements.txt` **未固定**深度学习栈版本，通常还需要：

- PyTorch（CPU 或 CUDA 版本）
- TorchVision
- Detectron2（很多 FastReID 环境需要）
- CUDA 运行库（如使用 GPU）

建议运行检查脚本：

```bash
python check_env.py
```

**UNSPECIFIED：**该仓库在某一套特定版本组合上的“已验证版本”。请确保 PyTorch/CUDA/Detectron2 相互兼容。

### 数据库（建议 MySQL 8.0）

1. 初始化表结构：

```bash
mysql -u root -p < backend/app/db/init.sql
```

2. 创建 `backend/app/core/config.py` 并配置：

- `SQLALCHEMY_DATABASE_URI`

3. 创建**bcrypt 哈希**的管理员账号：

```bash
cd backend
python create_admin.py
```

说明：
- `create_admin.py` 会创建 `admin`，密码为 `123456`（已哈希）。
- `backend/app/db/init.sql` 会插入 `admin / admin123`，但密码是**明文**，无法通过 `auth.py` 中的 bcrypt 校验。建议以 `create_admin.py` 为准（或将 SQL 插入改成 bcrypt 哈希）。

### 前端（Vue3 + Vite）

```bash
cd frontend
npm install
npm run dev
```

- Vite 常见默认端口为 `5173`（UNSPECIFIED：请以 `frontend/` 实际配置为准）。

---

## 训练与评估

训练/评估依赖 `fastreid/` 与 `configs/vehicle_reid.yml`。

### 训练

常见 FastReID 训练命令示例：

```bash
python fastreid/tools/train_net.py --config-file configs/vehicle_reid.yml
```

典型输出（FastReID 的常见行为）包括：

- 控制台训练日志
- TensorBoard 日志（如启用）
- Checkpoint 写入到 YAML 中的 `OUTPUT_DIR`：
  - `./outputs/vehicle_reid/`
  - 通常会生成 `model_final.pth`

**UNSPECIFIED：**不运行训练的前提下，无法确认该仓库 `fastreid/` 版本的 checkpoint 命名与评测触发策略。

### 评估（仅评估）

```bash
python fastreid/tools/train_net.py \
  --config-file configs/vehicle_reid.yml \
  --eval-only \
  MODEL.WEIGHTS ./outputs/vehicle_reid/model_final.pth
```

常见 ReID 评估指标（视数据集/评估器而定）：

- mAP
- CMC Rank-1 / Rank-5 / Rank-10

**UNSPECIFIED：**在未配置数据集并实际运行前，无法给出该仓库的确切输出格式。

---

## 系统运行

### 启动后端服务

建议从 `backend/` 目录启动，以保证 `from app...` 导入路径正确：

```bash
cd backend

# 确保 backend/app/core/config.py 已创建且数据库可连接
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger（FastAPI 常见）：`http://localhost:8000/docs`（UNSPECIFIED：以 `backend/main.py` 实际设置为准）。
- 静态资源通过 `/static` 挂载到 `datasets/`（用于返回底库图片 URL）。

### 构建底库特征库

两种方式：

#### 方式 A：管理员 API（推荐）

1) 将底库图片放到 `datasets/gallery/`

2) 触发重建：

- `POST /gallery/rebuild`（前缀可能不同，见下文）

也可调用：
- `POST /gallery/sync`（增量）
- `POST /gallery/clear`（清空表）
- `GET /gallery/status`（查看日志）
- `GET /gallery/stats`（统计）

**UNSPECIFIED：**具体路由前缀（例如 `/api/v1/admin/...`）取决于 `backend/main.py` 如何挂载 router。

#### 方式 B：本地脚本

```bash
cd backend
python reset_gallery.py
```

（UNSPECIFIED：`reset_gallery.py` 的确切逻辑以文件实现为准；请确认是否调用同一套入库管线。）

### 查询检索（Top-K）

检索接口参数：

- `file`：multipart 上传图片
- `top_k`：form 字段整数，默认 10

典型请求序列如下：

```mermaid
sequenceDiagram
  participant C as Client
  participant A as Auth API
  participant S as Search API
  participant E as ReID Engine
  participant D as MySQL

  C->>A: POST /auth/login (username, password)
  A-->>C: {access_token, role}

  C->>S: POST /search (file, top_k, Bearer token)
  S->>E: extract_feature(query)
  S->>D: SELECT * FROM vehicle_feature
  S->>S: L2 normalize + cosine similarity + sort
  S-->>C: ranked results (img_url, score, metadata)
```

---

## API 示例与预期输出

> 以下路径假设 `API_V1_STR=/api/v1` 且使用常见路由前缀。如果你的路由挂载不同，请将其视为**占位示例**并自行调整。

### 登录

`auth.py` 使用 `OAuth2PasswordRequestForm`，因此请求体必须是 `application/x-www-form-urlencoded`。

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=123456"
```

示例响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "admin"
}
```

### 检索

```bash
TOKEN="REPLACE_WITH_ACCESS_TOKEN"

curl -X POST "http://127.0.0.1:8000/api/v1/search" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@../datasets/query/example.jpg" \
  -F "top_k=10"
```

示例响应（形状与 `search.py` 一致）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "time_cost": 0.1532,
    "total_found": 3,
    "results": [
      {
        "vehicle_id": "0001",
        "cam_id": "c001",
        "capture_time": "2026-01-24T10:00:00",
        "img_path": "gallery/0001_c001_20260124100000.jpg",
        "img_url": "http://localhost:8000/static/gallery/0001_c001_20260124100000.jpg",
        "score": 0.9987
      }
    ]
  }
}
```

说明：
- `img_url` 目前在 `search_service.py` 里**硬编码**为 `http://localhost:8000`。如部署到其他地址/端口，需要修改代码。

### 管理员：重建底库

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/gallery/rebuild" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 管理员：查看底库状态

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/admin/gallery/status" \
  -H "Authorization: Bearer ${TOKEN}"
```

预期响应形状：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "is_running": false,
    "logs": [
      "[12:01:03] 开始扫描底库目录: .../datasets/gallery",
      "[12:01:04] 发现 120 张图像，准备执行高维特征提取",
      "[12:01:05] 底层落盘成功 [1]: 0001_c001_20260124100000.jpg"
    ]
  }
}
```

---

## 常见问题排查

### `ModuleNotFoundError: No module named 'app'`

多数后端脚本默认从 `backend/` 运行，使 `app/` 位于 Python 路径下。

修复：

```bash
cd backend
python create_admin.py
```

（或自行设置 `PYTHONPATH`。）

### `admin` 存在但仍无法登录

若 `sys_user.password` 是明文（例如来自 `init.sql` 的默认插入），bcrypt 校验必然失败。

修复：
- 运行 `backend/create_admin.py` 创建/更新 bcrypt 哈希密码，或
- 将 SQL 插入改为 bcrypt 哈希。

### 检索结果为空

原因可能包括：
- `vehicle_feature` 表为空
- 底库同步未执行或执行失败

修复：
- 将图片放到 `datasets/gallery/`
- 触发 `rebuild` 或运行本地入库脚本
- 查看 `/gallery/status` 日志与 MySQL 表内容

### 返回的图片 URL 不正确

`SearchService` 目前拼接：

- `http://localhost:8000/static/<img_path>`

若你的服务地址不同，需要修改 URL 构造（UNSPECIFIED：当前代码未提供已接入的配置项）。

### `detectron2` / CUDA 导入失败

`check_env.py` 会导入 `detectron2` 并检查 CUDA。失败时：

- 安装与你环境匹配的 PyTorch（CPU 或对应 CUDA）
- 安装与该 PyTorch/CUDA 匹配的 Detectron2
- 重新执行 `python check_env.py`

**UNSPECIFIED：**固定版本组合取决于你的平台与显卡环境。

### 底库同步提示 “is_running=true” 一直无法再触发

底库同步使用全局 `sync_status`。若进程异常中断，可能需要重启后端服务恢复状态。

---

## 项目状态说明

本仓库**仍处于持续开发中**。接口、配置项、模块边界可能调整；README 中对于仓库未固定/未完全定义的内容，已明确标注为 **UNSPECIFIED**，方便你在迭代过程中逐步补齐与修订。