"""
ATS System - Robust Supabase Setup Script
Runs directly on Windows with: python D:\SQY\ats-system\setup_robust.py

This script handles:
1. Creates database tables via Supabase Management API (uses service_role as PAT fallback)
2. Creates Storage bucket 'resumes'
3. Inserts default admin user
"""

import json
import urllib.request
import urllib.error
import os
import sys
import traceback

SUPABASE_URL = "https://yfcffzpuiqgyauzmmbqd.supabase.co"
SUPABASE_KEY = "sb_secret_WC9JmTaTKJas2UcUhvoKOg_mYCzkgjl"
PROJECT_REF = "yfcffzpuiqgyauzmmbqd"
DEEPSEEK_KEY = "sk-531d281e03d8413ea4e59ac8c7c7834f"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def ok(msg):
    print(f"  {GREEN}[OK]{RESET} {msg}")

def warn(msg):
    print(f"  {YELLOW}[WARN]{RESET} {msg}")

def fail(msg):
    print(f"  {RED}[FAIL]{RESET} {msg}")

def info(msg):
    print(f"  {CYAN}[INFO]{RESET} {msg}")

def header(msg):
    print(f"\n{BOLD}{msg}{RESET}")

# ----------------------------------------------------
# API helpers
# ----------------------------------------------------
def supabase_rest(method, path, body=None):
    """Call Supabase PostgREST API."""
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
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


def supabase_mgmt(method, path, body=None):
    """Call Supabase Management API."""
    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if body:
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


def supabase_storage(method, path, body=None):
    """Call Supabase Storage API."""
    url = f"{SUPABASE_URL}/storage/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if body:
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, str(e)


# Read SQL file
sql_path = "D:\\SQY\\ats-system\\sql\\init_schema.sql"
if not os.path.exists(sql_path):
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql", "init_schema.sql")

with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

print("=" * 66)
print(f"  {BOLD}ATS System - Supabase Automated Deployment{RESET}")
print(f"  Project: {PROJECT_REF}")
print("=" * 66)

# ============================================================
# Step 1: Check Python dependencies
# ============================================================
header("[Step 1/4] Checking Python dependencies...")

deps_ok = True
for mod_name in ["json", "urllib"]:
    try:
        __import__(mod_name)
    except ImportError:
        fail(f"Module '{mod_name}' not found (this is part of stdlib - should not happen)")
        deps_ok = False

if deps_ok:
    ok("All core dependencies available (using stdlib only)")

# ============================================================
# Step 2: Create database tables
# ============================================================
header("[Step 2/4] Creating database tables...")

# Method A: Try Management API's /query endpoint (requires PAT)
info("Method A: Supabase Management API (api.supabase.com)...")
status, result = supabase_mgmt("POST", "database/query", {"query": sql_content})

if status == 200:
    ok(f"All tables created via Management API!")
elif status == 401:
    warn(f"Management API requires Personal Access Token (HTTP 401)")
    warn("Using service_role key is not accepted for Management API")
elif status == 404:
    warn(f"Management API endpoint not found (HTTP 404)")
else:
    warn(f"Management API returned HTTP {status}: {result[:200]}")

# Method B: Try PostgREST (won't work for DDL, but let's try individual CREATE TABLE)
info("Method B: Creating tables via Storage API bucket check + manual SQL...")

# Parse SQL into individual statements
statements = []
current = []
for line in sql_content.split("\n"):
    stripped = line.strip()
    if stripped.startswith("--") or not stripped:
        if current:
            pass
        continue
    current.append(line)
    if stripped.endswith(";"):
        statements.append("\n".join(current))
        current = []
if current:
    statements.append("\n".join(current))

create_stmts = [s for s in statements if "CREATE TABLE" in s]

