"""
Supabase 客户端封装 - 数据库 CRUD 操作
"""
import streamlit as st
from datetime import datetime
from typing import Optional


def get_supabase_client():
    """获取 Supabase 客户端实例（带缓存）。"""
    if "supabase_client" in st.session_state:
        return st.session_state.supabase_client

    try:
        from supabase import create_client
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        client = create_client(url, key)
        st.session_state.supabase_client = client
        return client
    except Exception as e:
        st.error(f"❌ Supabase 连接失败: {e}")
        return None


# ============================================================
# 职位 CRUD
# ============================================================

def get_positions(status_filter: Optional[str] = None) -> list:
    """获取职位列表。"""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    try:
        query = supabase.table("positions").select("*").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        result = query.execute()
        return result.data
    except Exception as e:
        st.error(f"获取职位列表失败: {e}")
        return []


def create_position(title: str, jd_description: str, requirements: str,
                    hard_requirements: str, bonus_requirements: str = "",
                    department: str = "", headcount: int = 1,
                    created_by: Optional[str] = None) -> bool:
    """创建新职位。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        data = {
            "title": title,
            "jd_description": jd_description,
            "requirements": requirements,
            "hard_requirements": hard_requirements,
            "bonus_requirements": bonus_requirements,
            "department": department,
            "headcount": headcount,
            "status": "open",
            "created_by": created_by,
        }
        supabase.table("positions").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"创建职位失败: {e}")
        return False


def update_position(position_id: str, **kwargs) -> bool:
    """更新职位信息。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        supabase.table("positions").update(kwargs).eq("id", position_id).execute()
        return True
    except Exception as e:
        st.error(f"更新职位失败: {e}")
        return False


def delete_position(position_id: str) -> bool:
    """删除职位。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        supabase.table("positions").delete().eq("id", position_id).execute()
        return True
    except Exception as e:
        st.error(f"删除职位失败: {e}")
        return False


# ============================================================
# 候选人 CRUD
# ============================================================

def get_candidates(status_filter: Optional[str] = None,
                   position_id: Optional[str] = None,
                   search_text: Optional[str] = None) -> list:
    """获取候选人列表，支持多条件筛选。"""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    try:
        query = supabase.table("candidates").select("*").order("created_at", desc=True)

        if status_filter:
            query = query.eq("status", status_filter)
        if search_text:
            query = query.or_(
                f"name.ilike.%{search_text}%,phone.ilike.%{search_text}%,"
                f"email.ilike.%{search_text}%,school.ilike.%{search_text}%"
            )

        result = query.execute()
        candidates = result.data

        # 如果指定了职位，过滤出投递该职位的候选人
        if position_id and candidates:
            cp_result = supabase.table("candidate_positions").select("candidate_id") \
                .eq("position_id", position_id).execute()
            cp_ids = {r["candidate_id"] for r in cp_result.data}
            candidates = [c for c in candidates if c["id"] in cp_ids]

        return candidates
    except Exception as e:
        st.error(f"获取候选人列表失败: {e}")
        return []


def create_candidate(candidate_data: dict) -> Optional[str]:
    """创建候选人记录，返回新记录的 ID。"""
    supabase = get_supabase_client()
    if supabase is None:
        return None
    try:
        result = supabase.table("candidates").insert(candidate_data).execute()
        if result.data:
            return result.data[0]["id"]
        return None
    except Exception as e:
        st.error(f"创建候选人失败: {e}")
        return None


def update_candidate(candidate_id: str, **kwargs) -> bool:
    """更新候选人信息。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        supabase.table("candidates").update(kwargs).eq("id", candidate_id).execute()
        return True
    except Exception as e:
        st.error(f"更新候选人失败: {e}")
        return False


def delete_candidate(candidate_id: str) -> bool:
    """删除候选人。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        supabase.table("candidates").delete().eq("id", candidate_id).execute()
        return True
    except Exception as e:
        st.error(f"删除候选人失败: {e}")
        return False


# ============================================================
# 候选人-职位关联
# ============================================================

def link_candidate_to_position(candidate_id: str, position_id: str) -> bool:
    """将候选人与职位关联。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        supabase.table("candidate_positions").insert({
            "candidate_id": candidate_id,
            "position_id": position_id,
        }).execute()
        return True
    except Exception:
        # 可能已经存在关联，忽略
        return True


def get_candidate_positions(candidate_id: str) -> list:
    """获取候选人关联的职位列表。"""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    try:
        result = supabase.table("candidate_positions").select(
            "position_id, positions(*)").eq("candidate_id", candidate_id).execute()
        return [r["positions"] for r in result.data if r.get("positions")]
    except Exception:
        return []


def get_position_candidates_count(position_id: str) -> int:
    """获取某个职位的候选人数量。"""
    supabase = get_supabase_client()
    if supabase is None:
        return 0
    try:
        result = supabase.table("candidate_positions").select("id", count="exact") \
            .eq("position_id", position_id).execute()
        return result.count if result.count else 0
    except Exception:
        return 0


# ============================================================
# 招聘流程 Pipeline
# ============================================================

def get_pipeline_stages() -> list:
    """返回所有预定义的招聘阶段。"""
    return [
        "初筛-通过", "初筛-淘汰",
        "联系反馈",
        "部门筛选-通过", "部门筛选-淘汰",
        "初试-通过", "初试-淘汰",
        "复试-通过", "复试-淘汰",
        "发Offer", "接Offer", "拒Offer",
        "已入职",
        "试用期评估-通过", "试用期评估-未通过",
        "公海池",
    ]


