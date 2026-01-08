# 系統架構與設念 (Architecture)

## 核心目的 (Purpose)

本專案旨在解決氣象資料格式繁雜（Zarr, NetCDF, HDF5, HDF4）與存取困難的問題。透過建立標準化的 **STAC (SpatioTemporal Asset Catalog)** 介面：

1.  **統一存取層**：使用者無需關心底層檔案格式，統一透過 STAC API 查詢。
2.  **自動化 ETL**：從 NAS 儲存層自動掃描並建立索引。
3.  **時空資料立方 (Datacube)**：利用 `xstac` 擴充套件，自動提取變數、維度與解析度資訊。

---

## 系統流程 (System Flow)

```mermaid
graph TD
    A[NAS Storage] -->|Zarr/NetCDF/HDF| B(Intake Catalog *.yaml)
    B -->|Load Data| C[StacGenerator]
    C -->|Extract Metadata| D{xstac / Adapters}
    D -->|Enrich Metadata| C
    C -->|Generate JSON| E[stac_output/]
    E -->|Validation| F[Root Catalog Generator]
    F -->|Consolidate| G[catalog.json (Root)]
    E -->|Serve| H[FastAPI Server]
    H -->|View| I[STAC Browser]
```

---

## 核心組件 (Core Components)

### 1. Data Source Definition (`catalogs/*.yaml`)
- **角色**: Source of Truth (資料來源定義)。
- **技術**: 使用 `Intake` 與 `intake-xarray`。
- **功能**: 定義檔案位置、驅動程式 (Driver)、以及**人工維護的 Metadata** (如 License, Description, Keywords)。

### 2. Generator Logic (`src/generator/`)
- **角色**: ETL 處理核心。
- **職責**:
    - **Iterate**: 遍歷所有定義的 Source。
    - **Adapt**: 根據資料類型調用對應的 Adapter。
    - **Enrich**: 呼叫 `xstac` 讀取實體檔案 (Zarr/NC) 以提取真實的時空範圍與變數資訊。
    - **Output**: 生成符合 STAC Spec 的 JSON 檔案。

### 3. Adapters (`src/adapters/`)
不同的資料來源需要不同的處理策略，Adapter 模式負責將其統一轉為 STAC Item。

- **`GriddedDataAdapter`**: 處理 Zarr/NetCDF 等網格資料。負責計算 Bounding Box, Time Interval，並決定 Item 的顆粒度 (如：一年一個 Item)。
- **`CwaDataAdapter` (Planned)**: 處理氣象局測站資料 (CSV/DB)，將其轉換為 Feature Collection 或 Point Cloud 形式（視實作而定）。

---

## 關鍵技術決策

### Item 顆粒度 (Granularity)
- **現狀**: 預設採用「一年一個 Item」 (`{collection}-{year}`)。
- **原因**: 避免產生過多細碎的 Item (如每小時一個檔案會產生數萬個 Item)，這對靜態 STAC Catalog 的瀏覽效能較好。
- **例外**: 若資料集極大或需要高頻更新，架構上保留切換為「每月」或「每日」Item 的彈性。

### Idempotency (冪等性)
- 系統設計為可重複執行 (`build` command)。
- Item ID 具備唯一性與可預測性 (Deterministic)，確保重新生成時不會產生重複或衝突的 ID。
