"""
简历上传与 AI 解析模块 - 批量上传简历并自动分析
"""
import streamlit as st
import pandas as pd

from utils.auth import check_global_password, ensure_user_session
from utils.supabase_client import (
    get_positions, create_candidate, link_candidate_to_position,
)
from utils.deepseek_client import (
    extract_text_from_file, parse_resume_with_ai,
)

check_global_password()
ensure_user_session()

st.title("🤖 简历上传与 AI 智能解析")
st.markdown("批量上传 PDF/Word 简历，AI 自动提取信息并评估匹配度。")

# ============================================================
# 选择目标岗位
# ============================================================
positions = get_positions("open")

if not positions:
    st.warning("⚠️ 暂无开放岗位，请先在 [职位管理](/职位管理) 中添加岗位。")
    st.stop()

position_options = {p["title"]: p for p in positions}
selected_title = st.selectbox(
    "🎯 选择目标岗位",
    list(position_options.keys()),
    help="简历将与此岗位进行匹配分析",
)
selected_position = position_options[selected_title]

# 显示岗位关键信息
with st.expander("📋 岗位要求预览", expanded=False):
    st.markdown(f"**岗位职责:** {selected_position.get('jd_description', '无')[:300]}")
    st.markdown(f"**任职要求:** {selected_position.get('requirements', '无')[:300]}")
    if selected_position.get("hard_requirements"):
        st.markdown(f"**🔴 硬性红线:** {selected_position['hard_requirements']}")
    if selected_position.get("bonus_requirements"):
        st.markdown(f"**🌟 加分项:** {selected_position['bonus_requirements']}")

# ============================================================
# 上传简历文件
# ============================================================
st.markdown("---")
st.subheader("📤 上传简历")

uploaded_files = st.file_uploader(
    "支持 PDF、Word (.docx)、TXT 格式，可批量上传",
    type=["pdf", "docx", "doc", "txt"],
    accept_multiple_files=True,
)

