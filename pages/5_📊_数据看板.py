"""
数据看板 KPI Dashboard - 招聘效能核心指标可视化
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.auth import check_global_password, ensure_user_session
from utils.supabase_client import (
    get_positions, get_candidates, get_kpi_data,
    get_position_candidates_count, get_pipeline_stats,
)

check_global_password()
ensure_user_session()

st.title("📊 招聘效能看板")
st.markdown("KPI 核心指标 · 转化率 · 质量分布 · 渠道分析")

kpi = get_kpi_data()

# ============================================================
# 顶部 KPI 卡片
# ============================================================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📄 人才库总量", kpi.get("total_candidates", 0))
with col2:
    avg_score = kpi.get("avg_ai_score", 0)
    st.metric("⭐ 平均 AI 评分", f"{avg_score:.1f}")
with col3:
    stage_stats = kpi.get("stage_stats", {})
    total_in_pipeline = sum(stage_stats.values())
    st.metric("🔄 流程中候选人", total_in_pipeline)
with col4:
    hired = stage_stats.get("已入职", 0) + stage_stats.get("试用期评估-通过", 0)
    st.metric("✅ 已入职", hired)

st.markdown("---")

# ============================================================
# 第一行：转化率漏斗 + AI 评分分布
# ============================================================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 招聘转化漏斗")

    stage_stats = kpi.get("stage_stats", {})

    # 漏斗阶段 (从上到下)
    funnel_stages = [
        ("初筛-通过", "初筛通过"),
        ("联系反馈", "HR 联系"),
        ("部门筛选-通过", "部门通过"),
        ("初试-通过", "初试通过"),
        ("复试-通过", "复试通过"),
        ("接Offer", "接 Offer"),
        ("已入职", "正式入职"),
        ("试用期评估-通过", "转正"),
    ]

    funnel_values = []
    funnel_labels = []
    for stage_key, label in funnel_stages:
        count = stage_stats.get(stage_key, 0)
        funnel_values.append(count)
        funnel_labels.append(label)

    if sum(funnel_values) > 0:
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_labels,
            x=funnel_values,
            textinfo="value+percent initial",
            marker={"color": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
                              "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]},
        ))
        fig_funnel.update_layout(height=400)
        st.plotly_chart(fig_funnel, use_container_width=True)

        # 计算并显示转化率
        st.markdown("**转化率明细:**")
        for i in range(1, len(funnel_values)):
            if funnel_values[i - 1] > 0:
                rate = funnel_values[i] / funnel_values[i - 1] * 100
                st.caption(f"{funnel_labels[i-1]} → {funnel_labels[i]}: {rate:.1f}%")
    else:
        st.info("暂无流程数据，开始招聘后此处将展示转化漏斗。")

with col_right:
    st.subheader("⭐ AI 评分分布")

    candidates = get_candidates()
    scores = [c.get("ai_score", 0) or 0 for c in candidates if c.get("ai_score") is not None]

    if scores:
        # 分段统计
        bins = [0, 40, 60, 75, 90, 101]
        labels = ["0-39 不匹配", "40-59 部分匹配", "60-74 基本匹配", "75-89 较匹配", "90-100 非常匹配"]
        score_segments = pd.cut(scores, bins=bins, labels=labels, right=False)
        segment_counts = score_segments.value_counts().sort_index()

        fig_pie = px.pie(
            values=segment_counts.values,
            names=segment_counts.index,
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.4,
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("暂无评分数据")

st.markdown("---")

# ============================================================
# 第二行：各岗位对比 + 学历分布
# ============================================================
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("📌 各岗位候选人分布")

    positions = get_positions()
    pos_stats = []
    for p in positions:
        cnt = get_position_candidates_count(p["id"])
        if cnt > 0:
            pos_stats.append({"岗位": p["title"], "候选人数量": cnt, "状态": p.get("status", "")})

    if pos_stats:
        fig_bar = px.bar(
            pd.DataFrame(pos_stats),
            x="岗位", y="候选人数量",
            color="状态",
            color_discrete_map={"open": "#2ca02c", "closed": "#d62728", "draft": "#7f7f7f"},
            text="候选人数量",
        )
        fig_bar.update_layout(height=350)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("暂无数据")

with col_right2:
    st.subheader("🎓 学历分布")

    edu_stats = kpi.get("edu_stats", {})
    if edu_stats:
        fig_edu = px.pie(
            values=list(edu_stats.values()),
            names=list(edu_stats.keys()),
            hole=0.4,
        )
        fig_edu.update_layout(height=350)
        st.plotly_chart(fig_edu, use_container_width=True)
    else:
        st.info("暂无学历数据")

st.markdown("---")

# ============================================================
# 第三行：院校分布 + 各岗位平均评分
# ============================================================
col_left3, col_right3 = st.columns(2)

with col_left3:
    st.subheader("🏫 院校分布 TOP 15")

    school_stats = kpi.get("school_stats", {})
    if school_stats:
        school_sorted = sorted(school_stats.items(), key=lambda x: x[1], reverse=True)[:15]
        fig_school = px.bar(
            x=[s[0] for s in school_sorted],
            y=[s[1] for s in school_sorted],
            labels={"x": "院校", "y": "人数"},
        )
        fig_school.update_layout(height=350)
        st.plotly_chart(fig_school, use_container_width=True)
    else:
        st.info("暂无院校数据")

with col_right3:
    st.subheader("⭐ 各岗位平均 AI 评分")

    # 计算每个岗位的平均分
    positions = get_positions()
    pos_avg_scores = []
    for p in positions:
        candidates_for_pos = get_candidates(position_id=p["id"])
        if candidates_for_pos:
            scores_for_pos = [c.get("ai_score", 0) or 0 for c in candidates_for_pos]
            avg_pos = sum(scores_for_pos) / len(scores_for_pos)
            pos_avg_scores.append({"岗位": p["title"], "平均评分": round(avg_pos, 1), "人数": len(scores_for_pos)})

    if pos_avg_scores:
        pos_avg_scores.sort(key=lambda x: x["平均评分"], reverse=True)
        df_avg = pd.DataFrame(pos_avg_scores)
        fig_avg = px.bar(
            df_avg, x="岗位", y="平均评分",
            text="平均评分",
            color="平均评分",
            color_continuous_scale="RdYlGn",
        )
        fig_avg.update_layout(height=350)
        st.plotly_chart(fig_avg, use_container_width=True)
    else:
        st.info("暂无评分数据")

st.markdown("---")

# ============================================================
# 第四行：试用期通过率（留存指标）
# ============================================================
st.subheader("🔄 试用期转正率")

stage_stats = kpi.get("stage_stats", {})
onboarded = stage_stats.get("已入职", 0)
passed_probation = stage_stats.get("试用期评估-通过", 0)
failed_probation = stage_stats.get("试用期评估-未通过", 0)

col_ret1, col_ret2, col_ret3 = st.columns(3)
with col_ret1:
    st.metric("👥 已入职", onboarded)
with col_ret2:
    st.metric("✅ 转正通过", passed_probation)
with col_ret3:
    if onboarded > 0:
        retention_rate = (passed_probation / onboarded) * 100
        st.metric("📊 转正率", f"{retention_rate:.1f}%")
    else:
        st.metric("📊 转正率", "N/A")

# 面试转化率
st.markdown("---")
st.subheader("📊 面试阶段转化率")

screening_passed = stage_stats.get("初筛-通过", 0)
interview_passed = stage_stats.get("初试-通过", 0) + stage_stats.get("复试-通过", 0)
offer_accepted = stage_stats.get("接Offer", 0)

col_int1, col_int2, col_int3, col_int4 = st.columns(4)
with col_int1:
    total = kpi.get("total_candidates", 0)
    if total > 0:
        st.metric("📋 简历合格率", f"{screening_passed / total * 100:.1f}%")
    else:
        st.metric("📋 简历合格率", "N/A")
with col_int2:
    if screening_passed > 0:
        st.metric("🎤 面试转化率", f"{interview_passed / screening_passed * 100:.1f}%")
    else:
        st.metric("🎤 面试转化率", "N/A")
with col_int3:
    interview_total = stage_stats.get("初试-通过", 0) + stage_stats.get("初试-淘汰", 0) + \
                      stage_stats.get("复试-通过", 0) + stage_stats.get("复试-淘汰", 0)
    if interview_total > 0:
        st.metric("📝 Offer 发放率", f"{stage_stats.get('发Offer', 0) / interview_total * 100:.1f}%")
    else:
        st.metric("📝 Offer 发放率", "N/A")
with col_int4:
    offers = stage_stats.get("发Offer", 0)
    if offers > 0:
        st.metric("🤝 Offer 接受率", f"{offer_accepted / offers * 100:.1f}%")
    else:
        st.metric("🤝 Offer 接受率", "N/A")

# ============================================================
# 数据导出
# ============================================================
st.markdown("---")
st.subheader("📥 数据导出")
with st.expander("导出候选人数据", expanded=False):
    candidates = get_candidates()
    if candidates:
        export_data = []
        for c in candidates:
            export_data.append({
                "姓名": c.get("name", ""),
                "性别": c.get("gender", ""),
                "手机号": c.get("phone", ""),
                "邮箱": c.get("email", ""),
                "学历": c.get("education", ""),
                "院校": c.get("school", ""),
                "专业": c.get("major", ""),
                "毕业年份": c.get("graduation_year", ""),
                "工作年限": c.get("work_years", ""),
                "当前公司": c.get("current_company", ""),
                "AI评分": c.get("ai_score", ""),
                "硬性匹配": "是" if c.get("hard_match") else "否",
                "核心优势": c.get("ai_strengths", ""),
                "潜在风险": c.get("ai_risks", ""),
                "状态": c.get("status", ""),
                "入库时间": c.get("created_at", ""),
            })
        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 下载 CSV",
            csv,
            f"ATS_人才库_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True,
        )
