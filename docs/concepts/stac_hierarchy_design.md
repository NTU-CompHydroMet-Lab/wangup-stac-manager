很好，這一步其實就是**把「人類共識層」跟「STAC 機器層」一一對齊**。
我會做三件事：

1. **先給一個「你們現在的邏輯模型」總覽（回答你前面卡住的 catalog / collection / item / asset 問題）**
2. **定義每一個 STAC 層級「需要填什麼資訊、誰負責決定」**（直接可拿去開會）
3. **用你已經列出的資料（QPESUMS、ERA5、Himawari…）示範「實際要填哪些欄位」**

下面全部是 **human-readable markdown，用語偏 formal / team design doc**，但每一欄都能 1-to-1 對到 STAC JSON。

---

# STAC Information Mapping Guide (Lab Agreement Layer)

> Purpose:
> This document defines **what information must be provided at each STAC level**,
> based on our current lab datasets and medallion (Bronze / Silver / Gold) architecture.
>
> It is intended for **team discussion and metadata agreement**, not direct JSON generation.

---

## 0. Mental Model Clarification (重要先對齊)

### 為什麼「catalog 不是 data type」

在 **STAC 官方語意**中：

| Concept        | 是什麼                   | 不是什麼         |
| -------------- | --------------------- | ------------ |
| **Catalog**    | 導覽結構、索引入口             | ❌ 資料類型       |
| **Collection** | 一組同質資料的集合             | ❌ 單一檔案       |
| **Item**       | 一個時空切片 / logical unit | ❌ 一定要是單檔     |
| **Asset**      | 真正的資料或描述檔             | ✅ 檔案、Zarr、DB |

👉 **Data type / Tier / Processing level 都是「屬性（metadata）」而不是階層**

所以你提出的這個結構：

```
catalog (data type)
→ collection (tier)
→ asset (file path)
```

在「人類理解上」合理，但在 **STAC 設計哲學上會卡死**，因為：

* catalog 不能被 query（只負責導航）
* tier 可能跨 collection（同一 collection 有 Bronze + Silver）
* asset 才是真正的 data carrier

---

## 1. Lab-Wide STAC Hierarchy (Agreed Structure)

### Level 1 — STAC Catalog (Lab Entry Point)

**角色定位**

> 「我們這個實驗室有哪些資料？」

**你們目前的實際對應**

* 整個 NAS / Lab Data Universe
* 只會有 **1–2 個 root catalog**

**應填資訊（Minimal, Stable）**

| Field          | 說明                | 誰決定 |
| -------------- | ----------------- | --- |
| `id`           | lab-data-catalog  | 管理者 |
| `description`  | Lab data overview | 管理者 |
| `links`        | 指向各 Collection    | 自動  |
| `stac_version` | 固定                | 系統  |

⚠️ **Catalog 層級不討論 raw / processed / format**

---

## 2. STAC Collection — Dataset Definition Level（最重要）

> **你 markdown 裡每一個「資料集章節」= 一個 Collection**

### Collection 的核心問題

> 「這是一組什麼樣的資料？它的物理與科學邊界是什麼？」

### Collection 層級應填資訊（討論重點）

#### A. Identity & Scope（人類決策）

| Field         | 說明                  | Example              |
| ------------- | ------------------- | -------------------- |
| `id`          | Dataset identifier  | `qpesums-maxdbz`     |
| `title`       | Human-readable name | QPESUMS Radar Mosaic |
| `description` | 科學/業務意義             | Taiwan radar mosaic  |
| `keywords`    | 搜尋用                 | radar, precipitation |

#### B. Spatio-temporal Extent（必填）

| Field                      | 說明        |
| -------------------------- | --------- |
| `extent.spatial.bbox`      | 資料整體 bbox |
| `extent.temporal.interval` | 最早～最晚時間   |

👉 **這一層不管實際切幾年，只定「宇宙邊界」**

#### C. Processing / Tier Metadata（你們很在意的）

這裡是 **medallion architecture 的正確放置點**：

| Field                            | Value                  |
| -------------------------------- | ---------------------- |
| `properties["processing:level"]` | bronze / silver / gold |
| `properties["data:format"]`      | zarr, hdf5, sqlite     |
| `properties["data:source"]`      | CWA, ECMWF, JAXA       |

⚠️

