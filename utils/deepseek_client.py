"""
DeepSeek V4 API 封装 - AI 简历解析与评估
"""
import json
import streamlit as st
from openai import OpenAI


def get_deepseek_client():
    """获取 DeepSeek 客户端实例（带缓存）。"""
    if "deepseek_client" in st.session_state:
        return st.session_state.deepseek_client

    try:
        api_key = st.secrets["deepseek"]["API_KEY"]
        base_url = st.secrets["deepseek"]["BASE_URL"]
        client = OpenAI(api_key=api_key, base_url=base_url)
        st.session_state.deepseek_client = client
        return client
    except Exception as e:
        st.error(f"❌ DeepSeek API 配置失败: {e}")
        return None


def get_model_name() -> str:
    """获取配置的模型名称。"""
    return st.secrets.get("deepseek", {}).get("MODEL", "deepseek-chat")


def parse_resume_with_ai(resume_text: str, jd_text: str = "",
                         hard_requirements: str = "") -> dict:
    """
    使用 DeepSeek V4 解析简历并评估匹配度。

    Args:
        resume_text: 简历原始文本
        jd_text: 岗位描述（可选，用于匹配分析）
        hard_requirements: 硬性要求（可选，用于红线检测）

    Returns:
        dict: 包含解析结果的字典
    """
    client = get_deepseek_client()
    if client is None:
        return _fallback_parse_result()

    model = get_model_name()

    system_prompt = """你是一位资深招聘专家，擅长简历解析和人才评估。
请严格按以下 JSON 格式返回分析结果（不要包含 markdown 代码块标记）：
{
  "name": "姓名",
  "gender": "性别（男/女）",
  "age": "年龄（数字，如29）",
  "phone": "手机号码",
  "email": "邮箱",
  "education": "最高学历（如：硕士、本科、博士、大专等）",
  "school": "毕业院校全称",
  "graduation_year": "毕业年份",
  "major": "专业",
  "work_years": "工作年限（数字）",
  "current_company": "当前/最近公司",
  "hard_match": true/false,
  "hard_match_detail": "硬性要求匹配说明",
  "ai_score": 0-100的整数,
  "strengths": "核心优势（要点形式，每点用|分隔）",
  "risks": "潜在风险（要点形式，每点用|分隔，如无则填'无明显风险'）",
  "summary": "一句话综合评价"
}

评分标准：
- 90-100: 非常匹配，强烈推荐
- 75-89: 较匹配，推荐面试
- 60-74: 基本匹配，可考虑
- 40-59: 部分匹配，需进一步评估
- 0-39: 不匹配

注意：
- 如果简历中某字段缺失，请填写"未知"
- 硬性匹配度需根据任职年限、学历门槛、技能要求等客观判断
- 风险包括：频繁跳槽（2年内换3份以上）、职业空档期超6个月、技能断层、学历不达标等"""

    user_prompt = f"""请分析以下简历：

{resume_text}

---
岗位描述（参考）：
{jd_text if jd_text else '无'}

硬性要求：
{hard_requirements if hard_requirements else '无'}

请输出 JSON 格式的分析结果。"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()

        # 清理可能的 markdown 代码块标记
        if content.startswith("```"):
            # 去除 ```json 或 ``` 开头
            lines = content.split("\n")
            content = "\n".join(lines[1:]) if len(lines) > 1 else content
        if content.endswith("```"):
            content = content[:-3].strip()

        result = json.loads(content)

        # 标准化字段
        return {
            "name": str(result.get("name", "未知")),
            "gender": str(result.get("gender", "未知")),
            "age": result.get("age", None),
            "phone": str(result.get("phone", "未知")),
            "email": str(result.get("email", "未知")),
            "education": str(result.get("education", "未知")),
            "school": str(result.get("school", "未知")),
            "graduation_year": str(result.get("graduation_year", "未知")),
            "major": str(result.get("major", "未知")),
            "work_years": str(result.get("work_years", "未知")),
            "current_company": str(result.get("current_company", "未知")),
            "hard_match": bool(result.get("hard_match", False)),
            "hard_match_detail": str(result.get("hard_match_detail", "")),
            "ai_score": int(result.get("ai_score", 0)),
            "ai_strengths": str(result.get("strengths", "")),
            "ai_risks": str(result.get("risks", "")),
            "ai_summary": str(result.get("summary", "")),
            "ai_raw_response": json.dumps(result, ensure_ascii=False),
        }

    except json.JSONDecodeError as e:
        st.warning(f"AI 返回格式解析失败，使用原始内容。错误: {e}")
        return _fallback_parse_result(resume_text[:500])
    except Exception as e:
        st.error(f"AI 分析失败: {e}")
        return _fallback_parse_result(resume_text[:500])


def _fallback_parse_result(partial_text: str = "") -> dict:
    """AI 解析失败时的兜底结果。"""
    return {
        "name": "未识别",
        "gender": "未知",
        "age": None,
        "phone": "未知",
        "email": "未知",
        "education": "未知",
        "school": "未知",
        "graduation_year": "未知",
        "major": "未知",
        "work_years": "未知",
        "current_company": "未知",
        "hard_match": False,
        "hard_match_detail": "AI 解析失败，请手动审核",
        "ai_score": 0,
        "ai_strengths": "",
        "ai_risks": "",
        "ai_summary": "AI 解析失败",
        "ai_raw_response": partial_text,
    }


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """从 PDF 文件中提取文本，支持多种解析引擎。"""
    text = ""
    # 方法1: PyPDF2
    try:
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        text = "\n".join(text_parts)
        if len(text.strip()) > 20:
            return text
    except Exception:
        pass

    # 方法2: pypdf (PyPDF2 的升级版，兼容性更好)
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        text = "\n".join(text_parts)
        if len(text.strip()) > 20:
            return text
    except Exception:
        pass

    return text if len(text.strip()) > 10 else ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 Word 文件中提取文本。"""
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n".join(text_parts)
    except Exception as e:
        st.error(f"Word 解析失败: {e}")
        return ""


def extract_text_from_file(file_bytes: bytes, file_name: str) -> str:
    """根据文件类型提取文本。"""
    file_name_lower = file_name.lower()
    if file_name_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif file_name_lower.endswith((".docx", ".doc")):
        return extract_text_from_docx(file_bytes)
    elif file_name_lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        st.error(f"不支持的文件格式: {file_name}")
        return ""
