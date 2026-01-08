# API 與 模組參考 (API Reference)

本頁面列出 STAC Generator 的核心模組與類別說明，供開發者參考。

## 1. Generator Core (`src/generator/`)

### `BaseGenerator`
*   **Path**: `src/generator/base.py`
*   **功能**: 定義生成器的抽象介面。
*   **主要方法**:
    *   `generate()`: 執行生成流程的主要入口。
    *   `_create_collection()`: 建立 STAC Collection 物件。
    *   `_create_item()`: 建立 STAC Item 物件。

### `IntakeXarrayGenerator`
*   **Path**: `src/generator/intake_xarray.py`
*   **繼承自**: `BaseGenerator`
*   **功能**: 專門處理 Intake-Xarray 來源的生成器。
*   **特色**: 整合 `xstac`，在生成過程中動態讀取 Dataset 以豐富 Metadata (Datacube Extension)。

## 2. Adapters (`src/adapters/`)

Adapter 負責將異質的 Source 轉譯為統一的 STAC Item 結構。

### `BaseAdapter`
*   **Path**: `src/adapters/base.py`
*   **功能**: 所有 Adapter 的父類別。
*   **介面**: `get_items() -> Generator[pystac.Item]`

### `GriddedDataAdapter`
*   **Path**: `src/adapters/gridded.py`
*   **用途**: 處理規則網格資料 (Zarr, NetCDF)。
*   **邏輯**:
    1.  解析 `urlpath` glob pattern。
    2.  對每個檔案，嘗試從檔名 regex 提取年份 (`YYYY`)。
    3.  開啟檔案 (`xr.open_dataset`) 讀取真實經緯度與時間範圍。
    4.  產出 STAC Item。

## 3. Main Interface (`src/main.py`)

CLI 的進入點，使用 `Typer` 或 `Argparse` (視實作而定) 處理指令。
*   `build_all()`: 掃描 catalogs 目錄並依序執行生成。
*   `start_server()`: 啟動預覽 Web Server。
