# STAC 目錄層級架構說明

本文件說明本專案的 STAC (SpatioTemporal Asset Catalog) 層級架構，以鹽水溪流域淹水模擬事件為範例。

## 層級總覽

| 層級 | 角色 | 以淹水事件為例 |
|------|------|---------------|
| **Catalog** | 主題目錄，只負責組織與導航 | 「淹水模擬」 |
| **Collection** | 一組相關資料的描述，定義共同的時空範圍和授權 | 「降雨事件 20210604」 |
| **Item** | 單筆可定位的資料紀錄（時間 + 空間 + metadata + 資料連結） | 「輸入雨量」、「水深時序列」等 |
| **Asset** | 實際的檔案 | `.nc`、`.zarr`、`.parquet` |

簡單記：**Catalog 導航 → Collection 分類 → Item 定位 → Asset 取資料**。

## 目錄結構

```
stac_catalog/
├── catalog.json                              ← Root Catalog（全實驗室資料總目錄）
└── 淹水模擬/
    ├── catalog.json                          ← Group Catalog（淹水模擬主題目錄）
    └── flood_event_20210604/
        ├── collection.json                   ← Event Collection（事件層集合）
        ├── items/                            ← 事件層 Items
        │   ├── __rain_forcing.json
        │   ├── __depth_timeseries.json
        │   ├── __max_depth.json
        │   ├── __iot_timeseries.json
        │   └── __integrated.json             ← 跨資產融合 Item
        └── {product_id}/
            ├── collection.json               ← Product Collection（產品層集合）
            └── items/
                └── {product_id}-2021.json    ← 年度 Item
```

## 各層級說明

### Catalog（目錄）

Catalog 不包含資料，只負責組織和導航。

| Catalog | ID | 用途 |
|---------|-----|------|
| Root | `stac-root-catalog` | 整個實驗室的資料總目錄，連結所有主題 |
| Group | `淹水模擬` | 淹水模擬這個主題的分類目錄 |

### Collection（集合）

Collection 定義時空範圍（extent）、關鍵字、授權條款，是搜尋的基本單位。

| Collection | 說明 |
|------------|------|
| **降雨事件 20210604**（事件層） | 聚合此事件所有產品的入口，`aggregation_type: event_collection` |
| 輸入雨量（WGS84） | QPESUMS 時序列網格雨量，WGS84 座標 |
| 水深時序列（核心 Zarr） | FM_model_map 的 Mesh2d/mesh1d 水深，Zarr 格式 |
| 最大淹水深度（網格面） | 各 2D 網格面的時間最大淹水深度 |
| 淹水感測器驗證時序列 | IoT 觀測值 vs 模型模擬值的配對時序列 |

### Item（項目）

Item 是一個 GeoJSON Feature，同時攜帶 metadata 與指向 asset 的連結：

- `geometry` / `bbox` — 這筆資料的空間範圍
- `datetime` — 時間範圍
- `properties` — 所有描述性 metadata
- `assets` — 指向實際檔案的連結

#### 事件層 Items

| Item ID | 說明 |
|---------|------|
| `__rain_forcing` | 降雨驅動力 |
| `__depth_timeseries` | 水深時序列 |
| `__max_depth` | 最大淹水深度 |
| `__iot_timeseries` | 淹水感測器驗證資料 |
| **`__integrated`** | 跨資產融合 Item — 把上面四個整合在一起 |

#### 產品層 Items

每個 Product Collection 下各有一個年度 Item（如 `rainfall_wgs84-2021`），包含該產品的原始資料連結。

### Asset（資產）

Asset 是實際的檔案（透過 symlink 指向 `data/` 下的原始檔案），每個 asset 標註 media type 和 roles。

以跨資產融合 Item（`__integrated`）為例：

| Asset Key | 格式 | 說明 |
|-----------|------|------|
| `depth_simulation` | Zarr | Mesh2d 模擬水深時序列 |
| `depth_iot` | Parquet | IoT 站點模擬值 vs 觀測值 |
| `rain_forcing` | NetCDF | 降雨驅動力 |
| `max_depth` | NetCDF | 最大淹水深度 |
| `station_face_mapping` | JSON | IoT 測站 → Mesh2d 網格面對應索引 |
| `sim_depth_at_stations` | CSV | IoT 站點位置的模型模擬水深時序 |

## 以事件為例的完整對照

```
淹水模擬 (Catalog)
└── 降雨事件 20210604 (Collection)
    ├── __rain_forcing (Item) → rainfall_wgs84.nc (Asset)
    ├── __depth_timeseries (Item) → fm_map_core.zarr (Asset)
    ├── __max_depth (Item) → max_depth_faces.nc (Asset)
    ├── __iot_timeseries (Item) → iot_validation.parquet (Asset)
    └── __integrated (Item) → 上面四個 Asset 全部整合
```

## 新增事件

未來加入新事件（如 20210730）只需：

1. 準備資料至 `data/flood_modelling_products/event_20210730/`
2. 在 `config/catalogs/flood_modelling_intake_catalog.yaml` 新增對應 sources
3. 在 `config/main.yaml` 的 `build.targets` 加入新事件的 build targets
4. 執行 `uv run python -m src.cli build`

新事件會自動在同一個「淹水模擬」Catalog 下建立獨立的 Collection，結構完全一致。