* **同一 Collection 可以有多個 processing level**
* 不要用 Collection 分 tier

---

## 3. STAC Item — Logical Data Unit（你目前最困惑的地方）

### Item 不等於「檔案數」

**Item 回答的是：**

> 「一個可以被當成『一次分析單位』的資料是什麼？」

### 對你目前資料的建議原則（很關鍵）

| 情境          | Item 建議               |
| ----------- | --------------------- |
| 一年一個 Zarr   | ✅ **一年 = 1 Item**     |
| 不想巢狀 folder | ✅ Item 直接指向 Zarr root |
| 不想頻繁更新      | ✅ Item metadata 穩定    |

👉 **Item 不需要對應每天 / 每小時**

---

### Item 層級應填資訊

| Field            | 說明            | Example                |
| ---------------- | ------------- | ---------------------- |
| `id`             | 唯一識別          | `qpesums-2019`         |
| `datetime`       | 代表時間          | `2019-01-01T00:00:00Z` |
| `start_datetime` | 起始            | 2019-01-01             |
| `end_datetime`   | 結束            | 2019-12-31             |
| `geometry`       | 可省略或 bbox     | Taiwan bbox            |
| `collection`     | 所屬 collection | qpesums                |

⚠️

* Zarr 裡面有多時間步 ≠ 不能用 Item
* Item 是 **logical handle**

---

## 4. Asset — Actual Data Pointer（完全不抽象）

### Asset 就是你 NAS 上的東西

**Asset 回答的是：**

> 「資料實際在哪？怎麼讀？」

### Asset 應填資訊

| Field         | 說明              | Example                 |
| ------------- | --------------- | ----------------------- |
| `href`        | 路徑              | `/NAS/data/_Silver/...` |
| `type`        | media type      | `application/vnd+zarr`  |
| `roles`       | data / metadata | data                    |
| `title`       | Optional        | Zarr store              |
| `description` | Optional        | Chunked yearly data     |

---

## 5. Mapping Your Existing Datasets (Checklist Style)

下面是 **你可以直接貼給團隊填的 checklist**。

---

### 📡 QPESUMS — Radar Mosaic

#### Collection

* [ ] id
* [ ] description
* [ ] bbox (Taiwan)
* [ ] temporal extent (2013–2023)
* [ ] keywords
* [ ] data source (CWA)

#### Items (Silver)

* [ ] Item granularity: **1 year = 1 item**
* [ ] datetime / start / end
* [ ] geometry: reuse collection bbox

#### Assets

* [ ] Zarr path
* [ ] media type
* [ ] processing:level = silver

---

### 🌪️ ERA5 Convection

#### Collection

* [ ] Scope: East Asia convection subset
* [ ] Clarify if **global raw ERA5** is same or different collection
* [ ] processing:level allowed: bronze + silver?

#### Items

* [ ] Yearly or multi-year?
* [ ] Chunk strategy documented (not enforced)

---

### 🛰️ Himawari L2

#### Collection

* [ ] Product level (L2)
* [ ] Spatial resolution (0.05°)
* [ ] Temporal resolution (10-min)

#### Items

* [ ] 1 year per item (recommended)
* [ ] Avoid day-level explosion

---

### ☔ IMERG

#### Decision Needed (Collection level)

* [ ] One collection or split by run (Early/Late/Final)?
* [ ] processing:level mapping

---

### 🌧️ Rain Gauge (Gold)

#### Special Note

* Item can be **“station dataset snapshot”**
* Asset = SQLite DB
* Temporal extent still required

---

## 6. Key Design Decisions (Explicit for Meeting)

You can literally put this slide up:

1. **Collection defines scientific meaning, not storage**
2. **Tier is metadata, not hierarchy**
3. **Item granularity chosen to minimize churn**
4. **Asset points to stable paths only**
5. **STAC is an index, not a file manager**

---

## 7. Recommended Next Concrete Step

I strongly suggest：

> **Pick ONE dataset (QPESUMS)**
> → write **1 Collection JSON + 1 Item JSON by hand**
> → everyone sees「原來 STAC 是這樣用的」

如果你要，我可以下一步直接幫你：

* 寫 **QPESUMS Collection.json（帶註解）**
* 或幫你把 **這份 markdown 改成「團隊填表版」**
* 或幫你設計 **Item granularity decision flowchart**

你選一個方向，我接著下去。
