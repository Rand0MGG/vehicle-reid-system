# Vehicle ReID System

<p align="center">
  <strong>Full-stack vehicle re-identification search and admin console</strong>
</p>

<p align="center">
  <strong>Current release: v1.0.0</strong> · <a href="#english">English</a> · <a href="#中文--chinese">中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-2f5f8f?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Backend-0f766e?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue_3-Frontend-42b883?style=for-the-badge&logo=vue.js&logoColor=white" alt="Vue 3">
  <img src="https://img.shields.io/badge/MySQL-Feature_Store-4479a1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/FastReID-ReID_Engine-c96442?style=for-the-badge" alt="FastReID">
</p>

Vehicle ReID System turns a folder of gallery vehicle images into searchable feature vectors, then lets users upload a query image and retrieve visually similar vehicles. The v1.0.0 admin console also manages users, models, gallery processing, runtime parameters, monitoring, and audit logs.

<p align="center">
  <img src="media/前台_检索效果.png" alt="Vehicle ReID search result preview" width="92%">
</p>

## English

## Product Preview

| Login | Search Home |
|---|---|
| ![Login](media/前台_登录.png) | ![Search Home](media/前台_主界面.png) |

| Search Results | System Settings |
|---|---|
| ![Search Results](media/前台_检索效果.png) | ![System Settings](media/后台_系统设置.png) |

| Gallery Processing | Runtime Monitor |
|---|---|
| ![Gallery Processing](media/后台_图库处理.png) | ![Runtime Monitor](media/后台_运行监控.png) |

| Audit Logs | User & Role Management |
|---|---|
| ![Audit Logs](media/后台_操作日志.png) | ![User Management](media/后台_账号权限.png) |

## What It Does

- Authenticates users with JWT and role-based admin access.
- Scans `datasets/gallery/`, extracts ReID features, and stores image metadata plus serialized feature vectors in MySQL.
- Searches uploaded query images with feature extraction, cosine similarity, `similarity_threshold`, and a capped Top-K result count.
- Blocks unsafe search when gallery features were produced by an unknown model or by a model that differs from the current inference model.
- Provides an admin console for user editing, builtin-account protection, model switching, runtime config, gallery rebuild/sync/clear, opening the gallery folder, monitoring, and audit logs.
- Persists runtime configuration through `backend/app/core/system_config.py`.

## Architecture

```mermaid
flowchart LR
  User["User / Admin"] --> Browser["Vue 3 + Element Plus UI"]
  Browser -->|"HTTP / Bearer Token"| API["FastAPI Backend"]

  subgraph Backend["Backend Services"]
    Auth["Auth API<br/>login / logout"]
    Admin["Admin API<br/>users, config, models, gallery, logs"]
    Search["Search API<br/>query upload and retrieval"]
    Static["Static Files<br/>/static -> datasets/"]
  end

  API --> Auth
  API --> Admin
  API --> Search
  API --> Static

  Search --> SearchService["SearchService<br/>threshold + cosine ranking"]
  Admin --> GalleryService["GalleryService<br/>scan, ingest, rebuild"]
  SearchService --> Engine["ReID Engine<br/>FastReID predictor"]
  GalleryService --> Engine
  SearchService --> DB[("MySQL<br/>sys_user / sys_log / vehicle_feature")]
  GalleryService --> DB
  GalleryService --> Gallery[("datasets/gallery<br/>runtime gallery images")]
  Static --> Gallery
  Engine --> Models[("outputs/<br/>model weights")]
  Engine --> Configs[("configs/<br/>ReID config")]
```

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Rand0MGG/vehicle-reid-system.git
cd vehicle-reid-system
```

### 2. Create the Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install the PyTorch, CUDA, and Detectron2 stack that matches your machine if your environment does not already provide it. You can then run the local environment check:

```powershell
python check_env.py
```

### 3. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set at least:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:password@localhost:3306/vehicle_reid_db
ALLOWED_ORIGINS=http://localhost:5173
VITE_API_BASE_URL=/api/v1
VITE_DEV_PROXY_TARGET=http://localhost:8000
```

### 4. Initialize MySQL

```powershell
mysql -u root -p < backend/app/db/init.sql
```

The bootstrap script creates `vehicle_reid_db`, `sys_user`, `vehicle_feature`, and `sys_log`, then inserts the builtin admin account. Change the default admin password immediately after first login.

### 5. Start the backend

```powershell
cd backend
python main.py
```

The backend serves API routes under `/api/v1` and exposes runtime gallery files through the mounted `/static` route.

### 6. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite dev URL, log in with the builtin admin account, and switch to the admin console when you need model, gallery, config, user, or log management.

### 7. Build the gallery and search

