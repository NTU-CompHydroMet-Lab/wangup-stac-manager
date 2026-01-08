# 新增資料集標準作業流程 (SOP)

本文件定義了實驗室將資料加入 STAC 索引的標準流程。所有新加入的資料集都必須符合本規範，以確保 Catalog 的完整性與一致性。

> **參考標準**: 本規範參考 [Google Earth Engine STAC Catalog](https://radiantearth.github.io/stac-browser/#/external/storage.googleapis.com/earthengine-stac/catalog/catalog.json) 的最佳實踐，採用豐富的 Metadata 與 Scientific Extension 欄位。

## 1. 準備工作 (Per-Dataset Checklist)

在撰寫 YAML 之前，請先確認已收集以下資訊。這份清單**建議直接複製貼上到 Issue ticket 中追蹤**。

### 📌 Collection Level (資料集層級)
> 定義科學邊界與共通屬性

- [ ] **Data ID**: 英文小寫、無空格 (e.g., `qpesums-maxdbz`, `era5-convection`)
- [ ] **Title**: 人類可讀的完整名稱 (e.g., "QPESUMS Radar Mosaic Maximum Reflectivity")
- [ ] **Description**: 詳細描述，包含資料來源、用途、限制。
- [ ] **License**: 授權條款 (e.g., "CC-BY-4.0", "SCID", "Proprietary", "CWA Open Data")
- [ ] **Providers**: 完整列表，包含 `license` (授權方), `producer` (產製方), `processor` (處理方), `host` (託管方)。
- [ ] **Keywords**: 至少 3 個關鍵字，建議包含地名、變數名、計畫名。
- [ ] **Scientific Info**: DOI, 引用文獻 (Citation)。

### 📌 Item Level (顆粒度決策)
> 定義 STAC Item 代表的邏輯單元

- [ ] **Item Strategy**:
    - [ ] **Yearly (推薦)**: 適用於 Zarr, NetCDF 網格資料。一年一個 Item。
    - [ ] **Snapshot**: 適用於資料庫 (SQLite) 或固定測站清單。整個資料集只有一個 Item。

### 📌 Asset Level (實體檔案)
> 定義資料位置

- [ ] **Path Pattern**: 確認資料在 NAS 上的路徑規則 (e.g., `/NAS/data/2023/*.zarr`)。
- [ ] **Media Type**: 確認檔案格式 MIME type (Zarr: `application/vnd+zarr`, HDF5: `application/x-hdf5`)。

---

## 2. 標準 Metadata Template (Copy-Paste)

請複製以下區塊到 `catalogs/your_new_catalog.yaml` (或直接加在現有 yaml 中)。

```yaml
sources:
  # [REQUIRED] 唯一識別碼 (Slug)
  <dataset_id>:
    driver: zarr
    args:
      # [REQUIRED] 檔案路徑，支援 glob
      urlpath: "/path/to/data/*.zarr"
      
    metadata:
      # --- System Config (必要設定) ---
      stac_adapter: "gridded"
      
      # --- Collection Identity (General) ---
      # [REQUIRED] 顯示名稱
      title: "Dataset Title Here"
      # [REQUIRED] 詳細描述 (支援 Markdown)
      description: |
        Detailed description of the dataset.
        Include methodology, limitations, and usage notes.
      # [REQUIRED] 授權 SPDX code or "Proprietary"
      license: "CC-BY-4.0"
      
      # --- Providers (GEE Style) ---
      providers:
        - name: "Agency Name (e.g., CWA)"
          roles: ["licensor", "producer"]
          url: "https://www.cwa.gov.tw"
        - name: "NTU CompHydroMet Lab"
          roles: ["processor", "host"]
          url: "https://github.com/NTU-CompHydroMet-Lab"

      # --- Scientific Extension (Recommended) ---
      # [OPTIONAL] DOI 連結
      sci:doi: "10.1000/xyz123"
      # [OPTIONAL] 引用格式
      sci:citation: "Author et al. (2023). Dataset Title. Journal."
      
      # --- Search & Discovery ---
      keywords: ["keyword1", "keyword2", "Taiwan"]
      # [OPTIONAL] 專案編號
      project_id: "NSTC-112-XXXX"
      
      # --- Properties ---
      platform: "satellite-name"
      instruments: ["sensor-name"]
      # [REQUIRED] Medallion: bronze, silver, gold
      processing:level: "silver" 
```

---

## 3. 欄位定義說明 (Field Definitions)

### Core Fields
| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| `title` | ✅ | 簡短標題 |
| `description` | ✅ | 完整說明，越詳細越好 |
| `license` | ✅ | 使用 SPDX 代碼 (e.g. `CC-BY-4.0`) |
| `providers` | ✅ | 必須清楚標示誰擁有資料 (`licensor`) 以及誰託管資料 (`host`) |

### Scientific Extension (sci)
這能讓學術界使用者快速引用你的資料。
| 欄位 | 建議 | 說明 |
| --- | --- | --- |
| `sci:doi` | ⭕ | 資料集的 DOI (若有) |
| `sci:citation` | ⭕ | 建議的引用文字 |

### Properties
| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| `processing:level` | ✅ | `bronze` (Raw), `silver` (Cleaned), `gold` (Table) |
| `platform` | ⭕ | 衛星或載具平台 |

---

## 4. GEE 標準比較與FAQ

### Q: 我們要做到像 Earth Engine (GEE) 那麼詳細嗎？
**A: 盡量接近，但保持彈性。**
GEE 的 Catalog 非常完整，因為他們有團隊專門維護 Metadata。我們的策略是：
1.  **結構一致**：欄位名稱 (如 `sci:citation`) 跟他們對齊。
2.  **內容漸進**：不用一次填滿，但「必填」欄位 (`title`, `description`, `providers`) 必須確實填寫。

### Q: 為什麼 Providers 分這麼細？
A: 區分 `producer` (誰產生的) 與 `host` (誰存的) 很重要。例如 ERA5 資料，Producer 是 ECMWF，但 Host 是我們實驗室 (NTU Lab)。這能明確歸屬責任與版權。