def get_current_stage(candidate_id: str, position_id: str) -> Optional[dict]:
    """获取候选人当前所处的招聘阶段。"""
    supabase = get_supabase_client()
    if supabase is None:
        return None
    try:
        result = supabase.table("candidate_pipeline").select("*") \
            .eq("candidate_id", candidate_id) \
            .eq("position_id", position_id) \
            .eq("is_current", True) \
            .execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def advance_stage(candidate_id: str, position_id: str,
                  stage: str, notes: str = "",
                  updated_by: Optional[str] = None) -> bool:
    """
    推进候选人到新的招聘阶段。
    先将旧阶段标记为 is_current=false，再插入新阶段。
    """
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        # 将旧的 current 阶段标记为非当前
        supabase.table("candidate_pipeline").update({"is_current": False}) \
            .eq("candidate_id", candidate_id) \
            .eq("position_id", position_id) \
            .eq("is_current", True) \
            .execute()

        # 插入新阶段
        supabase.table("candidate_pipeline").insert({
            "candidate_id": candidate_id,
            "position_id": position_id,
            "stage": stage,
            "notes": notes,
            "updated_by": updated_by,
            "is_current": True,
        }).execute()
        return True
    except Exception as e:
        st.error(f"更新阶段失败: {e}")
        return False


def get_pipeline_history(candidate_id: str, position_id: str) -> list:
    """获取候选人的流程历史记录。"""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    try:
        result = supabase.table("candidate_pipeline").select("*") \
            .eq("candidate_id", candidate_id) \
            .eq("position_id", position_id) \
            .order("created_at", desc=True) \
            .execute()
        return result.data
    except Exception:
        return []


def get_pipeline_stats() -> dict:
    """获取各阶段的候选人数量统计（用于漏斗图）。"""
    supabase = get_supabase_client()
    if supabase is None:
        return {}
    try:
        result = supabase.table("candidate_pipeline").select("stage") \
            .eq("is_current", True).execute()
        stats = {}
        for r in result.data:
            stage = r["stage"]
            stats[stage] = stats.get(stage, 0) + 1
        return stats
    except Exception:
        return {}


# ============================================================
# 沟通记录
# ============================================================

def add_communication_note(candidate_id: str, position_id: str,
                           content: str, created_by: Optional[str] = None) -> bool:
    """添加沟通记录。"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    try:
        supabase.table("communication_notes").insert({
            "candidate_id": candidate_id,
            "position_id": position_id,
            "content": content,
            "created_by": created_by,
        }).execute()
        return True
    except Exception as e:
        st.error(f"添加沟通记录失败: {e}")
        return False


def get_communication_notes(candidate_id: str, position_id: str) -> list:
    """获取沟通记录列表。"""
    supabase = get_supabase_client()
    if supabase is None:
        return []
    try:
        result = supabase.table("communication_notes").select("*") \
            .eq("candidate_id", candidate_id) \
            .eq("position_id", position_id) \
            .order("created_at", desc=True) \
            .execute()
        return result.data
    except Exception:
        return []


# ============================================================
# KPI 统计辅助函数
# ============================================================

def get_kpi_data() -> dict:
    """获取招聘效能核心指标数据。"""
    supabase = get_supabase_client()
    if supabase is None:
        return {}

    try:
        # 总候选人
        total_result = supabase.table("candidates").select("id", count="exact").execute()
        total_candidates = total_result.count or 0

        # AI 评分分布
        score_result = supabase.table("candidates").select("ai_score").not_.is_("ai_score", "null").execute()
        valid_scores = [r["ai_score"] for r in score_result.data if r["ai_score"] is not None]

        # 学历分布
        edu_result = supabase.table("candidates").select("education").execute()
        edu_stats = {}
        for r in edu_result.data:
            edu = r.get("education", "未知") or "未知"
            edu_stats[edu] = edu_stats.get(edu, 0) + 1

        # 院校分布
        school_result = supabase.table("candidates").select("school").execute()
        school_stats = {}
        for r in school_result.data:
            s = r.get("school", "未知") or "未知"
            school_stats[s] = school_stats.get(s, 0) + 1

        # Pipeline 各阶段统计
        stage_stats = {}
        try:
            stage_result = supabase.table("candidate_pipeline").select("stage") \
                .eq("is_current", True).execute()
            for r in stage_result.data:
                stage = r["stage"]
                stage_stats[stage] = stage_stats.get(stage, 0) + 1
        except Exception:
            pass

        # 各岗位候选人数量
        pos_result = supabase.table("positions").select("id, title").eq("status", "open").execute()
        position_stats = {}
        for p in pos_result.data:
            cnt = get_position_candidates_count(p["id"])
            position_stats[p["title"]] = cnt

        return {
            "total_candidates": total_candidates,
            "avg_ai_score": sum(valid_scores) / len(valid_scores) if valid_scores else 0,
            "edu_stats": edu_stats,
            "school_stats": school_stats,
            "stage_stats": stage_stats,
            "position_stats": position_stats,
        }
    except Exception as e:
        st.error(f"获取 KPI 数据失败: {e}")
        return {}