Place gallery images in `datasets/gallery/`, then use `Admin Console -> Gallery Processing` to process new images or rebuild the full gallery. Recommended gallery filename format:

```text
vehicleId_cameraId_YYYYMMDDHHMMSS.jpg
```

If the filename does not match the pattern, the backend still ingests the image and falls back to `unknown` metadata where needed. After gallery processing completes, upload a query image from the search page and adjust `similarity_threshold` / Top-K from system settings when needed.

## Project Structure

```text
vehicle-reid-system/
|-- backend/                 FastAPI entrypoint, API routes, services, DB access, startup migrations
|-- frontend/                Vue 3 + Vite + Element Plus admin/search UI
|-- configs/                 ReID configuration files, including vehicle_reid.yml
|-- fastreid/                FastReID source integration
|-- media/                   README screenshots and GitHub presentation assets
|-- datasets/gallery/        Runtime gallery image folder
|-- outputs/                 Runtime/model artifacts such as checkpoint weights
|-- tmp/                     Temporary query-upload workspace
|-- requirements.txt         Backend Python dependency list
|-- .env.example             Local environment template
|-- VERSION.md               Release notes and version history
```

`outputs/`, `datasets/`, and `tmp/` are runtime data/artifact locations rather than core source modules. They are documented here because the application uses them at runtime, but they should not be treated as the main code surface.

## Runtime & Admin Guide

| Area | What v1.0.0 provides |
|---|---|
| User & role management | Create users, edit username/password/role, delete normal users, and protect builtin accounts from deletion or downgrade. |
| Model state | List available model weights, apply the current inference model, and compare current model state with the gallery feature model. |
| System config | Edit `model_device`, `log_level`, `similarity_threshold`, `max_results`, `search_default_top_k`, `gallery_poll_interval_ms`, and `allowed_query_suffixes`. Gallery and upload paths are shown as read-only runtime information. |
| Gallery processing | Process new gallery images, rebuild all features, clear gallery feature records, view task logs, copy the gallery path, or ask the server host to open the gallery folder. |
| Runtime overview | Track gallery image count, unique vehicle count, latest ingest time, model consistency, available model count, device, engine status, gallery task state, user count, log count, latest log time, and gallery path. |
| Audit logs | Record practical admin and user actions such as login/logout, search, blocked search, user edits, model changes, config saves, and gallery operations without logging noisy polling/list refreshes. |

## Search Flow

```mermaid
sequenceDiagram
  participant UI as Vue Search UI
  participant API as FastAPI /api/v1/search
  participant E as ReID Engine
  participant DB as MySQL vehicle_feature
  participant FS as datasets + /static

  UI->>API: Upload query image with Top-K
  API->>API: Validate suffix, model state, gallery model safety
  API->>E: Extract query feature
  API->>DB: Load gallery vectors and metadata
  API->>API: Normalize vectors and apply similarity_threshold
  API->>API: Sort by cosine similarity and cap by Top-K / max_results
  API->>FS: Build static image paths for matched gallery images
  API-->>UI: Return total_found, time_cost, metadata, image paths, similarity scores
```

## API Snapshot

| Area | Endpoint | Purpose |
|---|---|---|
| Auth | `POST /api/v1/auth/login` | Log in and receive a JWT access token. |
| Auth | `POST /api/v1/auth/logout` | Record logout and close the current session on the client side. |
| Search | `POST /api/v1/search` | Upload a query image and receive threshold-filtered ranked gallery results. |
| Models | `GET /api/v1/admin/models` | Read current model, gallery model, available weights, and search defaults. |
| Models | `POST /api/v1/admin/models/select` | Apply the selected current model. |
| Config | `GET /api/v1/admin/config` / `POST /api/v1/admin/config` | Read or update persisted runtime configuration. |
| Overview | `GET /api/v1/admin/overview` | Read the expanded operations overview. |
| Gallery | `/api/v1/admin/gallery/*` | Sync, rebuild, clear, monitor, and open the gallery folder. |
| Users | `/api/v1/admin/users` | List, create, update, and delete non-builtin users. |
| Logs | `GET /api/v1/admin/logs` | Read paginated audit logs. |

## Data Model

```mermaid
erDiagram
  SYS_USER ||--o{ SYS_LOG : writes
  SYS_USER {
    int id PK
    string username
    string password
    string role
    bool is_builtin
    datetime create_time
  }
  SYS_LOG {
    int id PK
    int user_id
    string operation
    bool status
    datetime exec_time
  }
  VEHICLE_FEATURE {
    int id PK
    string vehicle_id
    string cam_id
    datetime capture_time
    string img_path
    blob feature
    datetime create_time
  }
```

## Model & Safety Notes

