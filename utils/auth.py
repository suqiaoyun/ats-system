"""
认证模块 - 处理全局密码验证和用户登录
"""
import streamlit as st
import bcrypt
from datetime import datetime
from utils.supabase_client import get_supabase_client

# ============================================================
# 全局密码校验
# ============================================================

def check_global_password():
    """检查是否已通过全局密码验证，未通过则显示输入框。"""
    if "global_authenticated" not in st.session_state:
        st.session_state.global_authenticated = False

    if not st.session_state.global_authenticated:
        st.title("🔐 ATS 招聘管理系统")
        st.markdown("请输入系统访问密码")

        pwd = st.text_input("系统密码", type="password", key="global_pwd_input")
        if st.button("验证", type="primary", use_container_width=True):
            correct_pwd = st.secrets.get("GLOBAL_PASSWORD", "202603")
            if pwd == correct_pwd:
                st.session_state.global_authenticated = True
                st.rerun()
            else:
                st.error("❌ 密码错误，请重试")
        st.stop()


# ============================================================
# 用户登录管理
# ============================================================

def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希。"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配哈希值。"""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def login_user(email: str, password: str) -> tuple:
    """
    验证用户登录。
    Returns: (success: bool, user_data: dict | str)
    """
    supabase = get_supabase_client()
    if supabase is None:
        return False, "数据库连接失败"

    try:
        result = supabase.table("users").select("*").eq("email", email).execute()
        if not result.data:
            return False, "用户不存在"

        user = result.data[0]
        if not user.get("is_active", True):
            return False, "该账号已被禁用"

        if verify_password(password, user["password_hash"]):
            return True, {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "role": user["role"],
            }
        else:
            return False, "密码错误"
    except Exception as e:
        return False, str(e)


def register_user(email: str, username: str, password: str, role: str = "hr") -> tuple:
    """注册新用户（仅管理员可操作）。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False, "数据库连接失败"

    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return False, "该邮箱已被注册"

        user_data = {
            "email": email,
            "username": username,
            "password_hash": hash_password(password),
            "role": role,
        }
        supabase.table("users").insert(user_data).execute()
        return True, "注册成功"
    except Exception as e:
        return False, str(e)


def get_all_users() -> list:
    """获取所有用户列表（管理员功能）。"""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    try:
        result = supabase.table("users").select("*").order("created_at").execute()
        return result.data
    except Exception:
        return []


def ensure_user_session():
    """全局密码通过后自动以管理员身份进入。"""
    if "user" not in st.session_state:
        st.session_state.user = {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "admin@ats.com",
            "username": "管理员",
            "role": "admin",
        }


def show_login_page():
    """渲染用户登录页面。"""
    st.title("🔐 用户登录")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email = st.text_input("邮箱", placeholder="admin@ats.com")
        password = st.text_input("密码", type="password")

        if st.button("登录", type="primary", use_container_width=True):
            success, result = login_user(email, password)
            if success:
                st.session_state.user = result
                st.rerun()
            else:
                st.error(f"❌ {result}")

        st.caption("默认管理员: admin@ats.com / admin123")


# ============================================================
# 用户管理页面（管理员功能）
# ============================================================

def show_user_management():
    """渲染用户管理界面（仅管理员可见）。"""
    st.subheader("👥 用户管理")

    # 新增用户表单
    with st.expander("➕ 新增用户", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_email = st.text_input("邮箱", key="new_user_email")
            new_username = st.text_input("用户名", key="new_user_username")
        with col2:
            new_password = st.text_input("密码", type="password", key="new_user_pwd")
            new_role = st.selectbox("角色", ["hr", "admin"], key="new_user_role")

        if st.button("创建用户", type="primary"):
            if not new_email or not new_username or not new_password:
                st.error("请填写所有字段")
            else:
                success, msg = register_user(new_email, new_username, new_password, new_role)
                if success:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    # 用户列表
    users = get_all_users()
    if users:
        import pandas as pd
        df = pd.DataFrame(users)
        df_display = df[["username", "email", "role", "is_active", "created_at"]].copy()
        df_display.columns = ["用户名", "邮箱", "角色", "启用", "创建时间"]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
