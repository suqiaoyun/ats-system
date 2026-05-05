"""
招聘流程跟踪模块 - 全流程状态机管理
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from utils.auth import check_global_password, ensure_user_session
from utils.supabase_client import (
    get_positions, get_candidates, get_candidate_positions,
    get_current_stage, advance_stage, get_pipeline_history,
    add_communication_note, get_communication_notes,
    get_pipeline_stages, update_candidate, link_candidate_to_position,
    get_position_candidates_count,
)

check_global_password()
ensure_user_session()

st.title("🔄 招聘流程跟踪")
st.markdown("管理每位候选人的招聘进度，记录沟通反馈。")

# ============================================================
# 选择岗位和候选人
# ============================================================
col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    positions = get_positions()
    pos_options = {p["title"]: p for p in positions}
    selected_title = st.selectbox(
        "🎯 选择岗位",
        list(pos_options.keys()),
        key="pipeline_pos",
        index=None if not st.session_state.get("pipeline_position") else
            next((i for i, p in enumerate(positions) if p["id"] == st.session_state.get("pipeline_position")), 0),
    )

with col_sel2:
    # 状态快捷筛选
    stage_filter_labels = ["全部", "初筛-通过", "初筛-淘汰", "联系反馈", "部门筛选-通过",
                           "初试-通过", "复试-通过", "面试淘汰", "接Offer", "已入职",
                           "试用期评估-通过", "公海池"]
    stage_filter = st.selectbox("📊 阶段筛选", stage_filter_labels, key="pipeline_stage_filter")

# 清除跳转状态
if st.session_state.get("pipeline_position"):
    st.session_state.pipeline_position = None
if st.session_state.get("pipeline_candidate"):
    st.session_state.pipeline_candidate = None

if not selected_title:
    st.info("👈 请先选择一个岗位以查看其候选人流程。")
    st.stop()

selected_pos = pos_options[selected_title]
pos_id = selected_pos["id"]

# ============================================================
# 获取该岗位的候选人及其流程状态
# ============================================================
candidates = get_candidates(position_id=pos_id)

# 构建包含流程状态的数据
pipeline_data = []
for c in candidates:
    stage = get_current_stage(c["id"], pos_id)
    stage_name = stage["stage"] if stage else "未进入流程"
    stage_notes = stage.get("notes", "") if stage else ""

    # 阶段筛选
    if stage_filter != "全部":
        if stage_filter == "面试淘汰":
            if stage_name not in ["初试-淘汰", "复试-淘汰"]:
                continue
        else:
            if stage_name != stage_filter:
                continue

    pipeline_data.append({
        "candidate": c,
        "stage": stage_name,
        "stage_time": stage.get("created_at", "") if stage else "",
        "notes": stage_notes,
    })

st.markdown("---")
st.subheader(f"📋 {selected_title} —— 候选人流程 ({len(pipeline_data)} 人)")

# ============================================================
# 流程看板
# ============================================================
if not pipeline_data:
    st.info("暂无候选人进入此岗位的流程。")
else:
    # 按阶段分组
    stages_order = [
        "未进入流程", "初筛-通过", "联系反馈", "部门筛选-通过",
        "初试-通过", "复试-通过", "发Offer", "接Offer",
        "已入职", "试用期评估-通过", "试用期评估-未通过",
        "初筛-淘汰", "部门筛选-淘汰", "初试-淘汰", "复试-淘汰",
        "拒Offer", "公海池",
    ]

    stage_groups = {}
    for item in pipeline_data:
        s = item["stage"]
        stage_groups.setdefault(s, []).append(item)

    # 看板列
    active_stages = [s for s in stages_order if s in stage_groups]

    if active_stages:
        cols = st.columns(min(len(active_stages), 5))

        for i, stage_name in enumerate(active_stages[:5]):  # 最多显示5列
            items = stage_groups[stage_name]
            col_idx = i % 5
            with cols[col_idx]:
                color_map = {
                    "未进入流程": "gray", "初筛-通过": "blue",
                    "联系反馈": "orange", "部门筛选-通过": "violet",
                    "初试-通过": "green", "复试-通过": "green",
                    "发Offer": "orange", "接Offer": "green",
                    "已入职": "green", "试用期评估-通过": "green",
                }
                # 淘汰状态用红色
                if "淘汰" in stage_name or "未通过" in stage_name or stage_name == "拒Offer":
                    color_map[stage_name] = "red"

                color = color_map.get(stage_name, "gray")
                st.markdown(f"##### {stage_name} ({len(items)})")

                for item in items:
                    c = item["candidate"]
                    score = c.get("ai_score", 0) or 0
                    with st.container(border=True):
                        st.markdown(f"**{c.get('name', '-')}**")
                        st.caption(f"⭐ {score} | 🎓 {c.get('education', '-')}")
                        if st.button("详情", key=f"kanban_{c['id']}", use_container_width=True):
                            st.session_state.detail_candidate = c["id"]
                            st.rerun()

    # ============================================================
    # 候选人表格列表
    # ============================================================
    st.markdown("---")
    st.subheader("📊 列表视图")

    table_rows = []
    for item in pipeline_data:
        c = item["candidate"]
        score = c.get("ai_score", 0) or 0
        score_icon = "🟢" if score >= 75 else ("🟡" if score >= 60 else "🔴")
        table_rows.append({
            "ID": c["id"],
            "姓名": c.get("name", "-"),
            "AI评分": f"{score_icon} {score}",
            "学历": c.get("education", "-"),
            "院校": c.get("school", "-"),
            "当前阶段": item["stage"],
            "更新时间": item["stage_time"][:10] if item["stage_time"] else "-",
        })

    if table_rows:
        df = pd.DataFrame(table_rows)
        selection = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=350,
            on_select="rerun",
            selection_mode="single-row",
            column_config={"ID": None},
        )

        # 处理选中
        if selection and len(selection.selection.rows) > 0:
            row_idx = selection.selection.rows[0]
            if row_idx < len(pipeline_data):
                st.session_state.detail_candidate = pipeline_data[row_idx]["candidate"]["id"]

# ============================================================
# 候选人流程详情与操作
# ============================================================
if st.session_state.get("detail_candidate"):
    cid = st.session_state.detail_candidate
    candidate = next((c for c in candidates if c["id"] == cid), None)

    if candidate:
        st.markdown("---")
        st.subheader(f"📄 流程详情: {candidate.get('name', '未知')}")

        current_stage_info = get_current_stage(cid, pos_id)
        current_stage_name = current_stage_info["stage"] if current_stage_info else "未进入流程"
        current_stage_notes = current_stage_info.get("notes", "") if current_stage_info else ""

        col_info1, col_info2 = st.columns([2, 1])

        with col_info1:
            st.markdown(f"**当前阶段:** `{current_stage_name}`")
            st.markdown(f"**候选人:** {candidate.get('name', '-')} | {candidate.get('education', '-')} | {candidate.get('school', '-')}")
            score = candidate.get("ai_score", 0) or 0
            st.markdown(f"**AI 评分:** ⭐ {score}/100 | 硬性匹配: {'✅' if candidate.get('hard_match') else '❌'}")

        with col_info2:
            # 推进到下一阶段
            all_stages = get_pipeline_stages()

            # 根据当前阶段智能推荐下一步
            next_stage_map = {
                "初筛-通过": ["联系反馈", "初筛-淘汰", "公海池"],
                "初筛-淘汰": ["公海池", "联系反馈"],
                "联系反馈": ["部门筛选-通过", "部门筛选-淘汰", "初筛-淘汰"],
                "部门筛选-通过": ["初试-通过", "初试-淘汰"],
                "部门筛选-淘汰": ["公海池"],
                "初试-通过": ["复试-通过", "复试-淘汰"],
                "初试-淘汰": ["公海池"],
                "复试-通过": ["发Offer"],
                "复试-淘汰": ["公海池"],
                "发Offer": ["接Offer", "拒Offer"],
                "接Offer": ["已入职"],
                "拒Offer": ["公海池"],
                "已入职": ["试用期评估-通过", "试用期评估-未通过"],
                "试用期评估-通过": [],
                "试用期评估-未通过": [],
                "公海池": ["联系反馈"],
            }

            recommended = next_stage_map.get(current_stage_name, all_stages)
            if not recommended:
                recommended = all_stages

            # 对于未进入流程的候选人，直接引导到初筛
            if current_stage_name == "未进入流程":
                recommended = ["初筛-通过", "初筛-淘汰"]

            new_stage = st.selectbox(
                "推进到",
                recommended,
                key=f"advance_{cid}",
            )
            stage_notes = st.text_area("备注", key=f"notes_{cid}", height=60)

            user_id = st.session_state.user.get("id") if st.session_state.user else None

            if st.button("✅ 确认推进", type="primary", key=f"confirm_{cid}", use_container_width=True):
                success = advance_stage(cid, pos_id, new_stage, stage_notes, user_id)
                if success:
                    # 如果推进到公海池，更新候选人状态
                    if new_stage == "公海池":
                        update_candidate(cid, status="public_pool")
                    elif new_stage in ["已入职", "试用期评估-通过"]:
                        update_candidate(cid, status="hired")
                    elif new_stage not in ["初筛-淘汰", "初筛-通过"]:
                        update_candidate(cid, status="active")

                    st.success(f"✅ 已推进至「{new_stage}」")
                    st.rerun()

        # ============================================================
        # 流程历史
        # ============================================================
        st.markdown("---")
        col_hist, col_comm = st.columns(2)

        with col_hist:
            st.subheader("📜 流程历史")
            history = get_pipeline_history(cid, pos_id)
            if history:
                for h in history:
                    icon = "🟢" if "通过" in h["stage"] else ("🔴" if "淘汰" in h["stage"] or "未通过" in h["stage"] else "🔵")
                    st.markdown(f"{icon} **{h['stage']}**")
                    st.caption(f"{h.get('created_at', '')[:16]}")
                    if h.get("notes"):
                        st.caption(f"📝 {h['notes']}")
                    st.markdown("---")
            else:
                st.info("暂无流程记录")

        with col_comm:
            st.subheader("💬 沟通记录")
            notes = get_communication_notes(cid, pos_id)
            if notes:
                for n in notes:
                    st.markdown(f"📝 {n.get('content', '')}")
                    st.caption(f"—— {n.get('created_at', '')[:16]}")
                    st.markdown("---")
            else:
                st.info("暂无沟通记录")

            # 添加沟通记录
            new_note = st.text_area("添加沟通记录", key=f"comm_{cid}", height=80, placeholder="记录与候选人的沟通内容...")
            if st.button("💾 保存沟通记录", key=f"save_comm_{cid}"):
                if new_note.strip():
                    add_communication_note(cid, pos_id, new_note, user_id)
                    st.rerun()
