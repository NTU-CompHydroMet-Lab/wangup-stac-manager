# Gap Analysis: Lab STAC vs Google Earth Engine (GEE) STAC

本文件比較目前實驗室的 STAC 實作與 [Google Earth Engine STAC Catalog](https://radiantearth.github.io/stac-browser/#/external/storage.googleapis.com/earthengine-stac/catalog/catalog.json) 的差異，並提出改進建議。

## 1. 結構全面性 (Completeness)

| 特性 (Feature) | NTU Lab STAC (Current) | GEE STAC (Benchmark) | 差異與建議 (Gap & Action) |
| :--- | :--- | :--- | :--- |
| **Catalog Hierarchy** | Flat (所有 Collection 都在根目錄) | Nested (按主題/來源分類) | ⚠️ **差距**: GEE 有完整的分類樹 (Atmosphere > Temperature)。建議暫時維持 Flat (因資料少)，未來可引入 `catalog-builder`。 |
| **Collection Metadata** | 基本 (Title, Desc, License) | **極豐富** (Citation, DOI, Versions, Tags) | 🔴 **差距**: 缺 Scientific Extension。建議補上 `sci:doi` 與 `sci:citation`。 |
| **Item Granularity** | Yearly (1 Item = 1 Year) | Monthly/Daily (通常) | ✅ **差異**: 這是設計選擇。GEE 量體大需切細，我們為求管理方便維持 Yearly。 |
| **Asset Format** | Zarr (Cloud Native) | GeoTIFF (Cloud Optimized) | ✅ **差異**: 資料格式不同，無優劣之分。 |

---

## 2. Metadata 欄位比較 (Collection Level)

| 欄位 (Field) | Lab Status | GEE Standard | 改進動作 (Action Item) |
| :--- | :--- | :--- | :--- |
| `id` | ✅ Slug | Slug | - |
| `title` | ✅ | ✅ | - |
| `description` | ✅ Markdown | ✅ Rich Markdown | 我們的描述通常太短，需豐富化 (Methodology, Caveats)。 |
| `keywords` | ✅ | ✅ | 建議建立 Controlled Vocabulary (固定關鍵字表)。 |
| `providers` | ⚠️ Basic | ✅ **Detailed Roles** | 需區分 `licensor`, `producer`, `processor`, `host`。 |
| `license` | ⚠️ CC-BY-4.0 | ✅ SPDX / Custom | 需確認每個資料集的真實授權 (Proprietary vs Open)。 |
| `sci:citation` | ❌ Missing | ✅ Standard | **新增此欄位**，方便學術引用。 |
| `sci:doi` | ❌ Missing | ✅ Standard | **新增此欄位**。 |
| `gee:type` | N/A | `image_collection` | GEE 專用欄位，我們不需要。 |
| `summaries` | ✅ `processing:level` | ✅ Detailed (bands, vis) | GEE 有視覺化參數 (`gee:visualizations`)，我們目前不需要。 |

---

## 3. Metadata 欄位比較 (Item Level)

| 欄位 (Field) | Lab Status | GEE Standard | 改進動作 (Action Item) |
| :--- | :--- | :--- | :--- |
| `id` | `{col}-{year}` | `{col}/{id}` | ID 邏輯一致即可。 |
| `datetime` | Year Center | Acquisition Time | 我們的 Item 是「時段 (Interval)」，GEE 通常是「瞬間 (Point)」。 |
| `properties` | Minimal | Rich | - |
| `cube:dimensions` | ✅ via `xstac` | N/A (GEE 使用 `eo:bands`) | 我們使用 Datacube Extension，這點比 GEE 更適合 Zarr/NetCDF 多維資料。**優於 GEE**。 |
| `cube:variables` | ✅ via `xstac` | `eo:bands` | 同上，我們針對氣象資料的最佳化。 |

---

## 4. 程式碼支援度分析 (Codebase Check)

檢查 `src/generator/` 目前的支援狀況：

*   **Supported**: `title`, `description`, `license`, `providers` (basic), `processing:level`, `platform`.
*   **Partially Supported**: `summaries` (由 xstac 自動提取，但缺乏人工注入機制).
*   **Missing (需修改程式碼)**:
    *   `sci:*` (Scientific Extension): 目前 Generator **不會** 把 YAML 裡的 `sci:doi` 讀進去。
    *   `providers` (Detailed Roles): 目前只是直接複製 YAML，需確保 Schema 正確。

## 5. 總結建議

我們與 GEE 標準最主要的差距在於 **"Scientific Context" (學術脈絡)**。

**下一步修正計畫 (Next Steps)**:
1.  **文件面**: 繼續推動 `adding_datasets.md` 的標準化 (已完成)。
2.  **程式面**: 修改 `src/generator/base.py`，讓它能讀取並寫入 `sci:` 開頭的 metadata 欄位 以及正確處理 `providers` 結構。
