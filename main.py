"""
ATS 招聘管理系统 - 主入口
部署: streamlit run main.py
"""
import streamlit as st
import pandas as pd
from utils.auth import check_global_password, ensure_user_session
from utils.supabase_client import get_positions, get_candidates, get_kpi_data

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="ATS 招聘管理系统",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 全局密码校验
# ============================================================
check_global_password()

# ============================================================
# 用户登录
# ============================================================
ensure_user_session()

# ============================================================
# 首页仪表盘
# ============================================================
st.title("📋 ATS 招聘管理系统")
st.markdown("AI 驱动的招聘全流程管理平台 —— 职位管理 · 简历解析 · 流程跟踪 · 数据看板")

st.markdown("---")

# 快速统计卡片
kpi = get_kpi_data()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    total_candidates = kpi.get("total_candidates", 0)
    st.metric("📄 人才库总量", total_candidates)
with col2:
    positions = get_positions("open")
    st.metric("📌 在招岗位", len(positions))
with col3:
    avg_score = kpi.get("avg_ai_score", 0)
    st.metric("⭐ 平均 AI 评分", f"{avg_score:.1f}" if avg_score else "N/A")
with col4:
    stage_stats = kpi.get("stage_stats", {})
    in_interview = stage_stats.get("初试-通过", 0) + stage_stats.get("复试-通过", 0)
    st.metric("🎯 面试中", in_interview)
with col5:
    hired = stage_stats.get("已入职", 0) + stage_stats.get("试用期评估-通过", 0)
    st.metric("✅ 已入职", hired)

st.markdown("---")

# 在招岗位列表
st.subheader("📌 当前在招岗位")
positions = get_positions("open")
if positions:
    pos_data = []
    for p in positions:
        from utils.supabase_client import get_position_candidates_count
        cnt = get_position_candidates_count(p["id"])
        pos_data.append({
            "岗位名称": p["title"],
            "部门": p.get("department", "-"),
            "编制": p.get("headcount", 1),
            "投递数": cnt,
            "JD 摘要": (p.get("jd_description", "") or "")[:80] + "...",
        })
    pos_df = pd.DataFrame(pos_data)
    st.dataframe(pos_df, use_container_width=True, hide_index=True)
else:
    st.info("暂无在招岗位，请前往 [职位管理](/职位管理) 添加。")

st.markdown("---")

# 最近候选人
st.subheader("🆕 最近入库候选人")
candidates = get_candidates()
if candidates:
    recent = candidates[:10]
    cand_data = []
    for c in recent:
        cand_data.append({
            "姓名": c.get("name", "-"),
            "学历": c.get("education", "-"),
            "院校": c.get("school", "-"),
            "AI 评分": c.get("ai_score", "-"),
            "状态": c.get("status", "-"),
        })
    cand_df = pd.DataFrame(cand_data)
    st.dataframe(cand_df, use_container_width=True, hide_index=True)
else:
    st.info("暂无候选人数据，请前往 [简历上传](/简历上传与AI解析) 添加。")

st.markdown("---")

# 招聘漏斗概览
st.subheader("📊 招聘漏斗概览")
stage_stats = kpi.get("stage_stats", {})
if stage_stats:
    funnel_stages = [
        ("初筛-通过", "初筛通过"),
        ("联系反馈", "联系反馈"),
        ("部门筛选-通过", "部门筛选通过"),
        ("初试-通过", "初试通过"),
        ("复试-通过", "复试通过"),
        ("接Offer", "接Offer"),
        ("已入职", "已入职"),
        ("试用期评估-通过", "转正"),
    ]

    funnel_data = []
    for stage_key, label in funnel_stages:
        count = stage_stats.get(stage_key, 0)
        funnel_data.append({"阶段": label, "人数": count})

    funnel_df = pd.DataFrame(funnel_data)
    st.bar_chart(funnel_df.set_index("阶段"), use_container_width=True)
else:
    st.info("暂无流程数据")

