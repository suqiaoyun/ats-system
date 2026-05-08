# ATS 招聘管理系统

基于 **Streamlit + DeepSeek V4 + Supabase** 的 AI 驱动招聘全流程管理平台。

覆盖从职位发布、简历智能解析、人才库筛选、招聘流程跟踪到数据看板的完整闭环。

> 在线体验：[https://ats-system-2026.streamlit.app](https://ats-system-2026.streamlit.app)

---

## 功能模块

| 模块 | 核心功能 |
|------|---------|
| 📌 **职位管理** | 新增/编辑/删除岗位，配置岗位职责、任职要求、硬性红线、加分项 |
| 🤖 **简历上传与 AI 解析** | 批量上传 PDF/Word/TXT，DeepSeek V4 自动提取姓名/年龄/电话/学历/院校等信息，并给出 AI 匹配评分（0-100） |
| 🔍 **人才库** | 全量候选人管理，按岗位/状态/关键词多维度筛选，查看 AI 评语与硬性匹配结果 |
| 🔄 **招聘流程跟踪** | 全流程状态机（看板/表格双视图），阶段推进，沟通记录，流程历史追溯 |
| 📊 **数据看板** | 转化漏斗、评分分布、学历/院校分布、岗位投递统计、留存指标，支持 CSV 导出 |

## 技术栈

| 层 | 技术 |
|------|------|
| **前端/框架** | Streamlit（多页面） |
| **AI 模型** | DeepSeek V4（OpenAI 兼容 SDK） |
| **数据库** | Supabase（PostgreSQL） |
| **可视化** | Plotly（漏斗图、饼图、柱状图） |
| **文档解析** | PyPDF2 / pypdf（PDF）、python-docx（Word） |
| **部署** | Streamlit Cloud / GitHub |

---

## 快速开始

### 1. 克隆与安装

```bash
git clone <your-repo-url>
cd ats-system
pip install -r requirements.txt
```

### 2. 配置 Supabase 数据库

在 [supabase.com](https://supabase.com) 创建项目，进入 **SQL Editor**，执行 `sql/init_schema.sql` 创建以下 6 张表：

| 表 | 说明 |
|------|------|
| `users` | 用户（保留用于扩展，当前无需登录） |
| `positions` | 招聘岗位（含 JD、硬性要求、加分项） |
| `candidates` | 候选人（含 AI 解析结果、评分、优劣势） |
| `candidate_positions` | 候选人与岗位的多对多关联 |
| `candidate_pipeline` | 招聘流程阶段记录（状态机） |
| `communication_notes` | 沟通记录 |

### 3. 配置 DeepSeek API

在 [platform.deepseek.com](https://platform.deepseek.com) 注册并获取 API Key。AI 负责简历信息提取、匹配度评分、硬性红线检测。

### 4. 配置 Secrets

**本地开发：** 编辑 `.streamlit/secrets.toml`

```toml
[supabase]
SUPABASE_URL = "https://你的项目.supabase.co"
SUPABASE_KEY = "你的 service_role key"

[deepseek]
API_KEY = "sk-你的key"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
```

> 本项目无需密码登录，无需配置 `GLOBAL_PASSWORD`。

**Streamlit Cloud 部署：** 在 App Dashboard > Settings > Secrets 中粘贴以上内容。

### 5. 启动

```bash
streamlit run main.py
```

访问 `http://localhost:8501`，无需密码直接进入系统。

---

## 部署到 Streamlit Cloud

1. 将项目推送到 GitHub 仓库
2. 登录 [share.streamlit.io](https://share.streamlit.io)
3. 点击 **Create app**，选择仓库和分支
4. 在 **Settings > Secrets** 配置 Supabase 和 DeepSeek 的密钥
5. 部署完成后通过公网 URL 访问

每次 `git push` 到主分支后，Streamlit Cloud 会自动重新部署。

---

## 数据库设计

### ER 关系

```
users ──┐
         ├── positions ← candidate_pipeline
         │       ↑           ↑
         │       │           │
         └── communication_notes
                 
candidates ──→ candidate_positions ←── positions
     ↑                  ↑
     └── candidate_pipeline
```

### 各表字段说明

**positions（职位表）**
- `title` — 岗位名称
- `department` — 部门
- `jd_description` — 岗位职责描述
- `requirements` — 任职要求
- `hard_requirements` — 硬性红线条件（如"硕士及以上学历、5年以上经验"）
- `bonus_requirements` — 加分项（如"大厂经历、CPA/CFA 证书"）
- `status` — 状态：open / closed / draft
- `headcount` — 编制人数

**candidates（候选人表）**
- `name / gender / age / phone / email` — 基本信息
- `education / school / major / graduation_year` — 教育背景
- `work_years / current_company` — 工作经历
- `ai_score` — AI 综合评分（0-100）
- `ai_strengths / ai_risks` — AI 分析的优势与风险
- `hard_match / hard_match_detail` — 硬性红线匹配结果
- `status` — 状态：new / active / archived / hired / public_pool

> 注：候选人数据由 DeepSeek V4 AI 自动从简历中提取，无需手动录入。

---

## 使用流程

### 完整招聘闭环

```
① 职位管理 ───→ ② 上传简历 ───→ ③ 人才库筛选 ───→ ④ 流程推进 ───→ ⑤ 数据看板
    │                 │                │                │              │
    ├ 发布岗位        ├ PDF/Word/TXT   ├ AI评分排序     ├ 初筛          ├ 转化漏斗
    ├ 配置JD          ├ AI自动解析     ├ 优势/风险评估  ├ 部门筛选      ├ 评分分布
    ├ 硬性红线        ├ 匹配度评分     ├ 公海池管理     ├ 面试          ├ 院校分布
    └ 加分项          └ 一键入库       └ 多岗位关联     └ Offer/入职    └ 留存指标
```

### 具体操作步骤

1. **→ 职位管理** — 创建招聘岗位，填写 JD、硬性要求和加分项
2. **→ 简历上传** — 上传简历文件（可批量），DeepSeek 自动提取候选人信息并打分
3. **→ 人才库** — 按岗位/状态/关键词筛选候选人，查看 AI 评价，手动调整评分
4. **→ 招聘流程** — 拖拽式/按钮式推进候选人到下一阶段，记录沟通备注
5. **→ 数据看板** — 跟踪招聘效能指标，发现流程瓶颈

---

## 招聘阶段状态机

系统定义了完整的招聘流程状态机，支持双向流转和公海池回收：

```
                ┌──────────────────────────────────────────────┐
                │                                              │
                ▼                                              │
初筛-通过 ──→ 联系反馈 ──→ 部门筛选-通过 ──→ 初试-通过 ──→ 复试-通过 ──→ 发Offer ──→ 接Offer ──→ 已入职 ──→ 试用期评估-通过
  │               │              │                │             │           │           │               │
  ▼               ▼              ▼                ▼             ▼           ▼           ▼               ▼
初筛-淘汰      （淘汰）    部门筛选-淘汰       初试-淘汰    复试-淘汰    拒Offer     （放弃）     试用期评估-未通过
  │               │              │                │             │           │           │               │
  └───────────────┴──────────────┴────────────────┴─────────────┴───────────┴───────────┴───────────────┘
                                                      │
                                                      ▼
                                                   公海池
```

**阶段说明：**

| 阶段 | 含义 | 可流向 |
|------|------|--------|
| 初筛-通过 / 初筛-淘汰 | 简历初步筛选结果 | 联系反馈 / 公海池 |
| 联系反馈 | 与候选人初步沟通反馈 | 部门筛选-通过 / 部门筛选-淘汰 |
| 部门筛选-通过 / 部门筛选-淘汰 | 用人部门筛选结果 | 初试 / 公海池 |
| 初试/复试-通过 / 淘汰 | 面试结果 | 下一轮 / 公海池 |
| 发Offer | 发出录用通知 | 接Offer / 拒Offer |
| 接Offer / 拒Offer | 候选人反馈 | 已入职 / 公海池 |
| 已入职 | 正式入职 | 试用期评估 |
| 试用期评估-通过 / 未通过 | 转正或辞退 | — |
| 公海池 | 淘汰/放弃的候选人池 | 可重新激活 |

---

## 项目结构

```
ats-system/
├── main.py                         # 主入口（仪表盘）
├── pages/
│   ├── 1_📌_职位管理.py           # 职位 CRUD
│   ├── 2_🤖_简历上传与AI解析.py    # 简历上传与 AI 解析
│   ├── 3_🔍_人才库.py             # 人才库筛选与管理
│   ├── 4_🔄_招聘流程跟踪.py        # 流程状态机看板
│   └── 5_📊_数据看板.py           # KPI 数据可视化
├── utils/
│   ├── auth.py                     # 认证（简化版，直接放行）
│   ├── supabase_client.py          # Supabase CRUD 封装
│   └── deepseek_client.py          # DeepSeek AI 调用封装
├── sql/
│   └── init_schema.sql             # 数据库初始化脚本
├── .streamlit/
│   └── secrets.toml                # 本地密钥配置（不提交到 Git）
├── .gitignore                      # Git 忽略规则
├── requirements.txt                # Python 依赖
└── README.md                       # 本文件
```

---

## 常见问题

### 创建职位时提示数据库错误？
检查 Supabase 是否已执行 `sql/init_schema.sql` 建表脚本，以及 `.streamlit/secrets.toml` 中的数据库连接信息是否正确。

### AI 解析总是失败？
- 确认 DeepSeek API Key 有效且账户有余额
- 扫描件/图片类 PDF 无法提取文字，请使用文字版 PDF 或 Word
- 网络环境需能访问 `api.deepseek.com`

### 上传简历后提示文件存储失败？
已去除文件存储功能，只保存 AI 解析的结构化数据到数据库。此提示不会影响数据保存。

### 如何重新部署？
推送到 GitHub 主分支后，Streamlit Cloud 自动部署。如需手动重启，在 App 页面点 **Manage app → ⋯ → Reboot**。

---

*Built with Streamlit + DeepSeek V4 + Supabase*
