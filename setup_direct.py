"""
ATS Supabase Setup - Direct Python Script
Run: pip install supabase && python D:\SQY\ats-system\setup_direct.py
"""
import json
import urllib.request
import urllib.error
import os
import sys

SUPABASE_URL = "https://yfcffzpuiqgyauzmmbqd.supabase.co"
SUPABASE_KEY = "sb_secret_WC9JmTaTKJas2UcUhvoKOg_mYCzkgjl"
PROJECT_REF = "yfcffzpuiqgyauzmmbqd"

print("=" * 60)
print("  ATS System - Supabase Direct Setup")
print("=" * 60)

# ============================================================
# Approach 1: Try Supabase Management API
# The management API at api.supabase.com requires a PAT (personal access token)
# but let's try with the service_role key anyway
# ============================================================
print("\n[Attempt 1] Supabase Management API (POST /query)...")

def exec_sql_via_mgmt(sql_query):
    mgmt_url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps({"query": sql_query}).encode()
    req = urllib.request.Request(mgmt_url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return True, resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return False, e.code, e.read().decode()

# Read SQL file
sql_path = os.path.join("D:\\SQY\\ats-system\\sql", "init_schema.sql")
if not os.path.exists(sql_path):
    alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql", "init_schema.sql")
    sql_path = alt_path

with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

# Try executing all SQL at once
success, status, result = exec_sql_via_mgmt(sql_content)
if success and status == 200:
    print(f"  ✅ Management API: All tables created! Status {status}")
    print(f"  Response: {result[:200]}")
else:
    print(f"  ❌ Management API failed (HTTP {status}): {result[:300]}")
    print("  (Management API requires a Personal Access Token, not service_role key)")

# ============================================================
# Approach 2: Try supabase-py client's table creation via REST
# ============================================================
print("\n[Attempt 2] supabase-py client approach...")
try:
    import supabase
    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("  ✅ supabase client created successfully")

    # Check Supabase version/health
    try:
        health = client.table("_dummy").select("*").limit(1).execute()
        print(f"  ℹ️  Unexpected: REST API returned: {health}")
    except Exception as e:
        err_str = str(e)
        if "relation" in err_str.lower() or "does not exist" in err_str.lower():
            print("  ✅ Client connected - tables don't exist yet (expected)")
        else:
            print(f"  ⚠️  Client connection check: {err_str[:200]}")

    print("  ⚠️  PostgREST does not support CREATE TABLE (DDL)")
    print("  ⚠️  supabase-py client cannot execute DDL statements")

except ImportError as e:
    print(f"  ❌ supabase module not installed: {e}")
    print("  Run: pip install supabase --break-system-packages")
except Exception as e:
    print(f"  ❌ supabase-py error: {e}")

# ============================================================
# Approach 3: Try through Supabase REST API directly
# Using the /rest/v1/ endpoint with service_role key
# PostgREST doesn't support DDL, but let's try anyway
# ============================================================
print("\n[Attempt 3] Direct PostgREST approach...")

def supabase_rest_request(method, path, body=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if body:
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# Try checking if users table exists
status, result = supabase_rest_request("GET", "users?limit=1")
if status == 200:
    print("  ✅ Users table already exists")
elif status == 404 and "relation" in result.lower():
    print("  ⚠️  Users table does not exist (PostgREST can't create it)")
elif status == 401:
    print("  ❌ Unauthorized - service_role key rejected for browser context")
    print("  ℹ️  This is expected - service_role is a 'secret' key")
else:
    print(f"  Status {status}: {result[:200]}")

# ============================================================
# Approach 4: Try Supabase SQL API via custom RPC
# Some Supabase projects have a `pgroonga` or `http` extension
# that allows raw SQL via postgREST
# ============================================================
print("\n[Attempt 4] Custom RPC approach...")

# Try creating a pg_query function that wraps SQL execution
# This requires prior setup, but let's check
status, result = supabase_rest_request("GET", "rpc/pg_query?q=SELECT+1")
if status == 200:
    print(f"  ✅ RPC pg_query exists! Result: {result[:200]}")
elif status == 404:
    print("  ℹ️  RPC pg_query does not exist (no custom RPC function)")
else:
    print(f"  Status {status}: {result[:200]}")

# Check if there are any existing RPC functions
status, result = supabase_rest_request("GET", "")
print(f"  Root endpoint status: {status}")

# ============================================================
# Approach 5: Storage API
# ============================================================
print("\n[Attempt 5] Create Storage bucket 'resumes'...")

def create_bucket():
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps({
        "name": "resumes",
        "public": False,
        "file_size_limit": 10485760,
    }).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

status, result = create_bucket()
if status in (200, 201):
    print("  ✅ Storage bucket 'resumes' created successfully!")
elif status == 409 or "already exists" in result.lower():
    print("  ℹ️  Bucket 'resumes' already exists")
elif status == 400:
    print(f"  ❌ Bad request: {result[:300]}")
    print("  ℹ️  The service_role key may be rejected in this context")
else:
    print(f"  Status {status}: {result[:200]}")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print("""
The Supabase service_role key works with:
  - supabase-py client (non-browser Python context)
  - Supabase REST APIs from server-side Python

It does NOT work with:
  - Browser/JavaScript contexts (Supabase blocks secret keys there)
  - Management API (api.supabase.com) - requires PAT, not service_role

To complete the database setup:
  1. Run the original setup.py from a proper Python environment (not browser):
     pip install supabase --break-system-packages
     python D:\\SQY\\ats-system\\setup.py

  2. OR go to Supabase Dashboard -> SQL Editor
     URL: https://supabase.com/dashboard/project/yfcffzpuiqgyauzmmbqd/sql/new
     Paste the content of: D:\\SQY\\ats-system\\sql\\init_schema.sql
     Click "Run"

  3. OR go to Supabase Dashboard -> Storage
     Create a bucket named "resumes"
""")
print("=" * 60)
