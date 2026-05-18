# FinReg RAG — 银行制度文档智能问答与审查系统
  Banking Regulation Document Intelligent Q&A and Audit System
> 基于 RAG + 大模型的银行制度文档智能处理平台，面向金融机构合规与知识管理场景
> An LLM-based RAG platform for intelligent processing of banking regulatory documents, tailored for financial compliance and knowledge management.
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 目录/Table of Contents

- [项目定位/project-positioning](#项目定位)
- [核心功能/core-features](#核心功能)
- [快速开始/quick-start](#快速开始)
- [使用示例/usage-examples](#使用示例)
- [RAG 智能处理流水线/rag-pipeline](#rag-智能处理流水线)
- [架构总览/architecture-overview](#架构总览)
- [技术栈/technical-stack](#技术栈)
- [API 端点/api-endpoints](#api-端点)
- [配置参考/configuration-reference](#配置参考)
- [项目结构/project-structure](#项目结构)
- [安全设计/security-design](#安全设计)

---

## 项目定位 / Project Positioning

银行日常经营需要处理海量政策文件、监管制度与业务文档。FinReg RAG 聚焦**大模型与金融专业场景的深度融合**，运用 RAG（检索增强生成）技术，实现以下核心能力：

| 能力 | 场景 | 效果 |
|------|------|------|
| **制度文档问答** | 索引入库 → 检索条款 → 生成精准回答 | "现金交易超多少需上报？" → "根据制度第三章第十五条，单笔超 **20万元（含）**…" |
| **文档智能审查** | 对照规范逐条审查 → 标注风险点 → 给出修改建议 | 上传报告 → 合规风险评级 + 不合规条款清单 + 逐条修改建议 |
| **文档智能分类** | 自动识别文档类型 → 提取关键信息 → 评估风险等级 | 粘贴文档 → 文档类型、关键词、摘要、风险等级一键输出 |
| **代码生成** | 自然语言 → SQL/Python + 安全验证 + 沙箱执行 | "统计可疑交易 TOP10 分行" → 可执行 SQL + 验证结果 |

所有操作通过 **Web Dashboard 可视化界面**完成，无需命令行。

---

## 核心功能

### 1. 制度文档问答

基于 ChromaDB 向量检索 + LLM 的智能问答系统。

**工作流程：**
1. 制度文档入库（拖拽上传 / 文件夹批量导入 / 爬取网页 / 手动粘贴）
2. `sentence-transformers` 将文档块编码为 384 维向量，存入 ChromaDB
3. 用户提问 → 查询向量化 → ChromaDB 余弦相似度检索 Top-5 相关文档块
4. 检索结果注入制度专家 Prompt → LLM 生成精准回答
5. 回答附带引用来源（URL + 相似度得分）

**特性：**
- 仅基于提供的文档上下文回答，不编造信息
- 文档中无相关信息时明确提示用户
- 涉及金额、比例、时限等关键数字时精确引用
- 支持中文问答

### 2. 文档智能审查

对照知识库中的制度规范，逐条审查提交文档的合规性。

**输出内容包括：**
- 合规风险评级（高 / 中 / 低）
- 逐条审查结果（合规 / 不合规 / 不适用），含图标区分
- 每项的具体违规描述和制度依据
- 修改建议
- 整体审查总结

> 审查结果经过归一化层处理，自动适配不同 LLM 的 JSON 输出格式差异。

### 3. 文档智能分类

自动识别文档类型、提取关键信息、评估风险等级。

**输出内容：** 文档类型、分类、关键词列表、内容摘要、生效日期、风险等级、关键条款（含重要性标注）

### 4. 代码生成（SQL / Python）

用自然语言生成银行金融场景的代码，含安全验证和沙箱执行。

**4 个内置银行场景（10 张业务表）：**

| 场景 | 表数 | 包含表 |
|------|------|--------|
| 客户账户管理 | 3 | customers, accounts, transactions |
| 风险监控 | 3 | suspicious_transactions, large_transaction_reports, sanctions_screening |
| 贷款组合 | 2 | loans, loan_repayments |
| 贸易融资 | 2 | letters_of_credit, trade_finance_limits |

**代码生成流程：**
1. 选择银行场景 → 自动加载对应表结构（DDL）
2. 用自然语言描述需求
3. LLM 生成代码（RAG 上下文增强可选）
4. 安全验证（SQL 语法 + 9 类危险操作拦截 / Python AST + 15+ 敏感调用拦截）
5. 沙箱隔离执行（SQLite 内存数据库 / 临时文件）
6. 返回代码 + 验证结果 + 执行结果

> **注意：** 代码生成不依赖知识库。LLM（DeepSeek / GPT-4）在训练时已掌握 SQL 和 Python，可独立生成代码。RAG 知识库的作用是注入内部规范或特定框架的用法以提升生成质量。通用模式（无表结构）下沙箱自动跳过并给出提示；选择银行场景后沙箱正常执行。

### 5. 知识库管理

**双集合架构：** 系统内置两个独立的向量知识库集合，分开管理不同类型的文档。

| 集合 | 用途 | 典型内容 |
|------|------|---------|
| `regulatory_docs` | 制度文档库 | 银行监管政策、法规、制度文件、合规报告 |
| `code_docs` | 代码文档库 | SQL/Python 代码示例、技术文档、框架规范 |

**5 种入库方式：**

| 方式 | 适用场景 |
|------|---------|
| **拖拽上传** | 单个或少量文件（.txt .md .docx .py .sql 等 20+ 格式），拖入即入库 |
| **文件夹批量导入** | 大量文件（如 895 份制度文档），指定路径一键全量导入 |
| **爬取网站** | 制度/代码文档网站，自动抓取网页内容并索引 |
| **手动粘贴** | 临时文本片段，直接粘贴入库 |
| **API 调用** | 程序化批量索引入库 |

**文档管理：**
- Dashboard「Document Library」面板查看所有已索引文档
- 支持按集合切换、逐条删除、一键清空
- 显示文件名、来源 URL、索引块数

### 6. 操作历史

所有操作（问答、审查、分类、代码生成）自动记录到 `metrics_history.json`，服务重启不丢失。

- **首页 Activity History 面板** — 显示最近 30 条记录（类型、描述、Token 消耗、时间戳）
- Token 消耗 KPI 实时累计
- 支持一键清空历史记录

### 7. Web Dashboard 操作台

访问 `http://localhost:8000` 进入可视化界面：

```
左侧导航栏：
  📊 系统总览  → KPI 卡片（双库分离统计）+ RAG 流水线动画 + 操作历史 + 快速入口
  💬 制度问答  → 输入问题，AI 检索制度文档并生成回答（含参考来源）
  🔍 文档审查  → 粘贴文档，AI 对照制度规范逐条审查合规性
  📚 知识管理  → 拖拽上传 / 文件夹批量导入 / 爬取网站 / 语义搜索 / 文档库管理
  ⚡ 代码生成  → 银行场景 SQL/Python 生成 + 安全验证 + 沙箱执行
  🏷️ 智能分类  → 自动识别文档类型、提取关键信息、评估风险等级
```

**Dashboard 特性：**
- 纯原生 HTML/CSS/JS，零前端框架依赖，打开浏览器即用
- 中英文切换（侧栏底部 `中文 | EN`），偏好保存到 localStorage
- 精致商务风格，Cormorant Garamond 衬线标题 + DM Sans 无衬线正文
- KPI 数字平滑滚动动画、流水线步骤高亮动画
- 沙箱执行结果直观展示（成功/跳过/失败 + 友好提示）

---

## 快速开始

### 环境要求

- Python 3.10+
- OpenAI 兼容 API Key（支持 DeepSeek / GPT / 本地 vLLM）

### 1. 安装依赖

```bash
cd rag-code-gen
pip install -e ".[dev]"
```

首次运行时会自动下载嵌入模型 `all-MiniLM-L6-v2`（约 90MB）。

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```ini
# 必填：LLM API 密钥
OPENAI_API_KEY=sk-your-api-key-here

# 可选：API 端点（默认 DeepSeek）
OPENAI_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

### 3. 启动服务

```bash
python -m src.app
```

打开浏览器访问 **http://localhost:8000** 进入 Dashboard。

### 4. 索引导入文档

首次使用需要导入制度文档，推荐方式：

- **文件夹批量导入**：知识管理 → 输入 `./赛题制度文档/` → 选择「制度文档库」→ 批量导入
- **拖拽上传**：知识管理 → 将文件直接拖入上传区

### 5. 验证

```bash
curl http://localhost:8000/health
# 预期: {"status":"ok","service":"finreg-rag"}
```

---

## 使用示例

### 制度文档问答

```bash
# 1. 索引文档
curl -X POST http://localhost:8000/api/v1/documents/index \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "content": "中国人民银行令〔2020〕第1号：金融机构反洗钱监督管理办法。第十七条 单笔或者当日累计人民币交易20万元以上的现金收支，应当向中国反洗钱监测分析中心报告。",
      "url": "https://example.com/aml-regulation",
      "metadata": {"source": "manual"}
    }]
  }'

# 2. 提问
curl -X POST http://localhost:8000/api/v1/documents/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "大额交易的上报标准是什么？"}'
```

**响应示例：**
```json
{
  "question": "大额交易的上报标准是什么？",
  "answer": "根据《中国人民银行令〔2020〕第1号》第十七条规定，单笔或者当日累计人民币交易20万元以上的现金收支，金融机构应当向中国反洗钱监测分析中心报告。",
  "model": "deepseek-v4-flash",
  "sources": [
    {"document": "中国人民银行令〔2020〕第1号...单笔或者当日累计人民币交易20万元以上...", "score": 0.8562}
  ],
  "tokens_used": 312
}
```

### 文档智能审查

```bash
curl -X POST http://localhost:8000/api/v1/documents/review \
  -H "Content-Type: application/json" \
  -d '{
    "title": "2024Q3客户尽职调查报告",
    "content": "本报告记录了500名客户的KYC验证情况。但15个企业账户的受益所有人未完成验证。"
  }'
```

**响应示例：**
```json
{
  "review_result": {
    "risk_level": "中",
    "items": [
      {
        "status": "不合规",
        "clause": "金融机构应建立客户身份识别制度，包括识别受益所有人",
        "detail": "15个企业账户的受益所有人未验证",
        "suggestion": "立即补办受益所有人验证，获取最终控制人身份信息"
      }
    ],
    "summary": "主要发现：15个企业账户未验证受益所有人，违反制度要求。整体风险评级为中等。"
  }
}
```

### 文档智能分类

```bash
curl -X POST http://localhost:8000/api/v1/documents/classify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "反洗钱管理办法2024版",
    "content": "本文档规定了金融机构的反洗钱和反恐融资政策，包括客户尽职调查程序、大额交易报告标准（超20万元5个工作日内报告）、可疑交易立即报告等要求。"
  }'
```

### SQL 代码生成

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/ask \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "统计每个客户拥有的账户数量，按账户数量降序排列",
    "language": "sql",
    "table_schema": "CREATE TABLE customers (customer_id BIGINT PRIMARY KEY, full_name VARCHAR(200)); CREATE TABLE accounts (account_id BIGINT PRIMARY KEY, customer_id BIGINT, balance DECIMAL(20,4));"
  }'
```

**响应示例：**
```json
{
  "generated_code": "SELECT c.customer_id, c.full_name, COUNT(a.account_id) AS account_count FROM customers c LEFT JOIN accounts a ON c.customer_id = a.customer_id GROUP BY c.customer_id, c.full_name ORDER BY account_count DESC;",
  "validation": {"is_valid": true, "is_safe": true, "errors": []},
  "sandbox_execution": {"success": true, "output": "Rows: 0\n"}
}
```

> 通用模式（无表结构）下沙箱自动跳过并显示提示，需选择银行场景后沙箱正常建表执行。

### Python 代码生成

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/ask \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "创建函数计算两个数的最大公约数",
    "language": "python",
    "table_schema": ""
  }'
```

### 代码安全验证

```bash
# 拦截危险 SQL
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"code": "DROP TABLE customers;", "language": "sql"}'
# → {"is_valid": false, "is_safe": false, "errors": ["Security: forbidden keyword 'DROP' detected"]}

# 拦截危险 Python
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"code": "import os", "language": "python"}'
# → {"is_valid": false, "is_safe": false, "errors": ["Security: forbidden import 'os'"]}
```

### 沙箱执行

```bash
curl -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "SELECT 1+1 AS result;", "language": "sql", "table_schema": ""}'
```

### 文件夹批量导入

```bash
# 导入制度文档
curl -X POST http://localhost:8000/api/v1/documents/import-folder \
  -H "Content-Type: application/json" \
  -d '{"path": "./赛题制度文档/", "collection": "regulatory_docs"}'

# 导入代码文件
curl -X POST http://localhost:8000/api/v1/documents/import-folder \
  -H "Content-Type: application/json" \
  -d '{"path": "./src/", "collection": "code_docs"}'
```

支持文件格式：`.txt .md .docx .csv .json .py .sql .js .ts .java .go .sh .cpp .h .html .css .yaml .yml .toml .ini .cfg`

### 文件上传

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@policy.txt" \
  -F "collection=regulatory_docs"
```

### 爬取并入库

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/crawl-and-index \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/regulations/", "max_pages": 10, "collection": "regulatory_docs"}'
```

### 语义搜索

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "反洗钱大额交易报告标准", "top_k": 5, "filter_type": "regulatory_docs"}'
```

### 操作历史

```bash
# 查看历史
curl http://localhost:8000/api/v1/history?limit=30

# 清空历史
curl -X DELETE http://localhost:8000/api/v1/history
```

---

## RAG 智能处理流水线

```
您的制度文档                        您的业务问题
     │                                   │
     ▼                                   ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ ① 文档上传 │ → │ ② 智能分块 │ → │ ③ 向量嵌入 │ → │ ④ 语义检索 │ → │ ⑤ LLM生成 │
│  拖拽/粘贴 │    │ 每块~1000  │    │ 384维     │    │ Cosine    │    │ 7套Prompt │
│  文件夹导入 │    │ 字符+重叠  │    │ 向量化    │    │ 相似度匹配 │    │ 模板驱动   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └─────┬────┘
                                                                      │
                                                         ┌────────────┘
                                                         ▼
                                                  ┌──────────┐    ┌──────────┐
                                                  │ ⑥ 安全验证 │ → │ ⑦ 沙箱执行 │
                                                  │ SQL语法/   │    │ 隔离环境   │
                                                  │ Python AST │    │ 实际运行   │
                                                  └──────────┘    └─────┬────┘
                                                                        │
                                                                        ▼
                                                                 ┌──────────┐
                                                                 │ ⑧ 结果输出 │
                                                                 │ 制度问答/  │
                                                                 │ 合规审查/  │
                                                                 │ 代码+指标  │
                                                                 └──────────┘
```

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    FinReg RAG 系统架构                          │
├─────────────┬─────────────┬──────────────┬─────────────────────┤
│  数据采集层  │  知识检索层  │   生成与推理层  │     验证与输出层     │
├─────────────┼─────────────┼──────────────┼─────────────────────┤
│ 拖拽上传     │ Chunker     │ OpenAI兼容    │ SQLValidator       │
│ 文件夹导入   │  文档分块    │  DeepSeek     │  语法+安全审计      │
│ DocCrawler  │ Embedding   │  GPT-4o      │ PythonValidator    │
│  网页爬虫    │  向量嵌入    │  本地vLLM     │  AST+敏感拦截       │
│ CodeCrawler │ VectorStore │ 7套Prompt模板 │ CodeSandbox       │
│  代码爬虫    │  ChromaDB   │ 制度问答/审查  │  隔离执行环境       │
│             │ 双集合分离   │ 归一化层      │                   │
├─────────────┴─────────────┴──────────────┴─────────────────────┤
│                    Web Dashboard 可视化界面                     │
│     系统总览 │ 制度问答 │ 文档审查 │ 知识管理 │ 代码生成 │ 智能分类    │
│               中英双语切换 · 操作历史 · KPI 实时统计               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层次 | 技术 | 用途 |
|------|------|------|
| **Web 框架** | FastAPI + Uvicorn | 后端 API 服务 + Dashboard 托管 |
| **前端** | 原生 HTML/CSS/JS（零依赖） | Dashboard 可视化操作界面，中英双语 |
| **LLM 接入** | OpenAI SDK | 调用 DeepSeek/GPT/vLLM 进行问答、审查、代码生成 |
| **嵌入模型** | sentence-transformers (all-MiniLM-L6-v2) | 384 维文本向量化 |
| **向量数据库** | ChromaDB | 双集合向量存储，余弦相似度检索 |
| **文档解析** | python-docx | .docx 文件解析（上传 + 文件夹导入） |
| **爬虫** | httpx + BeautifulSoup4 + lxml | HTML 解析与网页内容抓取 |
| **SQL 解析** | sqlite3 + SQLAlchemy | SQL 语法验证与沙箱执行 |
| **Python 解析** | AST（标准库） | Python 语法验证与安全检查 |
| **配置管理** | pydantic-settings | 环境变量与配置管理 |
| **测试** | pytest + pytest-asyncio | 单元测试与异步测试 |

---

## API 端点

### 制度文档

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/documents/qa` | 制度文档问答 |
| `POST` | `/api/v1/documents/review` | 文档智能审查 |
| `POST` | `/api/v1/documents/classify` | 文档自动分类 |
| `POST` | `/api/v1/documents/index` | JSON 索引入库 |
| `POST` | `/api/v1/documents/upload` | 文件上传入库（multipart） |
| `POST` | `/api/v1/documents/import-folder` | 文件夹批量导入 |
| `GET` | `/api/v1/documents` | 列出已索引文档 |
| `DELETE` | `/api/v1/documents` | 清空知识库 |
| `DELETE` | `/api/v1/documents/by-id` | 按 ID 删除单条文档 |

### 代码生成

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/sql/generate` | 生成 SQL |
| `POST` | `/api/v1/python/generate` | 生成 Python |
| `POST` | `/api/v1/pipeline/ask` | 端到端：生成 + 验证 + 沙箱执行 |

### 验证与执行

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/validate` | 安全验证 |
| `POST` | `/api/v1/execute` | 沙箱执行 |

### 知识管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/crawl` | 爬取网站 |
| `POST` | `/api/v1/pipeline/crawl-and-index` | 爬取 + 自动入库 |
| `POST` | `/api/v1/search` | 语义搜索 |

### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Dashboard 操作台 (HTML) |
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/v1/collections` | 知识库集合列表及文档数 |
| `GET` | `/api/v1/dashboard/status` | 系统状态汇总（双库统计） |
| `GET` | `/api/v1/metrics` | 运行指标 |
| `GET` | `/api/v1/history` | 操作历史记录 |
| `DELETE` | `/api/v1/history` | 清空历史记录 |
| `GET` | `/api/v1/scenarios` | 银行场景列表 |
| `GET` | `/api/v1/scenarios/{name}` | 场景详情（含 DDL） |

---

## 配置参考

编辑 `.env` 文件：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | LLM API 密钥（**必填**） | — |
| `OPENAI_BASE_URL` | API 端点 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-v4-flash` |
| `LLM_TEMPERATURE` | 生成温度 (0-2) | `0.1` |
| `LLM_MAX_TOKENS` | 单次最大 Token 数 | `4096` |
| `EMBEDDING_MODEL` | 嵌入模型名称 | `all-MiniLM-L6-v2` |
| `HF_ENDPOINT` | HuggingFace 镜像 | `https://hf-mirror.com` |
| `CHROMA_PERSIST_DIR` | 向量库存储目录 | `./chroma_data` |
| `CHUNK_SIZE` | 分块大小（字符） | `1000` |
| `CHUNK_OVERLAP` | 分块重叠 | `200` |
| `RETRIEVAL_TOP_K` | 检索返回条数 | `5` |
| `API_PORT` | 服务端口 | `8000` |

**切换模型示例：**

```ini
# GPT-4o
OPENAI_API_KEY=sk-your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o

# 本地 vLLM
OPENAI_API_KEY=not-needed
OPENAI_BASE_URL=http://localhost:8001/v1
LLM_MODEL=Qwen2.5-7B-Instruct
```

---

## 项目结构

```
rag-code-gen/
├── src/
│   ├── app.py                    # FastAPI 入口 + Dashboard 路由
│   ├── config.py                 # 配置管理（pydantic-settings）
│   ├── dashboard.html            # Web Dashboard（零框架依赖，中英双语）
│   ├── cli.py                    # 命令行工具
│   ├── business/
│   │   └── banking.py            # 4 套银行金融场景 Schema（10 张表）
│   ├── crawler/                  # 数据采集层
│   │   ├── base.py               # 爬虫抽象基类
│   │   ├── doc_crawler.py        # 文档网站爬虫
│   │   └── code_crawler.py       # 代码文件爬虫
│   ├── rag/                      # RAG 检索引擎
│   │   ├── chunker.py            # 文档分块（文本/代码双策略）
│   │   ├── embedding.py          # 向量嵌入（本地模型，自动下载）
│   │   ├── vector_store.py       # ChromaDB 向量存储（多集合支持）
│   │   └── retriever.py          # 检索器（索引 + 语义检索）
│   ├── llm/                      # LLM 生成层
│   │   ├── providers.py          # LLM 提供商（OpenAI 兼容 / Mock）
│   │   ├── prompts.py            # 7 套 Prompt 模板
│   │   ├── sql_generator.py      # SQL 代码生成器
│   │   └── python_generator.py   # Python 代码生成器
│   ├── validator/                # 安全验证层
│   │   ├── sql_validator.py      # SQL 验证（9 类危险操作拦截）
│   │   ├── python_validator.py   # Python 验证（AST + 15+ 敏感调用拦截）
│   │   └── sandbox.py            # 沙箱执行（SQLite 内存 / 临时文件）
│   ├── evaluator/                # 评估与历史记录
│   │   ├── metrics.py            # 指标追踪 + 持久化历史记录
│   │   └── benchmark.py          # Benchmark 框架
│   └── api/                      # API 层
│       ├── routes.py             # 25 个 API 端点
│       └── schemas.py            # Pydantic 数据模型
├── tests/                        # 测试套件
├── pyproject.toml                # 项目元数据与依赖
├── .env.example                  # 环境配置模板
├── .gitignore
└── README.md
```

---

## 安全设计

### SQL 安全（9 类拦截）

DROP / TRUNCATE / ALTER TABLE DROP / EXEC / GRANT / REVOKE / INTO OUTFILE / LOAD_FILE / BENCHMARK / SLEEP / SHUTDOWN / KILL

### Python 安全（15+ 模块拦截）

`os` `subprocess` `shutil` `sys` `socket` `requests` `importlib` `ctypes` `multiprocessing` `threading` `asyncio` 等

### 危险函数拦截

`eval` `exec` `compile` `__import__` `open` `globals` `locals` `getattr` `setattr`

### 沙箱执行

- **SQL**：SQLite 内存数据库，完全隔离
- **Python**：临时文件执行，超时 10 秒自动终止

---