- `similarity_threshold` is applied inside the retrieval path before results are returned.
- Searches are blocked when gallery records exist but the gallery model is unknown, or when the gallery model differs from the current inference model.
- Runtime config is persisted by `backend/app/core/system_config.py`; admin settings are not just temporary UI state.
- User IDs are database primary keys and intentionally remain auto-incrementing. Deleted IDs are not reused, and business logic should not assume continuous IDs.

## Troubleshooting

- If `app` cannot be imported, start backend commands from `backend/` or set `PYTHONPATH` explicitly.
- If login fails, check `.env`, MySQL connectivity, and whether the backend has completed startup migrations.
- If search is blocked, rebuild the gallery with the current model from the admin gallery page.
- If no results are returned, check `similarity_threshold`, gallery processing status, and whether `vehicle_feature` has records.
- If CUDA or Detectron2 fails to import, switch `model_device` to `cpu` or install a PyTorch/CUDA/Detectron2 combination that matches the host machine.

---

# 中文 / Chinese

## 项目定位

Vehicle ReID System 是一个面向车辆重识别检索的全栈系统：前台负责登录和以图搜车，后台负责模型、图库、系统参数、账号权限、运行状态和审计日志管理。当前版本为 **v1.0.0**，以 FastAPI、Vue 3、MySQL 和 FastReID 为核心。

<p align="center">
  <img src="media/前台_检索效果.png" alt="车辆重识别检索效果" width="92%">
</p>

## 界面预览

| 登录 | 前台主界面 |
|---|---|
| ![登录](media/前台_登录.png) | ![前台主界面](media/前台_主界面.png) |

| 检索效果 | 系统设置 |
|---|---|
| ![检索效果](media/前台_检索效果.png) | ![系统设置](media/后台_系统设置.png) |

| 图库处理 | 运行监控 |
|---|---|
| ![图库处理](media/后台_图库处理.png) | ![运行监控](media/后台_运行监控.png) |

| 操作日志 | 账号权限 |
|---|---|
| ![操作日志](media/后台_操作日志.png) | ![账号权限](media/后台_账号权限.png) |

## 核心能力

- 使用 JWT 完成登录鉴权，并通过角色区分普通用户和管理员。
- 扫描 `datasets/gallery/`，提取车辆 ReID 特征，并将图片元数据和特征向量保存到 MySQL。
- 检索时对查询图提特征，按余弦相似度排序，并真正应用 `similarity_threshold` 和 Top-K 限制。
- 当图库特征模型未知，或图库特征模型与当前推理模型不一致时，直接阻止检索，避免返回不可信结果。
- 后台支持用户编辑、内置账号保护、模型切换、系统参数持久化、图库增量处理/全量重建/清空、打开图库目录、运行状态总览和操作日志。

## 系统架构

```mermaid
flowchart LR
  U["用户 / 管理员"] --> F["Vue 3 + Element Plus 前端"]
  F -->|"HTTP / Bearer Token"| B["FastAPI 后端"]
  B --> A["认证接口"]
  B --> M["管理接口"]
  B --> S["检索接口"]
  S --> E["ReID Engine / FastReID"]
  M --> G["GalleryService 图库处理"]
  G --> E
  S --> DB[("MySQL<br/>用户 / 日志 / 特征")]
  G --> DB
  G --> D[("datasets/gallery<br/>底库图片")]
  B --> Static["/static 静态文件挂载"]
  Static --> D
  E --> W[("outputs<br/>模型权重")]
  E --> C[("configs<br/>模型配置")]
```

## 快速上手

### 1. 克隆项目

```powershell
git clone https://github.com/Rand0MGG/vehicle-reid-system.git
cd vehicle-reid-system
```

### 2. 安装后端依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果当前环境没有可用的 PyTorch、CUDA 或 Detectron2，请按本机显卡和平台安装匹配版本，然后运行：

```powershell
python check_env.py
```

### 3. 配置环境变量

```powershell
Copy-Item .env.example .env
```

