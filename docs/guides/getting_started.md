# 快速入門 (Getting Started)

本指南將引導您如何在本地端建立開發環境並執行 STAC Generator。

## 環境需求

*   **OS**: Linux (Ubuntu 20.04+ Recommended)
*   **Python**: 3.10+
*   **Package Manager**: [uv](https://github.com/astral-sh/uv) (推薦) 或標準 pip

## 安裝步驟

1.  **Clone 專案**
    ```bash
    git clone <repository-url>
    cd stac
    ```

2.  **建立虛擬環境與安裝依賴 (使用 uv)**
    本專案使用 `uv` 進行依賴管理，速度極快且穩定。
    ```bash
    # 建立 venv
    uv venv

    # 啟動 venv
    source .venv/bin/activate

    # 安裝依賴 (讀取 pyproject.toml)
    uv pip install -r pyproject.toml
    # 或者如果使用 uv sync
    uv sync
    ```

## 執行 STAC Generator

專案提供了一個 CLI 入口 `src/main.py` 來管理所有操作。

### 1. 建置 Catalog (Build)
此指令會讀取 `catalogs/` 下的所有 YAML 定義，並在 `stac_output/` 生成靜態 JSON 檔案。

```bash
python src/main.py build
```

*   **輸入**: `catalogs/*.yaml`
*   **輸出**: `stac_output/` (包含 root catalog, collections, items)

### 2. 啟動預覽伺服器 (Serve)
啟動一個輕量級的 HTTP Server 來預覽生成的 STAC Catalog。

```bash
python src/main.py serve
```
*   預設 Port: `8000`
*   此指令通常會同時啟動 `stac-browser` (若有設定) 或僅提供靜態檔案存取。

### 3. 清理輸出 (Clean)
若需要完全重跑，可以手動刪除輸出目錄 (或使用對應的 clean 指令若有實作)。

```bash
rm -rf stac_output/*
```

---

## 下一步

*   嘗試 [新增一個資料集](adding_datasets.md) 到系統中。
*   了解 [Intake 與 STAC 的對應邏輯](../concepts/mapping.md)。
