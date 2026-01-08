# 完整欄位對照表 (STAC Field-by-Field Check)

本表逐行比對 [Google Earth Engine STAC](https://storage.googleapis.com/earthengine-stac/catalog/catalog.json) 與我們目前的實作 (`stac_output/`)。
為了方便後續維護者理解，新增了 **「STAC 定義/用途」** 欄位，解釋該欄位在規範中的標準意義。

---

## 1. 根目錄 (Root Catalog)
**Source**: `GEE/catalog.json` vs `stac_output/catalog.json`

| 欄位 (Field) | STAC 定義/用途 (Definition) | GEE Example | Lab Status | Decision |
| :--- | :--- | :--- | :--- | :--- |
| `id` | **唯一識別碼**。在同一目錄下必須唯一。 | `"GEE_catalog"` | ✅ `"stac-catalog"` | OK |
| `type` | **物件類型**。必須是 `Catalog` 或 `Collection`。 | `"Catalog"` | ✅ `"Catalog"` | OK |
| `title` | **人類可讀標題**。簡短名稱，用於顯示。 | `"Earth Engine..."` | ✅ `"NTU Lab Data"` | OK |
| `description` | **詳細描述**。支援 Markdown，解釋目錄內容。 | Markdown Links | ⚠️ Basic string | **Action**: 增強描述 |
| `stac_version` | **STAC 版本**。 | `"1.0.0"` | ✅ `"1.0.0"` | OK |
| `links` | **關聯連結**。包含 `self`, `root`, `child` 等結構關係。 | 1000+ children | ✅ Child links | OK |
| `conformsTo` | **符合規範列表**。列出支援的 Extension URL。 | (Empty in Root) | ❌ | Skip |

---

## 2. 資料集 (Collection) - 核心
**Source**: `GEE/ECMWF/ECMWF_ERA5_HOURLY.json` vs `stac_output/era5/collection.json`

| 欄位 (Field) | STAC 定義/用途 (Definition) | GEE Example | Lab Status | Decision |
| :--- | :--- | :--- | :--- | :--- |
| `id` | **集合識別碼**。全域唯一 ID (Slug)。 | `"ECMWF/ERA5/HOURLY"` | ✅ `"era5_east_asia"` | OK |
| `stac_extensions` | **擴充套件列表**。宣告此 Collection 使用了哪些非核心欄位 (如 `sci`, `cube`)。 | `["scientific"]` | ⚠️ `['datacube']` | **Action**: Add `scientific` |
| `title` | **集合標題**。 | `"ERA5 Hourly..."` | ✅ | OK |
| `description` | **完整說明**。應包含方法論、限制、數據來源背景。 | Detailed + Issues | ⚠️ Brief | **Action**: Expand |
| `license` | **授權條款**。應使用 [SPDX](https://spdx.org/licenses/) 代碼或 `proprietary`。 | `"proprietary"` | ✅ `"CC-BY-4.0"` | OK |
| `keywords` | **關鍵字**。輔助搜尋。 | `["climate"]` | ✅ | OK |
| `providers` | **資料提供者**。包含名稱、角色 (`roles`) 與網址。 | Detailed Roles | ⚠️ Simple Dict | **Action**: Fix roles |
| `extent` | **時空範圍**。包含 Bbox 與 Time Interval。 | Fixed interval | ✅ Auto-calculated | OK |
| `links` | **資源連結**。除結構外，也包含 `license`, `preview`, `cite-as`。 | Rich types | ⚠️ Structural only | **Action**: Add types |

---

## 3. 資料集 - 擴充屬性 (Extensions)

### A. Scientific Extension (`sci`)
用於標註科學資料的引用來源與學術脈絡。

| 欄位 (Field) | STAC 定義/用途 (Definition) | GEE Example | Lab Status | Decision |
| :--- | :--- | :--- | :--- | :--- |
| `sci:citation` | **引用格式**。建議使用者如何引用此資料集。 | `"Hersbach... (2020)"` | ❌ | **Must Have** |
| `sci:doi` | **數位物件識別碼**。資料集的永久連結。 | `"10.1000/xyz"` | ❌ | **Must Have** |

### B. Google Earth Engine Extension (`gee`)
GEE 專用的客製化欄位 (非 STAC 標準)。

| 欄位 (Field) | STAC 定義/用途 (Definition) | GEE Example | Decision |
| :--- | :--- | :--- | :--- |
| `gee:type` | GEE 內部資料類型 (Image vs ImageCollection)。 | `"image_collection"` | ❌ Skip |
| `gee:terms_of_use` | **使用條款全文**。雖然非標準，但很實用，建議放入 `description` 或自訂欄位。 | Full Text | **Action**: Add field |

### C. Datacube Extension (`cube`)
用於描述多維陣列資料 (NetCDF/Zarr) 的維度與變數。我們用這個取代 GEE 的 `eo:bands`。

| 欄位 (Field) | STAC 定義/用途 (Definition) | 比較 (vs GEE) | Decision |
| :--- | :--- | :--- | :--- |
| `cube:dimensions` | **維度定義**。描述軸 (Axis) 的名稱、類型、範圍 (e.g. `time`, `lat`, `lon`)。 | GEE 無此概念 (預設 2D) | **Keep** (Superior) |
| `cube:variables` | **變數定義**。描述陣列中的變數屬性 (Unit, Shape, Chunks)。 | 類似 GEE `eo:bands` | **Keep** (Superior) |

---

## 4. 變數描述 (Variable Metadata) Detail

| 欄位 | STAC 定義 (Definition) | GEE (`eo:bands`) | Lab (`cube:variables`) |
| :--- | :--- | :--- | :--- |
| `name` | **變數名稱**。 | `temperature_2m` | `t2m` (Original) |
| `description` | **變數描述**。 | Detailed text | `attrs.long_name` |
| `unit` | **單位** (使用 UDUNITS 格式)。 | `gee:units` | `unit` (CF Standard) |
| `shape` | **陣列形狀**。 | N/A | `[Time, Lat, Lon]` |
| `chunks` | **分塊大小** (Cloud Native IO 關鍵)。 | N/A | `[1, 100, 100]` |

---

## 5. 總結修正方向

為了補足與 GEE 的差距，同時保留我們對多維資料的優勢，未來的 `Collection` JSON 應該長這樣：

```json
{
  "type": "Collection",
  "stac_extensions": [
    "https://stac-extensions.github.io/scientific/v1.0.0/schema.json", // [NEW]
    "https://stac-extensions.github.io/datacube/v2.0.0/schema.json"     // [EXISTING]
  ],
  "title": "ERA5 Hourly Data",
  "providers": [ // [UPDATED]
    {
      "name": "ECMWF",
      "roles": ["producer", "licensor"],
      "url": "https://..."
    },
    {
      "name": "NTU Lab",
      "roles": ["host", "processor"],
      "url": "https://..."
    }
  ],
  "sci:citation": "Hersbach, H. et al...", // [NEW]
  "sci:doi": "10.xxx/xxx",                 // [NEW]
  "cube:variables": { ... }                // [KEEP]
}
```

---

## 6. 參考資源 (References)

以下是本文件提及之規範與範例的官方來源：

| 資源名稱 | 連結 | 用途說明 |
| :--- | :--- | :--- |
| **STAC Spec** | [radiantearth/stac-spec](https://github.com/radiantearth/stac-spec) | STAC 核心規範 (Catalog, Collection, Item) |
| **Scientific Ext** | [stac-extensions/scientific](https://github.com/stac-extensions/scientific) | 定義引用 (`sci:citation`) 與 DOI (`sci:doi`) |
| **Datacube Ext** | [stac-extensions/datacube](https://github.com/stac-extensions/datacube) | 定義多維陣列 (`cube:variables`, `dimensions`) |
| **GEE STAC** | [google/earthengine-catalog](https://github.com/google/earthengine-catalog) | Google Earth Engine 的 STAC 實作原始碼 (Jsonnet) |
| **STAC Browser** | [radiantearth/stac-browser](https://github.com/radiantearth/stac-browser) | STAC 的視覺化前端 (我們專案使用的 static browse) |

---

## 7. JSON 實例對照 (JSON Commented Walkthrough)

以下分別展示 **Lab (目前)** 與 **GEE (目標)** 的 JSON 結構，並附上註解說明差異。

### 7.1. NTU Lab STAC (Current Status)

這是我們目前產出的樣子。優點是 Datacube 資訊完整，缺點是缺乏學術脈絡。

```jsonc
{
  "type": "Collection",
  "id": "era5_east_asia",
  "stac_version": "1.0.0",
  "description": "Short description...",  // ⚠️ Gap: 描述通常太短
  "license": "CC-BY-4.0",
  
  // [Analysis]: 我們使用 datacube extension，這對 Zarr 很好
  "stac_extensions": [
    "https://stac-extensions.github.io/datacube/v2.0.0/schema.json"
  ],

  // ⚠️ Gap: Providers 只有基本的 name/url，沒有 roles
  "providers": [
    {
      "name": "ECMWF",
      "url": "https://..."
    }
  ],

  // ❌ Gap: 缺少 sci:citation 與 sci:doi (Scientific Extension)

  // [Advantage]: 我們用 cube:variables 描述多維資料 (優於 GEE 的 eo:bands)
  "cube:variables": {
    "t2m": {
      "type": "data",
      "dimensions": ["time", "lat", "lon"],
      "unit": "K",               // ✅ Standard: 使用標準單位
      "shape": [8760, 721, 1440],  // ✅ Unique: 明確的陣列形狀
      "chunks": [1, 100, 100]      // ✅ Unique: 明確的分塊策略 (Cloud Native Friendly)
    }
  }
}
```

### 7.2. Google Earth Engine STAC (Target Standard)

這是我們希望能達到的標準（除了 eo:bands 以外）。

```jsonc
{
  "type": "Collection",
  "id": "ECMWF/ERA5/HOURLY",
  "stac_version": "1.0.0",
  "description": "Detailed description with methodology...", // ✅ Goal: 詳細的 Markdown 描述
  "license": "proprietary",
  
  "stac_extensions": [
    "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
    "https://stac-extensions.github.io/scientific/v1.0.0/schema.json" // ✅ Goal: 引入 Scientific Ext
  ],

  // ✅ Goal: 詳細的 Providers 角色分工
  "providers": [
    {
      "name": "C3S",
      "roles": ["licensor", "producer"], // 明確指出誰授權、誰生產
      "url": "https://..."
    },
    {
      "name": "Google",
      "roles": ["host"],                 // 明確指出誰負責 hosting
      "url": "https://..."
    }
  ],

  // ✅ Goal: 學術引用資訊 (這是最重要的差距)
  "sci:citation": "Hersbach, H. et al (2020). The ERA5 global reanalysis...",
  "sci:doi": "10.1000/xyz",

  // [Note]: GEE 使用 eo:bands (主要針對 2D 影像)，我們不需要模仿這個
  "summaries": {
    "eo:bands": [
      {
        "name": "temperature_2m",
        "description": "Air temperature...",
        "gee:units": "K"
      }
    ]
  }
}
```

### 7.3. Item Level Comparison (JSON Watch)

**NTU Lab Item (Current):** 1 Item = 1 Year.

```jsonc
{
  "type": "Feature",
  "id": "era5_east_asia-2023",
  "collection": "era5_east_asia",
  
  // [Analysis]: 我們的 Interval 有效覆蓋整年
  "properties": {
    "start_datetime": "2023-01-01T00:00:00Z",
    "end_datetime": "2023-12-31T23:00:00Z",
    "cube:variables": { ... } // ✅ 這裡也有變數細節，方便讀取
  },

  // ❌ Gap: 只有 bbox，沒有預覽圖
  "assets": {
    "zarr": {
      "href": "/NAS/.../era5_2023.zarr",
      "roles": ["data"]
    }
  }
}
```

**GEE Item (Typical):** 1 Item = 1 Hour/Image.

```jsonc
{
  "type": "Feature",
  "id": "ECMWF/ERA5/HOURLY/20230101T000000",
  "collection": "ECMWF/ERA5/HOURLY",
  
  "properties": {
    "datetime": "2023-01-01T00:00:00Z", // ✅ Point time
    "eo:cloud_cover": 0
  },

  "assets": {
    // 🌟 Advantage: GEE 預先算好了縮圖 (Thumbnail)
    "thumbnail": {
      "href": "https://earthengine.googleapis.com/.../thumb",
      "type": "image/png",
      "roles": ["thumbnail"]
    }
  }
}
```

---

## 8. 視覺化差異分析 (Visualization Gap)

> **Q: 為什麼 GEE 有漂亮的地圖跟全球溫度圖，我們只有 bbox？**

這不是 STAC 格式的問題，而是 **「資源 (Assets)」** 的問題。

### 原因 1: 預渲染縮圖 (Thumbnails)
GEE 會為每一張影像預先產生一張小的 JPG/PNG 預覽圖，並在 Item JSON 的 assets 裡標註 `roles: ["thumbnail"]`。stac-browser 讀到這個 role，就會自動顯示圖片，而不是只顯示方框。

### 原因 2: 動態圖磚服務 (Dynamic Tiling)
GEE 甚至提供 `xyz` 或 `tilejson` 的 Asset 連結。stac-browser 可以掛載這些連結，讓使用者在地圖上拖拉縮放 (Slippy Map)。這需要背後有一個運作中的 Map Server (如 GEE Engine, TiTiler)。

### 我們的解決方案 (Action Plan)
我們目前是靜態檔案 (Static File)，沒有 Map Server，但我們可以做 **Thumbnails**。

1.  **Generate Thumbnails**: 在產生 STAC Item 時，順便用 Python (matplotlib/xarray) 畫一張該年的平均溫度/降雨分佈圖 (PNG)。
2.  **Add to Assets**:
    ```json
    "assets": {
      "thumbnail": {
        "href": "./thumbnails/era5_2023_thumb.png",
        "type": "image/png",
        "roles": ["thumbnail"]
      }
    }
    ```
3.  **Result**: 這樣 stac-browser 就會顯示那張漂亮的溫度圖，而不是只有藍色方框了。




