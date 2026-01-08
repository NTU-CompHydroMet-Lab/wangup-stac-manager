# STAC Metadata Comparison Matrix (Lab vs GEE)

這份文件詳細比較了每個階層（Root > Provider > Collection > Item）的 Metadata 差異。
欄位分類為：✅ (雙方皆有), 🌟 (GEE 額外欄位), 🧪 (Lab 額外/特有欄位)。

---

## Level 1: Root Catalog (根目錄)

| 欄位 (Field) | Lab (Current) | GEE (Example) | 必要性 (Decision) |
| :--- | :--- | :--- | :--- |
| `id` | ✅ `stac-catalog` | `GEE_catalog` | 必填 |
| `description` | ✅ Basic | Rich Markdown (Links to HTML/Browser) | 建議增強描述與連結 |
| `title` | ✅ | `Earth Engine Public Data Catalog` | 必填 |
| `links` | ✅ (child links) | ✅ (child links) | 必填 |
| `stac_version` | ✅ `1.0.0` | `1.0.0` | 必填 |
| `conformsTo` | ❌ | ❌ (Root Usually minimal) | 保持現狀 |

**小結**：Root 層級差異不大，主要是描述的豐富度。

---

## Level 2: Provider Catalog (e.g. ECMWF)

GEE 有這一層「中間層」來歸類同一來源的資料，我們目前只有 Root 直接連到 Collection。

| 欄位 (Field) | Lab (N/A) | GEE (ECMWF) | 必要性 (Decision) |
| :--- | :--- | :--- | :--- |
| `id` | - | `ECMWF` | 若資料量大需分類才需要 |
| `type` | - | `Catalog` | - |
| `description` | - | 連結到 ECMWF 官網 | - |
| `links` | - | 指向各個 ERA5 Collection | - |

**小結**：目前我們資料量不到 20 個，**不需要** 這一層，維持平面結構即可。

---

## Level 3: Collection (e.g. ERA5 Hourly)

這是差異最大的地方。

### A. 通用屬性 (Common)
| 欄位 | Lab | GEE | 備註 |
| :--- | :--- | :--- | :--- |
| `id` | ✅ `era5_east_asia` | `ECMWF/ERA5/HOURLY` | GEE 用斜線分層，我們用底線 |
| `title` | ✅ | `ERA5 Hourly...` | - |
| `description` | ✅ | ✅ (Very detailed) | 需加強內容 |
| `license` | ✅ `CC-BY-4.0` | `proprietary` | - |
| `extent` | ✅ (Auto-calc) | ✅ | GEE 寫死 `2026-01`，我們自動抓 |
| `keywords` | ✅ | ✅ | - |
| `providers` | ⚠️ Simple Dict | ✅ **Full Role List** | **需改進**：區分 producer/host |

### B. GEE 額外欄位 (GEE Extra)
| 欄位 | GEE 用途 | Lab 建議 |
| :--- | :--- | :--- |
| `gee:type` | `image_collection` | ❌ 不需 (GEE 內部邏輯) |
| `gee:terms_of_use` | 完整授權文字 | 🌟 **建議採用** (放入 `collection.json`) |
| `gee:interval` | 時間頻率 (hourly) | ❌ 不需 (由 Item 決定) |
| `sci:citation` | 學術引用格式 | 🌟 **強烈建議** (Scientific Extension) |
| `sci:doi` | DOI 連結 | 🌟 **強烈建議** |
| `summaries:eo:bands` | 波段清單 | ❌ 改用 `cube:variables` |

### C. Lab 特有/優勢 (Lab Advantage)
我們使用 `datacube` extension 來描述多維網格資料，這比 GEE 的 Image Collection 更先進。

| 欄位 | 說明 | 優勢 |
| :--- | :--- | :--- |
| `cube:dimensions`🧪 | 定義 (time, lat, lon) | 機器可讀性高，支援切片 |
| `cube:variables`🧪 | 定義變數 (chunks, shape, unit) | 完整描述 Zarr 內部結構 |
| `xstac:attrs`🧪 | 原始 NetCDF 屬性 | 保留原始 Metadata (standard_name) |

---

## Level 4: Item (Logical Unit)

| 欄位 | Lab (Yearly) | GEE (Hourly) | 決策 |
| :--- | :--- | :--- | :--- |
| `id` | `{col}-{year}` | `{col}/{time}` | 維持 Yearly 策略 |
| `properties:datetime` | ❌ (use start/end) | ✅ Point time | 維持我們的 Interval 模式 |
| `assets` | ✅ Zarr (S3/NAS) | ✅ GeoTIFF | - |
| `assets:roles` | ✅ `data` | ✅ `data` | - |

---

## 結論與行動方針

1.  **保留優勢**：繼續使用 `cube:dimensions` 與 `cube:variables` (來自 `xstac`)，這是氣象資料的標準做法，比 GEE 的 `eo:bands` 更好。
2.  **補強弱點**：
    *   **Provider Roles**: 在 YAML 中強制區分 `producer` vs `host`。
    *   **Scientific Context**: 引入 `sci:citation` 與 `sci:doi`。
    *   **Terms**: 在 YAML 增加 `terms_of_use` 欄位並寫入 JSON。

我們不需要完全複製 GEE (例如 `gee:*` namespace)，而是吸收其「詳細描述」的精神。