至少需要修改 `.env` 中的数据库连接和 JWT 密钥：

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:password@localhost:3306/vehicle_reid_db
ALLOWED_ORIGINS=http://localhost:5173
VITE_API_BASE_URL=/api/v1
VITE_DEV_PROXY_TARGET=http://localhost:8000
```

### 4. 初始化数据库

```powershell
mysql -u root -p < backend/app/db/init.sql
```

该脚本会创建 `vehicle_reid_db`、`sys_user`、`vehicle_feature`、`sys_log`，并插入内置管理员账号。首次登录后请立即修改默认密码。

### 5. 启动服务

```powershell
cd backend
python main.py
```

```powershell
cd frontend
npm install
npm run dev
```

后端接口前缀为 `/api/v1`，运行图库文件通过 `/static` 挂载访问。

### 6. 处理图库并开始检索

将底库图片放入 `datasets/gallery/`，然后进入 `后台 -> 图库处理`，选择“处理新增图片”或“重新处理全部图片”。推荐文件名格式：

```text
vehicleId_cameraId_YYYYMMDDHHMMSS.jpg
```

如果文件名不符合该格式，系统仍会入库，但车辆 ID、相机 ID 或时间字段会使用兜底值。图库处理完成后，即可在前台上传查询图进行检索。

## 检索流程

```mermaid
sequenceDiagram
  participant UI as 前台检索页
  participant API as /api/v1/search
  participant E as ReID Engine
  participant DB as MySQL 特征表
  participant FS as datasets + /static

  UI->>API: 上传查询图和 Top-K
  API->>API: 校验图片格式、当前模型、图库模型状态
  API->>E: 提取查询图特征
  API->>DB: 读取图库向量和元数据
  API->>API: 向量归一化并应用 similarity_threshold
  API->>API: 按余弦相似度排序并截断结果数
  API->>FS: 生成可展示的图库图片路径
  API-->>UI: 返回命中数、耗时、元数据、图片路径和相似度
```

## 项目结构

```text
vehicle-reid-system/
|-- backend/                 FastAPI 应用、接口、服务、数据库连接、启动迁移
|-- frontend/                Vue 3 + Vite + Element Plus 前端
|-- configs/                 ReID 配置文件，包括 vehicle_reid.yml
|-- fastreid/                FastReID 源码集成
|-- media/                   README 截图素材
|-- datasets/gallery/        运行时底库图片目录
|-- outputs/                 模型权重和运行产物
|-- tmp/                     查询图上传等临时文件
|-- requirements.txt         后端 Python 依赖
|-- .env.example             本地环境变量模板
|-- VERSION.md               版本记录
```

`outputs/`、`datasets/`、`tmp/` 是运行数据或产物目录，不是核心源码模块；README 仅说明它们在运行链路中的作用。

## 后台运维能力

| 模块 | 说明 |
|---|---|
| 账号权限 | 创建用户、修改用户名/密码/角色、删除普通用户，并保护内置账号不被删除或降级。 |
| 系统设置 | 配置运行设备、日志级别、相似度阈值、最大返回数、默认 Top-K、图库轮询间隔和允许图片后缀。 |
| 模型管理 | 查看当前模型、图库特征模型、模型一致性状态和可用权重，并切换当前推理模型。 |
| 图库处理 | 处理新增图片、全量重建、清空图库特征、复制路径、打开服务端图库目录、查看任务日志。 |
| 运行监控 | 查看图库数量、唯一车辆数、最近入库时间、模型一致性、引擎状态、用户数、日志数和图库任务状态。 |
| 操作日志 | 记录登录、退出、检索、被阻止的检索、用户编辑、模型切换、配置保存和图库操作，避免轮询类只读动作刷屏。 |

## 接口概览

| 模块 | 接口 | 用途 |
|---|---|---|
| 认证 | `POST /api/v1/auth/login` | 登录并返回 JWT。 |
| 认证 | `POST /api/v1/auth/logout` | 记录退出登录。 |
| 检索 | `POST /api/v1/search` | 上传查询图并返回阈值过滤后的排序结果。 |
| 模型 | `GET /api/v1/admin/models` | 读取当前模型、图库模型、可用模型和检索默认配置。 |
| 模型 | `POST /api/v1/admin/models/select` | 应用当前推理模型。 |
| 配置 | `GET /api/v1/admin/config` / `POST /api/v1/admin/config` | 读取或保存运行时配置。 |
| 总览 | `GET /api/v1/admin/overview` | 读取后台运行状态总览。 |
| 图库 | `/api/v1/admin/gallery/*` | 同步、重建、清空、查看状态、打开图库目录。 |
| 用户 | `/api/v1/admin/users` | 查看、创建、编辑和删除非内置用户。 |
| 日志 | `GET /api/v1/admin/logs` | 查看分页操作日志。 |

## 重要说明

- `similarity_threshold` 已接入检索链路，会在结果返回前过滤低分结果。
- 图库已有特征但模型来源未知，或图库模型与当前模型不一致时，检索会被阻止，需要重新处理图库。
- 系统参数由 `backend/app/core/system_config.py` 持久化，不是临时前端状态。
- 用户 ID 使用数据库自增主键，删除后不会复用旧 ID；代码和界面不应依赖连续 ID。
- 如果检索无结果，请优先检查图库是否处理完成、`vehicle_feature` 是否有记录、阈值是否过高，以及当前模型是否与图库模型一致。
