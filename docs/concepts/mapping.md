# Intake 與 STAC 的對應關係 (Mapping Specs)

本文件定義如何將實驗室的資料概念映射到 STAC (SpatioTemporal Asset Catalog) 的階層結構。

## 階層對應總表

| STAC 層級 | 實驗室概念 | 負責模組 | 規則與定義 |
| --- | --- | --- | --- |
| **Catalog** | 資料庫根目錄 (Root) | System | 只有一個 Root Catalog。不做「資料類型」的分類目錄 (Flat list of collections preferred)。 |
| **Collection** | **資料集 (Dataset)** | Intake Entry | 定義科學邊界 (例如: "QPESUMS", "ERA5")。包含聚合的時空範圍與共通 Metadata。 |
| **Item** | **邏輯單元 (Logical Unit)** | Adapter | **1 Item = 1 年** (針對 Zarr) 或 **1 Item = 1 快照** (針對 DB)。避免過度細碎的 Item。 |
| **Asset** | **實體檔案 (File)** | Adapter | 指向實際的 Zarr Store, NetCDF 檔案 或 SQLite DB。 |
| **Property** | Metadata | Intake/xstac | 包含 `processing:level`, `data:source`, `gsd` 等欄位。 |

---

## 詳細映射規則

### 1. Collection (來自 Intake Source)
Intake YAML 中的每一個 Entry 對應一個 STAC Collection。
- **ID**: 使用 Intake Source 的 key (例如 `qpesums`, `imerg_bronze`).
- **Title/Description**: 來自 Intake Metadata。
- **Keywords/Providers**: 來自 Intake Metadata。

### 2. Item 策略 (Granularity Strategy)

為了平衡瀏覽效能與資料存取靈活性，我們採用以下策略：

#### A. 網格資料 (Gridded Data) - 如 QPESUMS, ERA5
*   **Item 單位**: **Yearly (每年一個 Item)**
*   **Item ID 命名**: `{collection_id}-{year}` (例如 `qpesums-2023`)
*   **Asset**: 指向該年份的 Zarr Group 或檔案。
*   **考量**: 雖然 Zarr 內部可能包含細緻的時間切片，但在 STAC 層級我們將其視為一個完整的「年度資料方塊」。

#### B. 靜態/測站資料 (Static/Station) - 如 Rain Gauges
*   **Item 單位**: **Single Item (單一快照)**
*   **Item ID 命名**: `{collection_id}-source`
*   **Asset**: 指向 SQLite 或 CSV 檔案。

### 3. Metadata 欄位處理

Generator 會自動合併來自兩個來源的 Metadata：
1.  **Intake YAML (人工維護)**: 優先權較低，用於提供 Context (Description, License, Project ID)。
2.  **xstac (自動提取)**: 優先權最高，從檔案 Header 讀取真實資訊 (Variables, Dimensions, Shape, Time Range)。

---

## 範例：特定資料集設定

| 資料集 (Collection) | Item 策略 | Asset Media Type | 關鍵 Metadata |
| --- | --- | --- | --- |
| **QPESUMS** | Yearly (`qpesums-2023`) | `application/vnd+zarr` | `constellation`: "radar", `gsd`: 1300m |
| **ERA5 Convection** | Yearly | `application/vnd+zarr` | `source`: "ECMWF", `variables`: ["u", "v", "w"] |
| **Himawari L2** | Yearly | `application/vnd+zarr` | `platform`: "himawari-8", `gsd`: 500m |
| **CWA Rain Gauge** | Snapshot | `application/vnd.sqlite3` | `source`: "CWA", `station_count`: (dynamic) |
