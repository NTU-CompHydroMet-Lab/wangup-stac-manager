# 新增資料集指南 (Adding Datasets)

要在本系統中新增一個資料集，您主要需要撰寫 **Intake Catalog YAML**。系統會自動偵測並生成對應的 STAC Collection。

## 流程總覽

1.  **準備資料**: 確認資料位於 NAS 上，且路徑規律 (例如按年份分資料夾)。
2.  **撰寫 YAML**: 在 `catalogs/` 目錄下新增 `.yaml` 檔案。
3.  **測試**: 執行 `python src/main.py build` 生成 STAC。
4.  **驗證**: 檢查生成的 JSON 是否包含正確的 Metadata。

---

## 步驟詳解

### 1. 撰寫 Intake YAML

在 `catalogs/` 目錄中建立一個新檔案，例如 `catalogs/my_new_data.yaml`。
Intake Source 的名稱 (Key) 將直接成為 STAC Collection ID。

```yaml
sources:
  # STAC Collection ID: "my_custom_dataset"
  my_custom_dataset:
    description: "這是一個範例資料集"
    driver: zarr  # 或 netcdf, rasterio
    args:
      # 支援 glob pattern
      urlpath: "/home/sungche/data/MyData/*.zarr"
      
    metadata:
      # [必要] 指定使用的 Adapter 類型
      stac_adapter: "gridded"  # 對應 src/adapters/gridded.py
      
      # [STAC Collection Metadata]
      title: "My Custom Dataset Global 1km"
      license: "CC-BY-4.0"
      providers:
        - name: "NTU Lab"
          roles: ["producer", "host"]
          url: "https://example.com"
          
      # [STAC Summaries]
      keywords: ["temperature", "global"]
```

### 2. 選擇 Adapter (`stac_adapter`)

在 `metadata` 中必須指定 `stac_adapter` 欄位，這決定了系統如何讀取您的資料並切分 Item。

| Adapter 名稱 | 適用場景 | Item 切分邏輯 |
| --- | --- | --- |
| `gridded` | 大部分網格資料 (Zarr, NetCDF) | **一年一個 Item** (依照檔名中的年份或檔案屬性) |
| `cwa` | 氣象局測站資料 | **單一 Item** (Snapshot) |

### 3. 設定樣板 (Templating) - 進階

若您的檔案路徑包含日期結構，Intake 支援 Python format string。

```yaml
args:
  urlpath: "/data/era5/{year}/{month}.nc"
```
*注意：目前的 `GriddedDataAdapter` 主要使用 glob 抓取檔案列表，再從檔名 regex 解析年份，因此建議直接使用 glob pattern (`*.zarr`)。*

### 4. 處理 Metadata 豐富化 (Enrichment)

系統會自動使用 `xstac` 讀取您的資料檔案。請確保您的資料檔案 (Zarr/NetCDF) 具備標準的 CF-Conventions 屬性，例如：
*   `standard_name` or `long_name` (用於 Variable 描述)
*   `units` (單位)
*   `coordinates` (經緯度定義)

如果有缺漏，STAC Generator 可能會發出警告，但仍會嘗試生成基本的時空範圍。

---

## 常見問題

### Q: 我的資料不是按年份分檔，而是單一大檔，怎麼辦？
A: 使用 `gridded` adapter 時，如果檔名沒有年份，它會嘗試讀取檔案內的時間維度。如果是一個跨多年的大檔案，它可能會生成一個跨多年的單一 Item，或您需要修改 Adapter 邏輯來支援切片。

### Q: 如何排除特定檔案？
A: 在 YAML 的 `urlpath` 使用更精確的 glob pattern，或是在檔案系統中將不需索引的檔案移走。
