"""
人才库模块 - 简历筛选、搜索、公海池管理
"""
import streamlit as st
import pandas as pd

from utils.auth import check_global_password, ensure_user_session
from utils.supabase_client import (
    get_positions, get_candidates, update_candidate, delete_candidate,
    get_candidate_positions, link_candidate_to_position,
    get_position_candidates_count, get_current_stage, advance_stage,
    get_supabase_client,
)

check_global_password()
ensure_user_session()

st.title("🔍 人才库")
st.markdown("全量候选人管理，支持按岗位、状态、关键词筛选。")

# ============================================================
# 筛选器
# ============================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    # 岗位筛选
    positions = get_positions()
    pos_options = {"全部岗位": None}
    for p in positions:
        pos_options[f"{p['title']} ({p.get('status', '')})"] = p["id"]

    # 检查是否从职位管理跳转过来的
    preselected = None
    prefilled_title = st.session_state.get("filter_by_position_title", "")
    prefilled_id = st.session_state.get("filter_by_position")
    if prefilled_id and prefilled_title:
        prefilled_display = [k for k, v in pos_options.items() if v == prefilled_id]
        if prefilled_display:
            preselected = list(pos_options.keys()).index(prefilled_display[0])

    selected_pos_label = st.selectbox(
        "🎯 岗位筛选",
        list(pos_options.keys()),
        index=preselected if preselected is not None else 0,
        key="talent_pos_filter",
    )
    selected_pos_id = pos_options[selected_pos_label]

    # 清除跳转状态
    if prefilled_id:
        st.session_state.filter_by_position = None
        st.session_state.filter_by_position_title = None

with col2:
    status_options = ["全部", "new", "active", "archived", "hired", "public_pool"]
    status_labels = {"全部": None, "new": "新入库", "active": "流程中", "archived": "已归档", "hired": "已入职", "public_pool": "公海池"}
    selected_status_label = st.selectbox(
        "📊 状态筛选",
        list(status_labels.keys()),
        format_func=lambda x: status_labels[x],
        key="talent_status_filter",
    )
    selected_status = status_labels[selected_status_label]

with col3:
    search_text = st.text_input("🔎 搜索", placeholder="姓名、手机、学校...", key="talent_search")

with col4:
    sort_by = st.selectbox("📐 排序", ["AI评分降序", "入库时间降序", "姓名"], key="talent_sort")

# ============================================================
# 获取候选人
# ============================================================
candidates = get_candidates(
    status_filter=selected_status,
    position_id=selected_pos_id,
    search_text=search_text if search_text else None,
)

# 排序
if sort_by == "AI评分降序":
    candidates.sort(key=lambda x: x.get("ai_score", 0) or 0, reverse=True)
elif sort_by == "入库时间降序":
    candidates.sort(key=lambda x: x.get("created_at", ""), reverse=True)
elif sort_by == "姓名":
    candidates.sort(key=lambda x: x.get("name", ""))

# 如果指定了岗位但候选人列表为空，从该岗位关联中重新获取
if selected_pos_id and not candidates:
    supabase = get_supabase_client()
    if supabase:
        cp_result = supabase.table("candidate_positions").select("candidate_id") \
            .eq("position_id", selected_pos_id).execute()
        cp_ids = {r["candidate_id"] for r in cp_result.data}
        if cp_ids:
            all_candidates = get_candidates()
            candidates = [c for c in all_candidates if c["id"] in cp_ids]
            # 重新排序
            if sort_by == "AI评分降序":
                candidates.sort(key=lambda x: x.get("ai_score", 0) or 0, reverse=True)
            elif sort_by == "入库时间降序":
                candidates.sort(key=lambda x: x.get("created_at", ""), reverse=True)

# ============================================================
# 统计摘要
# ============================================================
st.markdown("---")
col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    st.metric("📋 当前显示", len(candidates))
with col_b:
    avg = sum(c.get("ai_score", 0) or 0 for c in candidates) / len(candidates) if candidates else 0
    st.metric("⭐ 平均评分", f"{avg:.1f}")
with col_c:
    passed = sum(1 for c in candidates if c.get("hard_match"))
    st.metric("✅ 硬性通过", passed)
with col_d:
    public = sum(1 for c in candidates if c.get("status") == "public_pool")
    st.metric("🌊 公海池", public)

# ============================================================
# 候选人表格
# ============================================================
st.markdown("---")
st.subheader(f"📋 候选人列表 ({len(candidates)} 人)")

if not candidates:
    st.info("暂无符合条件的候选人。")
