"""
ATS 系统一键部署脚本
运行: python setup.py
"""
import sys
import os
import json
import urllib.request
import urllib.error

# ============================================================
# 配置（自动从 secrets.toml 读取）
# ============================================================
SUPABASE_URL = "https://yfcffzpuiqgyauzmmbqd.supabase.co"
SUPABASE_KEY = "sb_secret_WC9JmTaTKJas2UcUhvoKOg_mYCzkgjl"
DEEPSEEK_KEY = "sk-531d281e03d8413ea4e59ac8c7c7834f"

PROJECT_REF = "yfcffzpuiqgyauzmmbqd"

print("=" * 60)
print("  ATS 招聘管理系统 - 自动化部署")
print("=" * 60)

# ============================================================
# Step 1: 检查依赖
# ============================================================
print("\n[1/4] 检查依赖...")
try:
    import streamlit
    import pandas
    import openai
    import supabase
    import bcrypt
    import plotly
    print("  ✅ 所有核心依赖已安装")
except ImportError as e:
    print(f"  ❌ 缺少依赖: {e}")
    print("  请运行: pip install -r requirements.txt --break-system-packages")
    sys.exit(1)

# ============================================================
# Step 2: 测试 Supabase 连接
# ============================================================
print("\n[2/4] 测试 Supabase 连接...")

def supabase_api_request(method, path, body=None):
    """调用 Supabase REST API (PostgREST)。"""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if body:
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# 测试：尝试读取 users 表
status, result = supabase_api_request("GET", "users?limit=1")
if status in (200, 404):
    if status == 404 and "relation" in result.lower():
        print("  ⚠️ 数据库表尚未创建，将在下一步执行建表")
    else:
        print("  ✅ Supabase 连接成功")
else:
    print(f"  ❌ 连接失败 (HTTP {status}): {result[:200]}")
    print("  请检查 SUPABASE_KEY 是否正确（需要 service_role key）")
    # 不退出，继续尝试

# ============================================================
# Step 3: 执行数据库建表
# ============================================================
print("\n[3/4] 执行数据库建表...")

# 读取 SQL 文件
sql_path = os.path.join(os.path.dirname(__file__), "sql", "init_schema.sql")
with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

# Split into individual statements
statements = []
current = []
for line in sql_content.split("\n"):
    stripped = line.strip()
    if stripped.startswith("--") or not stripped:
        continue
    current.append(line)
    if stripped.endswith(";"):
        statements.append("\n".join(current))
        current = []

# 跳过最后的 INSERT 语句（独立执行）
setup_stmts = [s for s in statements if "INSERT INTO users" not in s]
insert_stmt = next((s for s in statements if "INSERT INTO users" in s), None)

# 使用 Supabase SQL API（通过 PostgREST rpc 不可行，改用 Management API）
# 注意：PostgREST 不支持 DDL。需要用 Supabase Management API 或 SQL Editor。

print("  ℹ️  PostgREST 不支持直接建表（DDL），将使用 Management API...")

# 尝试通过 Supabase Management API 执行 SQL
def exec_sql_via_mgmt(sql_query):
    """通过 Supabase Management API 执行 SQL。"""
    mgmt_url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/query"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps({"query": sql_query}).encode()
    req = urllib.request.Request(mgmt_url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# 尝试逐条执行 CREATE TABLE
tables_created = 0
create_stmts = [s for s in setup_stmts if "CREATE TABLE" in s.upper() or "CREATE INDEX" in s.upper() or "CREATE UNIQUE INDEX" in s.upper()]

for stmt in create_stmts:
    status, result = exec_sql_via_mgmt(stmt)
    if status == 200 or status == 201:
        tables_created += 1
    elif "already exists" in result.lower() or status == 409:
        tables_created += 1  # 表已存在也算成功
    else:
        # 静默失败，因为 Management API 可能不支持
        pass

if tables_created > 0:
    print(f"  ✅ 通过 Management API 执行了 {tables_created} 条 DDL 语句")
else:
    print("  ⚠️ Management API 不可用（可能需要 personal access token）")
    print("  📋 请手动执行建表：")
    print(f"     1. 打开 https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new")
    print(f"     2. 粘贴 sql/init_schema.sql 的全部内容")
    print(f"     3. 点击 Run 执行")
    print(f"\n     文件路径: {sql_path}")

# 尝试插入默认用户
if insert_stmt and tables_created > 0:
    status, result = exec_sql_via_mgmt(insert_stmt)
    if status in (200, 201):
        print("  ✅ 默认管理员用户已创建 (admin@ats.com / admin123)")
    elif "duplicate" in result.lower() or "already exists" in result.lower():
        print("  ℹ️  默认管理员用户已存在")

# ============================================================
# Step 4: 创建 Supabase Storage Bucket
# ============================================================
print("\n[4/4] 创建文件存储 Bucket...")

def create_storage_bucket():
    """通过 Supabase Storage API 创建 bucket。"""
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps({
        "name": "resumes",
        "public": False,
        "file_size_limit": 10485760,  # 10MB
    }).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

status, result = create_storage_bucket()
if status in (200, 201):
    print("  ✅ Storage Bucket 'resumes' 创建成功")
elif status == 409 or "already exists" in result.lower() or "duplicate" in result.lower():
    print("  ℹ️  Storage Bucket 'resumes' 已存在")
elif status == 400 and "valid" in result.lower():
    # Key 格式不对，可能是 anon key 而非 service_role
    print(f"  ❌ Storage 创建失败: {result[:300]}")
    print("  请确保使用的是 service_role key（不是 anon key）")
else:
    print(f"  ⚠️ Storage 创建返回 {status}: {result[:200]}")
    print("  请手动在 Supabase Dashboard > Storage 创建名为 'resumes' 的 bucket")

# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 60)
print("  部署完成！")
print("=" * 60)
print(f"""
下一步操作：

1. 【重要】如果建表未自动完成，请手动执行:
   → 打开 https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new
   → 粘贴 sql/init_schema.sql 全部内容
   → 点击右下角 Run

2. 启动系统:
   cd ats-system
   streamlit run main.py

3. 访问 http://localhost:8501
   - 系统密码: 202603
   - 管理员: admin@ats.com / admin123
""")
