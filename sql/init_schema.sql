-- ========================================
-- ATS 系统数据库初始化脚本
-- 请在 Supabase SQL Editor 中执行此脚本
-- ========================================

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'hr' CHECK (role IN ('admin', 'hr')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 职位表
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    department TEXT DEFAULT '',
    jd_description TEXT DEFAULT '',
    requirements TEXT DEFAULT '',
    hard_requirements TEXT DEFAULT '',
    bonus_requirements TEXT DEFAULT '',
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed', 'draft')),
    headcount INT DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 候选人表
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    education TEXT DEFAULT '',
    school TEXT DEFAULT '',
    graduation_year TEXT DEFAULT '',
    major TEXT DEFAULT '',
    work_years TEXT DEFAULT '',
    current_company TEXT DEFAULT '',
    raw_resume_text TEXT DEFAULT '',
    resume_file_path TEXT DEFAULT '',
    resume_file_name TEXT DEFAULT '',
    ai_score FLOAT DEFAULT 0,
    ai_strengths TEXT DEFAULT '',
    ai_risks TEXT DEFAULT '',
    hard_match BOOLEAN DEFAULT false,
    hard_match_detail TEXT DEFAULT '',
    ai_raw_response TEXT DEFAULT '',
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'active', 'archived', 'hired', 'public_pool')),
    source TEXT DEFAULT 'upload',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 候选人-职位关联表 (多对多)
CREATE TABLE IF NOT EXISTS candidate_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(candidate_id, position_id)
);

-- 5. 招聘流程阶段记录 (状态机历史)
CREATE TABLE IF NOT EXISTS candidate_pipeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN (
        '初筛-通过', '初筛-淘汰',
        '联系反馈',
        '部门筛选-通过', '部门筛选-淘汰',
        '初试-通过', '初试-淘汰',
        '复试-通过', '复试-淘汰',
        '发Offer', '接Offer', '拒Offer',
        '已入职',
        '试用期评估-通过', '试用期评估-未通过',
        '公海池'
    )),
    notes TEXT DEFAULT '',
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_current BOOLEAN DEFAULT true
);

-- 为 candidate_pipeline 添加部分索引，确保每个 candidate+position 只有一条 current
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_current_stage
ON candidate_pipeline (candidate_id, position_id)
WHERE is_current = true;

-- 6. 沟通记录表
CREATE TABLE IF NOT EXISTS communication_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    content TEXT DEFAULT '',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. 创建索引
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_school ON candidates(school);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_cp_candidate ON candidate_positions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_cp_position ON candidate_positions(position_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_candidate ON candidate_pipeline(candidate_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON candidate_pipeline(stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_current ON candidate_pipeline(is_current);

-- 8. 启用 RLS (Row Level Security) - 可选，根据安全需求开启
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- 9. 创建 Supabase Storage Bucket (需要在 Supabase Dashboard 手动创建)
-- Bucket 名称: resumes
-- 权限: 公开读取 (或按需配置)

-- 10. 插入默认管理员用户 (密码: admin123, bcrypt hash)
-- 首次部署后请立即修改密码!
INSERT INTO users (email, username, password_hash, role)
VALUES ('admin@ats.com', '管理员', '$2b$12$LJ3m4ys3GZfnYMz8kVsKaOTSxGHLJfXJru5WoR.KqD7IFNa2KyvGq', 'admin')
ON CONFLICT (email) DO NOTHING;