else:
    # 构建表格数据
    table_rows = []
    for c in candidates:
        score = c.get("ai_score", 0) or 0
        score_icon = "🟢" if score >= 75 else ("🟡" if score >= 60 else "🔴")
        status_map = {
            "new": "🆕 新入库", "active": "🔄 流程中",
            "archived": "📦 已归档", "hired": "✅ 已入职",
            "public_pool": "🌊 公海池",
        }
        table_rows.append({
            "ID": c["id"],
            "姓名": c.get("name", "-"),
            "性别": c.get("gender", "-"),
            "学历": c.get("education", "-"),
            "院校": c.get("school", "-"),
            "手机号": c.get("phone", "-"),
            "AI评分": f"{score_icon} {score}",
            "硬性匹配": "✅" if c.get("hard_match") else "❌",
            "状态": status_map.get(c.get("status", "new"), c.get("status", "")),
            "优势": (c.get("ai_strengths", "") or "")[:40],
            "风险": (c.get("ai_risks", "") or "")[:40],
        })

    df = pd.DataFrame(table_rows)

    # 显示表格并获取选中行
    selection = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=400,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "ID": None,  # 隐藏 ID 列
        },
    )

    # ============================================================
    # 候选人详情与操作
    # ============================================================
    st.markdown("---")
    st.subheader("📄 候选人详情")

    # 处理选中
    selected_candidate = None
    if selection and len(selection.selection.rows) > 0:
        row_idx = selection.selection.rows[0]
        if row_idx < len(candidates):
            selected_candidate = candidates[row_idx]
            st.session_state.selected_candidate_id = selected_candidate["id"]
    elif st.session_state.get("selected_candidate_id"):
        # 从 session 中恢复
        cid = st.session_state.selected_candidate_id
        matches = [c for c in candidates if c["id"] == cid]
        if matches:
            selected_candidate = matches[0]

    if selected_candidate:
        c = selected_candidate
        col_d1, col_d2, col_d3 = st.columns([2, 2, 1])

        with col_d1:
            st.markdown(f"### {c.get('name', '未知')}")
            st.markdown(f"📧 {c.get('email', '-')}  |  📱 {c.get('phone', '-')}")
            st.markdown(f"🎓 {c.get('education', '-')}  |  🏫 {c.get('school', '-')}")
            st.markdown(f"📖 {c.get('major', '-')}  |  🎓 {c.get('graduation_year', '-')}届")
            st.markdown(f"💼 {c.get('current_company', '-')}  |  🕐 {c.get('work_years', '-')}年经验")

        with col_d2:
            score = c.get("ai_score", 0) or 0
            st.metric("⭐ AI 综合评分", f"{score}/100")
            st.markdown(f"**硬性匹配:** {'✅ 通过' if c.get('hard_match') else '❌ 未通过'}")
            st.markdown(f"📝 {c.get('hard_match_detail', '')}")

            # 获取关联职位
            pos_list = get_candidate_positions(c["id"])
            if pos_list:
                st.markdown("**关联岗位:**")
                for p in pos_list:
                    st.caption(f"• {p.get('title', '-')}")

        with col_d3:
            # 快速操作
            new_status = st.selectbox(
                "状态变更",
                ["new", "active", "archived", "hired", "public_pool"],
                format_func=lambda x: {"new": "新入库", "active": "流程中", "archived": "已归档", "hired": "已入职", "public_pool": "公海池"}[x],
                key=f"status_{c['id']}",
            )
            if new_status != c.get("status"):
                if st.button("💾 更新状态", key=f"update_status_{c['id']}", use_container_width=True):
                    update_candidate(c["id"], status=new_status)
                    st.rerun()

            if st.button("🗑️ 删除", key=f"delete_{c['id']}", use_container_width=True):
                delete_candidate(c["id"])
                st.rerun()

        # 优势与风险
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**💪 核心优势:**")
            st.markdown(c.get("ai_strengths", "无"))
        with col_s2:
            st.markdown("**⚠️ 潜在风险:**")
            st.markdown(c.get("ai_risks", "无"))

        with st.expander(f"📝 AI 综合评语 —— {c.get('name', '')}", expanded=False):
            ai_raw = c.get("ai_raw_response", "")
            if ai_raw:
                try:
                    import json
                    ai_data = json.loads(ai_raw)
                    st.json(ai_data)
                except Exception:
                    st.text(ai_raw)

        # ============================================================
        # 关联/切换岗位
        # ============================================================
        st.markdown("---")
        st.subheader("🔗 岗位关联")
        current_positions = get_candidate_positions(c["id"])
        current_pos_ids = {p["id"] for p in current_positions}

        available_positions = [p for p in get_positions("open") if p["id"] not in current_pos_ids]
        if available_positions:
            col_link1, col_link2 = st.columns([3, 1])
            with col_link1:
                link_pos = st.selectbox(
                    "关联到新岗位",
                    [p["title"] for p in available_positions],
                    key=f"link_{c['id']}",
                )
            with col_link2:
                if st.button("🔗 关联", key=f"btn_link_{c['id']}", use_container_width=True):
                    pos_obj = next(p for p in available_positions if p["title"] == link_pos)
                    link_candidate_to_position(c["id"], pos_obj["id"])
                    st.rerun()

        # 当前岗位及流程状态
        if current_positions:
            st.markdown("**已关联岗位及流程状态:**")
            for pos in current_positions:
                stage = get_current_stage(c["id"], pos["id"])
                stage_name = stage["stage"] if stage else "未进入流程"
                col_p1, col_p2 = st.columns([3, 1])
                with col_p1:
                    st.markdown(f"• **{pos.get('title', '-')}** → `{stage_name}`")
                with col_p2:
                    if st.button("➡️ 流程", key=f"goto_pipeline_{c['id']}_{pos['id']}"):
                        st.session_state.pipeline_candidate = c["id"]
                        st.session_state.pipeline_position = pos["id"]
                        st.switch_page("pages/4_🔄_招聘流程跟踪.py")

    else:
        st.info("👆 请在上方表格中点击选择一位候选人查看详情")