# ============================================================
# 简历解析与预览
# ============================================================
if uploaded_files:
    st.markdown("---")
    st.subheader(f"📋 待解析简历 ({len(uploaded_files)} 份)")

    # 缓存上传的文件内容，避免 rerun 后丢失
    if "uploaded_file_cache" not in st.session_state:
        st.session_state.uploaded_file_cache = {}

    # 把本次上传的文件缓存起来
    for f in uploaded_files:
        if f.name not in st.session_state.uploaded_file_cache:
            f.seek(0)
            st.session_state.uploaded_file_cache[f.name] = f.read()

    # 准备解析所有简历
    if "parsed_results" not in st.session_state:
        st.session_state.parsed_results = {}

    for uploaded_file in uploaded_files:
        file_key = uploaded_file.name

        # 跳过已解析的
        if file_key in st.session_state.parsed_results:
            continue

        # 从缓存取文件内容
        file_bytes = st.session_state.uploaded_file_cache.get(file_key)
        if file_bytes is None:
            st.error(f"❌ {uploaded_file.name} 文件内容丢失，请重新上传")
            continue

        with st.spinner(f"🤖 AI 正在分析: {uploaded_file.name} ..."):
            # 提取文本
            resume_text = extract_text_from_file(file_bytes, uploaded_file.name)

            if not resume_text or len(resume_text.strip()) < 10:
                st.error(f"❌ {uploaded_file.name} 文本提取失败（可能是扫描件或加密 PDF），请换用文字版简历")
                continue

            # AI 解析
            jd_text = selected_position.get("jd_description", "")
            hard_req = selected_position.get("hard_requirements", "")
            result = parse_resume_with_ai(resume_text, jd_text, hard_req)

            result["position_title"] = selected_title

            st.session_state.parsed_results[file_key] = result

    # 显示解析结果表格
    st.markdown("---")
    st.subheader("📊 AI 解析结果预览")

    parsed_list = list(st.session_state.parsed_results.values())

    if parsed_list:
        table_data = []
        for i, r in enumerate(parsed_list):
            score = r.get("ai_score", 0)
            score_emoji = "🟢" if score >= 75 else ("🟡" if score >= 60 else "🔴")
            table_data.append({
                "序号": i + 1,
                "姓名": r.get("name", "-"),
                "性别": r.get("gender", "-"),
                "年龄": r.get("age", "-"),
                "手机号": r.get("phone", "-"),
                "学历": r.get("education", "-"),
                "院校": r.get("school", "-"),
                "硬性匹配": "✅" if r.get("hard_match") else "❌",
                "AI 评分": f"{score_emoji} {score}",
                "核心优势": (r.get("ai_strengths", "") or "")[:80],
                "潜在风险": (r.get("ai_risks", "") or "")[:80],
            })

        df_preview = pd.DataFrame(table_data)
        st.dataframe(df_preview, use_container_width=True, hide_index=True, height=350)

        # 展开每份简历的详细信息
        for i, r in enumerate(parsed_list):
            with st.expander(f"📄 详情: {r.get('name', '未知')} —— AI 评分 {r.get('ai_score', 0)}", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**姓名:** {r.get('name', '-')}")
                    st.markdown(f"**性别:** {r.get('gender', '-')}")
                    st.markdown(f"**年龄:** {r.get('age', '-')}")
                    st.markdown(f"**手机:** {r.get('phone', '-')}")
                    st.markdown(f"**邮箱:** {r.get('email', '-')}")
                    st.markdown(f"**当前公司:** {r.get('current_company', '-')}")
                with col_b:
                    st.markdown(f"**学历:** {r.get('education', '-')}")
                    st.markdown(f"**院校:** {r.get('school', '-')}")
                    st.markdown(f"**专业:** {r.get('major', '-')}")
                    st.markdown(f"**毕业年份:** {r.get('graduation_year', '-')}")
                    st.markdown(f"**工作年限:** {r.get('work_years', '-')}年")

                st.markdown(f"**🔴 硬性匹配:** {'✅ 通过' if r.get('hard_match') else '❌ 未通过'} —— {r.get('hard_match_detail', '')}")
                st.markdown(f"**⭐ AI 综合评分:** {r.get('ai_score', 0)} / 100")
                st.markdown(f"**💪 核心优势:** {r.get('ai_strengths', '-')}")
                st.markdown(f"**⚠️ 潜在风险:** {r.get('ai_risks', '-')}")
                st.markdown(f"**📝 综合评语:** {r.get('ai_summary', '-')}")

                # 允许手动调整评分
                manual_score = st.slider(
                    "手动调整评分",
                    0, 100, int(r.get("ai_score", 0)),
                    key=f"manual_score_{i}",
                )
                if manual_score != r.get("ai_score"):
                    st.session_state.parsed_results[list(st.session_state.parsed_results.keys())[i]]["ai_score"] = manual_score

        # ============================================================
        # 保存到数据库
        # ============================================================
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("💾 全部保存到人才库", type="primary", use_container_width=True):
                success_count = 0
                fail_count = 0
                pos_id = selected_position["id"]

                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, (file_key, result) in enumerate(st.session_state.parsed_results.items()):
                    status_text.text(f"正在保存: {result.get('name', file_key)} ...")
                    progress_bar.progress((idx + 1) / len(st.session_state.parsed_results))

                    candidate_data = {
                        "name": result.get("name", "未知"),
                        "gender": result.get("gender", "未知"),
                        "age": result.get("age", None),
                        "phone": result.get("phone", "未知"),
                        "email": result.get("email", "未知"),
                        "education": result.get("education", "未知"),
                        "school": result.get("school", "未知"),
                        "graduation_year": result.get("graduation_year", "未知"),
                        "major": result.get("major", "未知"),
                        "work_years": result.get("work_years", "未知"),
                        "current_company": result.get("current_company", "未知"),
                        "ai_score": result.get("ai_score", 0),
                        "ai_strengths": result.get("ai_strengths", ""),
                        "ai_risks": result.get("ai_risks", ""),
                        "hard_match": result.get("hard_match", False),
                        "hard_match_detail": result.get("hard_match_detail", ""),
                        "ai_raw_response": result.get("ai_raw_response", ""),
                        "status": "new",
                        "source": "upload",
                    }

                    candidate_id = create_candidate(candidate_data)
                    if candidate_id:
                        link_candidate_to_position(candidate_id, pos_id)
                        success_count += 1
                    else:
                        fail_count += 1

                progress_bar.progress(1.0)
                status_text.text("保存完成")

                if success_count > 0:
                    st.success(f"✅ 成功保存 {success_count} 份简历到人才库")
                    # 清除解析缓存
                    st.session_state.parsed_results = {}
                if fail_count > 0:
                    st.error(f"❌ {fail_count} 份简历保存失败")

        with col_btn2:
            if st.button("🗑️ 清除解析结果", use_container_width=True):
                st.session_state.parsed_results = {}
                st.rerun()
