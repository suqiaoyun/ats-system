"""
职位管理模块 - 新增、编辑、删除招聘岗位
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from utils.auth import check_global_password, ensure_user_session
from utils.supabase_client import (
    get_positions, create_position, update_position, delete_position,
    get_position_candidates_count,
)

check_global_password()
ensure_user_session()

st.title("📌 职位管理")
st.markdown("管理公司当前所有在招岗位，配置 JD 与任职要求。")

# ============================================================
# 新增职位
# ============================================================
with st.expander("➕ 新增职位", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("岗位名称", placeholder="如: 高级前端工程师")
        department = st.text_input("部门", placeholder="如: 技术部")
    with col2:
        headcount = st.number_input("编制人数", min_value=1, value=1)
        status = st.selectbox("初始状态", ["open", "draft"], format_func=lambda x: "开放招聘" if x == "open" else "草稿")

    st.markdown("---")
    jd_description = st.text_area(
        "岗位职责 (JD)",
        placeholder="描述该岗位的主要职责和工作内容...",
        height=120,
    )
    requirements = st.text_area(
        "任职要求",
        placeholder="描述该岗位的技能要求、经验要求等...",
        height=120,
    )
    hard_requirements = st.text_area(
        "硬性红线要求",
        placeholder="如: 硕士及以上学历、5年以上经验、必须掌握XX技能...",
        height=80,
    )
    bonus_requirements = st.text_area(
        "加分项",
        placeholder="如: 有大厂经历、开源贡献、发表过顶会论文、CPA/CFA 等证书...",
        height=80,
    )

    if st.button("💾 保存职位", type="primary", use_container_width=True):
        if not title:
            st.error("请填写岗位名称")
        elif not jd_description:
            st.error("请填写岗位职责")
        else:
            user_id = st.session_state.user.get("id") if st.session_state.user else None
            success = create_position(
                title=title,
                jd_description=jd_description,
                requirements=requirements,
                hard_requirements=hard_requirements,
                bonus_requirements=bonus_requirements,
                department=department,
                headcount=headcount,
                created_by=user_id,
            )
            if success:
                st.success(f"✅ 职位「{title}」创建成功")
                st.rerun()

# ============================================================
# 职位列表与操作
# ============================================================
st.markdown("---")
st.subheader("📋 职位列表")

status_filter = st.radio(
    "状态筛选",
    ["全部", "开放中", "已关闭", "草稿"],
    horizontal=True,
    key="pos_status_filter",
)

filter_map = {"开放中": "open", "已关闭": "closed", "草稿": "draft"}
status_value = filter_map.get(status_filter)

positions = get_positions(status_value)

if not positions:
    st.info("暂无职位数据，请点击上方「新增职位」添加。")
else:
    for i, pos in enumerate(positions):
        cnt = get_position_candidates_count(pos["id"])

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 0.8, 0.8])
            with col1:
                status_emoji = {"open": "🟢", "closed": "🔴", "draft": "⚪"}
                emoji = status_emoji.get(pos.get("status", ""), "⚪")
                st.markdown(f"**{emoji} {pos['title']}**")
                st.caption(f"{pos.get('department', '-')} | 编制: {pos.get('headcount', 1)} | 投递: {cnt}")
            with col2:
                if st.button("📝 编辑", key=f"edit_{pos['id']}", use_container_width=True):
                    st.session_state.editing_position = pos["id"]
                    st.session_state.edit_data = pos
                    st.rerun()
            with col3:
                if st.button("🔍 查看候选人", key=f"view_{pos['id']}", use_container_width=True):
                    st.session_state.filter_by_position = pos["id"]
                    st.session_state.filter_by_position_title = pos["title"]
                    st.switch_page("pages/3_🔍_人才库.py")
            with col4:
                new_status = "closed" if pos.get("status") == "open" else "open"
                btn_label = "🔒 关闭" if pos.get("status") == "open" else "🔓 重开"
                if st.button(btn_label, key=f"toggle_{pos['id']}", use_container_width=True):
                    update_position(pos["id"], status=new_status)
                    st.rerun()
            with col5:
                if st.button("🗑️", key=f"del_{pos['id']}", use_container_width=True, help="删除此职位"):
                    delete_position(pos["id"])
                    st.rerun()

        # 展开 JD 详情
        with st.expander(f"查看 JD 详情 —— {pos['title']}", expanded=False):
            st.markdown("**岗位职责:**")
            st.markdown(pos.get("jd_description", "无"))
            st.markdown("**任职要求:**")
            st.markdown(pos.get("requirements", "无"))
            st.markdown("**硬性红线:**")
            st.markdown(pos.get("hard_requirements", "无"))
            st.markdown("**加分项:**")
            st.markdown(pos.get("bonus_requirements", "无"))

        st.markdown("---")

# ============================================================
# 编辑职位弹窗
# ============================================================
if st.session_state.get("editing_position"):
    pos_id = st.session_state.editing_position
    edit_data = st.session_state.get("edit_data", {})

    with st.expander("✏️ 编辑职位（当前正在编辑）", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("岗位名称", value=edit_data.get("title", ""), key="edit_title")
            new_dept = st.text_input("部门", value=edit_data.get("department", ""), key="edit_dept")
        with col2:
            new_hc = st.number_input("编制人数", value=edit_data.get("headcount", 1), key="edit_hc")

        new_jd = st.text_area("岗位职责", value=edit_data.get("jd_description", ""), key="edit_jd", height=120)
        new_req = st.text_area("任职要求", value=edit_data.get("requirements", ""), key="edit_req", height=120)
        new_hard = st.text_area("硬性红线", value=edit_data.get("hard_requirements", ""), key="edit_hard", height=80)
        new_bonus = st.text_area("加分项", value=edit_data.get("bonus_requirements", ""), key="edit_bonus", height=80)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 保存修改", type="primary", use_container_width=True):
                success = update_position(
                    pos_id,
                    title=new_title,
                    department=new_dept,
                    headcount=new_hc,
                    jd_description=new_jd,
                    requirements=new_req,
                    hard_requirements=new_hard,
                    bonus_requirements=new_bonus,
                )
                if success:
                    st.success("✅ 修改已保存")
                    st.session_state.editing_position = None
                    st.session_state.edit_data = {}
                    st.rerun()
        with c2:
            if st.button("🗑️ 删除此职位", type="secondary", use_container_width=True):
                if delete_position(pos_id):
                    st.success("✅ 职位已删除")
                    st.session_state.editing_position = None
                    st.session_state.edit_data = {}
                    st.rerun()

        if st.button("❌ 取消编辑", use_container_width=True):
            st.session_state.editing_position = None
            st.session_state.edit_data = {}
            st.rerun()
