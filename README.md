# ATS 招聘管理系统

基于 Streamlit + DeepSeek V4 + Supabase 的 AI 驱动招聘全流程管理平台。

## 功能模块

| 模块 | 说明 |
|------|------|
| 职位管理 | 新增/编辑/删除岗位，配置 JD 和硬性红线要求 |
| 简历上传与 AI 解析 | 批量上传 PDF/Word，AI 自动提取信息并打分 |
| 人才库 | 全量候选人管理，支持筛选、搜索、公海池归档 |
| 招聘流程跟踪 | 全流程状态机，看板视图 + 沟通记录 |
| 数据看板 | 转化漏斗、评分分布、学历/院校分析、留存指标 |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd ats-system

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 Supabase

1. 在 [supabase.com](https://supabase.com) 创建项目
2. 进入 SQL Editor，执行 `sql/init_schema.sql`
3. 在 Storage 中创建名为 `resumes` 的 Bucket（公开访问）
4. 在 Project Settings > API 获取：
   - `Project URL`
   - `service_role key`（注意：是 secretkey，不是 anon key）

### 3. 配置 DeepSeek API

1. 在 [platform.deepseek.com](https://platform.deepseek.com) 注册并获取 API Key
2. 充值后即可使用

### 4. 配置 Secrets

**本地开发：** 编辑 `.streamlit/secrets.toml`

```toml
GLOBAL_PASSWORD = "202603"

[supabase]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "eyJhbGciOi..."

[deepseek]
API_KEY = "sk-your-key"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
```

**Streamlit Cloud 部署：** 在 Dashboard > Settings > Secrets 中粘贴以上内容。

### 5. 启动

```bash
streamlit run main.py
```

访问 http://localhost:8501

- 系统密码：`202603`
- 默认管理员：`admin@ats.com` / `admin123`

## 部署到 Streamlit Cloud

1. 将项目推送到 GitHub
2. 在 [share.streamlit.io](https://share.streamlit.io) 创建 App
3. 配置 Secrets（同本地配置）
4. 部署完成后即可通过公网 URL 访问

## 技术栈

- **框架**：Streamlit
- **AI 模型**：DeepSeek V4（兼容 OpenAI SDK）
- **数据库**：Supabase (PostgreSQL)
- **文件存储**：Supabase Storage
- **可视化**：Plotly
- **文档解析**：PyPDF2、python-docx

## 使用流程

1. **管理员登录** → 创建 HR 账号
2. **配置职位** → 填写 JD 和硬性要求
3. **上传简历** → AI 自动解析、评分、匹配
4. **人才库筛选** → 查看评分、优势、风险
5. **流程推进** → 初筛 → 联系 → 面试 → Offer → 入职 → 转正
6. **数据看板** → 实时查看招聘效能指标

## 数据库 Schema

```
users                      # 用户表
positions                  # 职位表
candidates                 # 候选人表（含 AI 解析结果）
candidate_positions        # 候选人-职位关联（多对多）
candidate_pipeline         # 招聘流程阶段记录（状态机）
communication_notes        # 沟通记录
```

## 招聘阶段状态机

```
初筛-通过 → 联系反馈 → 部门筛选-通过 → 初试-通过 → 复试-通过 → 发Offer → 接Offer → 已入职 → 试用期评估-通过
    ↓              ↓              ↓              ↓            ↓          ↓          ↓              ↓
初筛-淘汰     部门筛选-淘汰    初试-淘汰     复试-淘汰    拒Offer                            试用期评估-未通过
    ↓              ↓              ↓            ↓          ↓
    └──────────────┴──────────────┴────────────┴──────────┘
                              ↓
                           公海池
```
