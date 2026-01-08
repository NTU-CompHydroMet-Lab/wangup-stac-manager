# STAC Generator Project Documentation

歡迎來到 STAC Generator 專案文件中心。本專案旨在建立一套自動化流程，將異質格式的氣象資料（Zarr, NetCDF, HDF5）轉換為標準化的 **SpatioTemporal Asset Catalog (STAC)** 格式。

## 文件導覽

### 核心概念 (Concepts)
了解本專案的設計哲學與核心邏輯。
- [架構總覽 (Architecture)](architecture.md): 系統流程圖、核心模組與設計目標。
- [Intake 與 STAC 對應 (Mapping)](concepts/mapping.md): 了解 Intake Catalog 如何映射至 STAC Collection/Item。

### 使用指南 (Guides)
一步步教你如何安裝、執行與擴充專案。
- [快速入門 (Getting Started)](guides/getting_started.md): 環境建置與 CLI 基礎指令。
- [新增資料集 (Adding Datasets)](guides/adding_datasets.md): 如何撰寫 Intake Catalog 並選擇適合的 Adapter。

### 開發參考 (Reference)
- [API 參考 (API Reference)](reference/api.md): 核心類別與函式說明。
- [專案結構 (Project Logic)](concepts/project_logic.md): 深入程式碼結構。

---

## 專案目標

1.  **標準化索引**: 透過 STAC API 統一查詢 Zarr, NetCDF 等且不同來源的資料。
2.  **豐富 Metadata**: 自動提取 Datacube 資訊 (`xstac` 整合)。
3.  **可視化**: 支援 STAC Browser 直接瀏覽。

## 快速連結

- [Source Code (src/)](../src)
- [Catalogs (catalogs/)](../catalogs)
- [Project Readme](../README.md)
