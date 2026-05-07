"""
认证模块 - 简化版：直接放行
"""
import streamlit as st


def check_global_password():
    """取消密码验证，直接通过。"""
    st.session_state.global_authenticated = True


def ensure_user_session():
    """自动以管理员身份进入。"""
    if "user" not in st.session_state:
        st.session_state.user = {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "admin@ats.com",
            "username": "管理员",
            "role": "admin",
        }
