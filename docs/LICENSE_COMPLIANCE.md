# 專案版權合規與致謝記錄 (License Compliance & Acknowledgements)

為了確保未來將 **Hermes Intelligence OS** 專案上傳至 GitHub 時符合著作權法規與開源社群規範，本文件記錄了我們在設計過程中參考的開源專案、其授權協議（License），以及對應的版權合規行動指南。

---

## 1. 參考專案授權資訊

本專案在規劃與架構設計中，參考了以下兩個 GitHub 開源專案的核心概念與技術實踐：

### 📰 1. AI-News-Briefing
*   **來源連結**：[hoangsonww/AI-News-Briefing](https://github.com/hoangsonww/AI-News-Briefing)
*   **授權協議**：**MIT License** (極為寬容的開源協議)
*   **主要參考概念**：
    *   多 AI 引擎的降級與備用路由機制（Multi-LLM Fallback）。
    *   AI 整理品質評估與漂移檢測框架（Quality Eval Harness）。
    *   將簡報輸出為帶有 `[[wikilinks]]` 的 Obsidian 筆記，以自動構建知識圖譜的構想。

### 🎓 2. ArxivDigest
*   **來源連結**：[AutoLLM/ArxivDigest](https://github.com/AutoLLM/ArxivDigest)
*   **授權協議**：**MIT License** (極為寬容的開源協議)
*   **主要參考概念**：
    *   基於自然語言研究興趣描述，利用 LLM 進行 1-10 分的語意相關性打分與過濾管道。
    *   結合 GitHub Actions 與免費郵件發送服務（如 SendGrid）實現零伺服器成本的自動化運行方案。

---

## 2. 著作權與上傳 GitHub 的合規評估

由於上述兩個專案均採用 **MIT 授權條款**，其條款極度自由，允許商業使用、修改與再分發。我們上傳 GitHub 的合規性取決於我們的**實作方式**：

### 情況 A：僅參考設計概念，程式碼自行撰寫（目前狀態）
*   **著作權評估**：**完全沒有法律問題**。著作權法保護的是「具體的表達形式（程式碼實作）」，而不保護「抽象的概念或架構想法」。由於 Hermes 的 SQLite 記憶體資料庫結構、Notion/Obsidian 雙向同步同步引擎都是由我們自行開發，因此不構成任何侵權。
*   **建議行動**：在專案的 `README.md` 或本文件中列出致謝即可，非法律強制，但符合開源社群禮儀。

### 情況 B：直接複製或修改了對方的程式碼（如腳本、Prompts 或打分演算法）
*   **著作權評估**：**合法，但必須遵守 MIT 授權的唯一限制**：必須在代碼中保留原作者的著作權聲明與許可聲明。
*   **建議行動**：
    1.  如果在專案中直接引入了對方的程式碼檔案，請勿刪除該檔案頂部的原作者 Copyright 註解（例如 `# Copyright (c) 202X hoangsonww`）。
    2.  如果大幅度整合了程式碼，可在本專案根目錄建立 `LICENSE` 檔案（若我們也採用 MIT 授權），並在專案中附帶原專案的授權聲明複本。

---

## 3. 未來上傳 GitHub 的合規行動清單 (Checklist)

當我們準備好將本專案推送到公開的 GitHub 倉庫時，請務必確認以下事項：

*   [x] **清理敏感資訊（Security Audit）**：`.env`、SQLite 資料庫檔案、logs、exports、generated output 已由 `.gitignore` 排除，並新增 `scripts/pre_publish_audit.py` 作為發布前掃描。
*   [x] **確認專案授權**：根目錄已新增 `LICENSE`，Hermes 採用與參考專案相容的 **MIT License**。
*   [x] **保留致謝聲明**：專案首頁 `README.md` 底部已加入 `Acknowledgements`（致謝）區塊，列出這兩個啟發設計的專案。

---

### 📝 附錄：MIT 授權許可文字參考
> "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files... subject to the following conditions:
> **The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.**"
