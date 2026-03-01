# Flood Modelling 資料盤點與重整建議

## 1) 盤點範圍
- 根目錄：`data/flood_modelling_20210604`
- 檔案總數：13
- 總容量：約 23.9 GB（以 `du -sh` 估算）

## 2) 目錄結構（現況）
```text
data/flood_modelling_20210604/
├── 輸入雨量/
│   ├── WGS84/
│   │   └── 2021-06-04-0000~2021-06-08-0000QPESUMS.nc
│   └── TWD97/
│       └── 0604_TWD97_Clean_V5.nc
├── IOT_catch/
│   ├── 20210604比對分析.xlsx
│   └── IOT_shpfile/
│       ├── YS_IOT.shp/.shx/.dbf/.prj/.cpg
│       └── YS_IOT.qmd
└── 輸出成果/
    └── output/
        ├── FM_model_map.nc
        ├── FM_model_fou.nc
        ├── FM_model_his.nc
        └── FM_model.dia
```

## 3) 檔案與資料型態摘要
| 類型 | 數量 | 代表檔案 | 特徵 |
|---|---:|---|---|
| NetCDF (`.nc`) | 5 | `FM_model_map.nc` | 主要科學資料，最大檔案在模擬輸出 |
| Shapefile 套件 | 5 | `YS_IOT.shp/.dbf/...` | IoT 點位圖資（EPSG:3826） |
| Excel | 1 | `20210604比對分析.xlsx` | 比對分析表（非機器可讀 metadata） |
| Delft/模型設定 | 1 | `FM_model.dia` | 模型相關輸出/設定檔 |
| QGIS Metadata | 1 | `YS_IOT.qmd` | GIS 軟體側 metadata |

## 4) 容量分布（重點）
- `輸出成果/`: 約 23 GB（瓶頸）
  - `FM_model_map.nc`: 約 22 GB（主要壓力來源）
  - `FM_model_fou.nc`: 約 666 MB
  - `FM_model_his.nc`: 約 36 KB
- `輸入雨量/`: 約 194 MB
- `IOT_catch/`: 約 752 KB

## 5) 已辨識出的資料語意
### 5.1 輸入雨量
- `WGS84` 檔：
  - 變數：`precipitation_observed(time, y, x)`
  - 時間維度：98
  - CRS：EPSG:4326
  - 全域屬性含 `title=QPESUMS Open Data`
- `TWD97` 檔：
  - 變數：`rainfall(time, y, x)`
  - 時間維度：98
  - CRS：EPSG:3826

### 5.2 IoT 點位
- `YS_IOT.shp`：
  - 幾何型態：Point
  - Feature 數：88
  - CRS：EPSG:3826 (TWD97/TM2 zone 121)
  - 屬性欄位：`Name`, `x`, `y`, `field_4`

### 5.3 模擬輸出
- `FM_model_map.nc`（22 GB）：
  - CF/UGRID 結構，含 1D/2D mesh 與 `time` 維度
  - 含水位/水深/流速/流量等時序變數（`Mesh2d_*`, `mesh1d_*`）
  - `time_coverage_start/end`: 2021-06-04 ~ 2021-06-08
- `FM_model_his.nc`：
  - 各類 water balance 時序摘要（時間序列統計）
- `FM_model_fou.nc`：
  - 網格/幾何與頻域或模型場資訊（同為 CF/UGRID 類型）

## 6) 現行存法的主要問題
- 命名語意混雜（中文目錄 + 英文檔名 + 版本規則不一致），不利自動化。
- 「輸入/輸出/分析表」混在同一層，缺乏 dataset-level manifest。
- 大檔（22 GB）單檔 NetCDF 不利切片存取、版本控管與雲端分發。
- 缺少 machine-readable 的資料字典（目前 metadata 多在檔頭、qmd、xlsx）。
- 同一事件（20210604）缺少固定識別碼與處理版本（processing version）。

## 7) 建議重整方向（先可落地，再優化）
## 7.1 目錄分層（建議）
```text
data/flood_modelling/
└── events/
    └── event_20210604/
        ├── inputs/
        │   ├── rainfall/
        │   │   ├── qpesums_wgs84_v1.nc
        │   │   └── qpesums_twd97_v1.nc
        │   └── boundary/
        ├── context/
        │   ├── iot_stations/
        │   │   ├── iot_stations.gpkg
        │   │   └── iot_stations.csv
        │   └── analysis/
        │       └── comparison_20210604.xlsx
        ├── outputs/
        │   ├── map/
        │   │   └── fm_map.zarr
        │   ├── summary/
        │   │   └── fm_his.nc
        │   └── mesh/
        │       └── fm_fou.nc
        └── metadata/
            ├── manifest.yaml
            └── provenance.yaml
```

## 7.2 格式策略（建議）
- `FM_model_map.nc`：
  - 優先轉為 Zarr（時間/空間分塊），利於雲端與 API 存取。
  - 原始 `.nc` 留作 archive（cold storage），不做主服務來源。
- Shapefile：
  - 主格式改為 `GeoPackage (.gpkg)`（單檔、欄位編碼更穩定）。
  - 若需互通可保留 `.shp` 作 legacy export。
- Excel：
  - 將核心欄位落成 `CSV` 或 `Parquet`，再把 `.xlsx` 當附件。

## 7.3 STAC 建議映射
- 新增一個 Flood Modelling 的 parent catalog（例如 `flood_modelling`）。
- 以「事件」作 Collection（`event_20210604`）。
- Collection 內 Item 可分為：
  - `rainfall_input_wgs84`
  - `rainfall_input_twd97`
  - `iot_station_points`
  - `fm_map`（大檔主產物）
  - `fm_his`（摘要時序）
  - `fm_fou`（網格/幾何輸出）
- 資產角色建議：
  - `data`, `metadata`, `visual`, `analysis`, `model-output`

## 8) 建議執行順序（低風險）
1. 先做 metadata 清冊：建立 `manifest.yaml`（每個檔案的 id/type/crs/time/size/checksum）。
2. 將 `YS_IOT.*` 轉 `iot_stations.gpkg`，並產生 `iot_stations.csv`。
3. 將 `FM_model_map.nc` 轉為 `fm_map.zarr`（保留原檔）。
4. 建立 `config/catalogs/flood_modelling_intake_catalog.yaml` 並加入 `config/main.yaml` target。
5. 先只上架 `inputs + his + iot`，確認 STAC 流程後再上 `fm_map.zarr`。

## 9) 待確認事項（進入實作前）
- 事件命名規範：`event_YYYYMMDD` 是否固定？
- `FM_model_fou.nc` 在業務語意上的正式名稱與用途（mesh? boundary? 頻域?）。
- `FM_model_map` 的對外服務需求：全量下載、子區域切片、還是時間抽樣？
- 是否要維持「中英混合目錄名」；建議對外 STAC id 改全英文 snake_case。
