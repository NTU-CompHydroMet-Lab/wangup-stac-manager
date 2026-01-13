# 系統架構 (Architecture)

## 核心目的 (Purposes)

本專案旨在解決氣象資料格式繁雜（Zarr, NetCDF, HDF5）與存取困難的問題。透過建立標準化的 **STAC (SpatioTemporal Asset Catalog)** 介面：

1.  **統一存取層**：使用者無需關心底層檔案格式，統一透過 STAC API (或靜態 JSON) 查詢。
2.  **自動化 ETL**：從 NAS 儲存層自動掃描並建立索引。
3.  **零複製 (Zero-Copy)**：僅建立 Metadata 索引與 Symlink，不複製 TB 級原始數據。

---

## 系統流程 (System Flow)

```mermaid
graph TD
    A[NAS Storage] -->|Zarr/NetCDF/HDF| B(Intake Catalog *.yaml)
    B -->|Configuration| C[Core Builder]
    C -->|Instantiate| D[StacGenerator]
    
    subgraph "ETL Process (Parallel)"
    D -->|Extract Metadata| E{Normalization Logic}
    E -->|Enrich| F{xstac}
    F -->|Generate| G[Event Thumbnail]
    G -->|Output| H[Collection/Items JSON]
    end
    
    H -->|Update| I[Root Catalog (Grouping)]
    I -->|Serve| J[FastAPI Server]
    J -->|Visualize| K[STAC Browser]
```

---

## 核心組件 (Core Components)

### 1. Configuration (`config/catalogs/*.yaml`)
- **角色**: Single Source of Truth。
- **技術**: Intake YAML 標準。
- **Metadata 結構**: 採用 4-Tier 標準 (Identity, Display, Scientific, Providers)。
- **關鍵欄位**: `collection_name` (標題), `catalog_name` (分組), `thumbnail_datetime` (事件時間)。

### 2. Core Orchestration (`src/core/`)
- **`builder.py`**: 負責解析 Intake Catalog 並分派平行任務。
- **`root_catalog.py`**: 負責掃描生成的子目錄，並根據 `catalog_name` 自動建立階層式目錄結構 (Group Catalogs)。
- **`validator.py`**: 整合 `stac-validator`，確保輸出的 JSON 符合 STAC 規範。

### 3. Generator Engine (`src/generator/`)
- **`base.py` (Abstract)**: 定義 STAC 生成的生命週期 (Collection -> Items -> Assets)。
- **`intake_xarray.py` (Impl)**: 針對 Xarray 可讀取的資料來源實作。
    - **Normalization**: 自動處理 0-360 經度轉換為 -180/180。
    - **Enrichment**: 使用 `xstac` 提取 Data Cube Extension 資訊。
- **`thumbnails.py`**: 實作「事件導向」縮圖生成 (Nearest Neighbor Time Selection)。
- **`assets.py`**: 處理 Zarr Symlink 與 Example Notebook 關聯。

---

## 關鍵技術決策

### 1. 靜態生成 (Static Generation)
- **決策**: 不使用動態 Database (如 pgstac)，而是生成靜態 JSON 檔案。
- **優勢**: 極致效能、易於部署 (CDN/S3)、零維護成本。
- **限制**: 複雜搜尋 (Search API) 需由 Client 端實作或遍歷目錄。

### 2. 事件導向視覺化 (Event-Based Visualization)
- **決策**: 放棄統計平均圖 (Mean/Max)，改用特定災害事件 (如颱風) 的當下快照。
- **優勢**: 讓使用者一眼就能看出資料的實際解析度與品質。

### 3. 虛擬存取 (Virtual Access)
- **決策**: 使用 Symlink 指向原始 NAS 數據。
- **優勢**: 節省數 TB 空間，且確保數據來源唯一。