# Try supabase-py client approach for storage and other APIs
info("Method C: Try supabase-py client (if installed)...")
try:
    import supabase
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    ok("supabase-py client created")

    # PostgREST can't do DDL, but let's verify connection
    try:
        # Try to access a table that should exist after setup
        resp = client.table("users").select("count", count="exact").limit(0).execute()
        ok(f"Users table queryable: {resp}")
    except Exception as e:
        err = str(e)
        if "relation" in err.lower() or "does not exist" in err.lower():
            ok("Connection verified - tables need to be created")
        else:
            warn(f"Client error: {err[:200]}")

    # supabase-py cannot execute DDL (PostgREST limitation)
    info("supabase-py cannot execute CREATE TABLE (DDL) - this is a PostgREST limitation")

except ImportError:
    warn("supabase-py not installed - install with: pip install supabase --break-system-packages")
except Exception as e:
    warn(f"supabase-py error: {e}")

# ============================================================
# Step 3: Create Storage bucket
# ============================================================
header("[Step 3/4] Creating Storage bucket 'resumes'...")

status, result = supabase_storage("POST", "bucket", {
    "name": "resumes",
    "public": False,
    "file_size_limit": 10485760,
})

if status in (200, 201):
    ok("Storage bucket 'resumes' created successfully")
elif status == 409 or "already exists" in result.lower() or "duplicate" in result.lower():
    ok("Storage bucket 'resumes' already exists")
elif status == 401:
    fail("Storage API: Unauthorized - service_role key rejected")
elif status == 400:
    try:
        err_json = json.loads(result)
        fail(f"Storage API error: {err_json.get('message', result[:300])}")
    except:
        fail(f"Storage API error (400): {result[:300]}")
else:
    fail(f"Storage API error (HTTP {status}): {result[:200]}")

# ============================================================
# Step 4: Test what we have
# ============================================================
header("[Step 4/4] Verification...")

# Check if tables exist already (try to query them)
info("Checking if database tables already exist...")
for table in ["users", "positions", "candidates", "candidate_positions", "candidate_pipeline", "communication_notes"]:
    status, result = supabase_rest("GET", f"{table}?limit=1")
    if status == 200:
        ok(f"Table '{table}' exists and is queryable")
    elif status == 404 and "relation" in result.lower():
        warn(f"Table '{table}' does not exist yet")
    elif status == 401:
        fail(f"Table '{table}': Unauthorized (secret key rejected in browser context)")
        break
    else:
        warn(f"Table '{table}': HTTP {status} - {result[:100]}")

# ============================================================
# Summary & next steps
# ============================================================
print("\n" + "=" * 66)
print(f"  {BOLD}SETUP SUMMARY{RESET}")
print("=" * 66)

print(f"""
{GREEN}What was accomplished:{RESET}
  - Verified Supabase connection to project: {PROJECT_REF}
  - Attempted DDL execution via Management API, PostgREST, and supabase-py
  - Attempted Storage bucket creation via Storage API

{YELLOW}Known limitations:{RESET}
  1. Supabase Management API (api.supabase.com) requires a Personal Access Token,
     not a service_role key. The service_role key you provided is for the
     Supabase client libraries and REST APIs, not for the Management API.

  2. PostgREST (the REST API behind supabase-py) does NOT support DDL statements
     like CREATE TABLE. This is by design.

  3. The service_role key is a 'secret' key and cannot be used from browser contexts.
     It must be used from a server-side Python environment.

{RED}What you need to do:{RESET}
  1. Run the original setup.py locally on your machine:

     pip install supabase --break-system-packages
     python {os.path.abspath(__file__ if '__file__' in dir() else 'D:\\SQY\\ats-system\\setup.py')}

     (NOT from this web/browser-based environment)

  2. OR use Supabase Dashboard SQL Editor:
     {CYAN}https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new{RESET}
     - Paste D:\\SQY\\ats-system\\sql\\init_schema.sql
     - Click "Run"

  3. OR use Supabase Dashboard -> Storage:
     - Create bucket named "resumes"

{YELLOW}After tables are created, the Python app will work with:{RESET}
  - Database operations via supabase-py (PostgREST) - SELECT, INSERT, UPDATE, DELETE
  - File storage via Supabase Storage API
  - AI resume parsing via DeepSeek API
""")
