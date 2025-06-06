"""
面试智能体 API 服务
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from pathlib import Path
import uuid

from interview_agent.core import (
    ResumeParser, 
    QuestionGenerator,
    InterviewConductor,
    QuestionType
)
from config.settings import settings

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered Interview Agent API"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
resume_parser = ResumeParser()
question_generator = QuestionGenerator()
interview_conductor = InterviewConductor()


# 请求/响应模型
class UploadResumeResponse(BaseModel):
    profile_id: str
    name: str
    skills: List[str]
    experience_years: int


class GenerateQuestionsRequest(BaseModel):
    profile_id: str
    duration_minutes: int = 30
    focus_areas: Optional[List[str]] = None


class GenerateQuestionsResponse(BaseModel):
    session_id: str
    questions: List[dict]


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str


class SubmitAnswerResponse(BaseModel):
    interviewer_response: str
    is_completed: bool
    next_question: Optional[dict] = None


class InterviewReportResponse(BaseModel):
    session_id: str
    candidate_name: str
    duration_minutes: float
    overall_score: float
    strengths: List[str]
    improvements: List[str]
    recommendation: str


# 临时存储（实际应用中应使用数据库）
profiles_store = {}


@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "Interview Agent API",
        "version": settings.app_version,
        "endpoints": {
            "upload_resume": "/api/resume/upload",
            "generate_questions": "/api/questions/generate",
            "start_interview": "/api/interview/start",
            "submit_answer": "/api/interview/answer",
            "get_report": "/api/interview/report"
        }
    }


@app.post("/api/resume/upload", response_model=UploadResumeResponse)
async def upload_resume(file: UploadFile = File(...)):
    """上传并解析简历"""
    # 验证文件类型
    if not file.filename.endswith(('.md', '.pdf', '.docx')):
        raise HTTPException(400, "不支持的文件格式")
    
    # 保存文件
    upload_path = Path(settings.upload_dir) / file.filename
    upload_path.parent.mkdir(exist_ok=True)
    
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 解析简历
    try:
        profile = resume_parser.parse(upload_path)
        profile_id = str(uuid.uuid4())
        profiles_store[profile_id] = profile
        
        return UploadResumeResponse(
            profile_id=profile_id,
            name=profile.name,
            skills=profile.skills[:10],  # 返回前10个技能
            experience_years=profile.experience_years
        )
    except Exception as e:
        raise HTTPException(500, f"简历解析失败: {str(e)}")


@app.post("/api/questions/generate", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    """生成面试题目"""
    profile = profiles_store.get(request.profile_id)
    if not profile:
        raise HTTPException(404, "候选人信息未找到")
    
    # 生成题目
    questions = question_generator.generate_interview_plan(
        profile=profile,
        duration_minutes=request.duration_minutes,
        focus_areas=request.focus_areas
    )
    
    # 创建面试会话
    session = interview_conductor.create_session(profile, questions)
    
    # 转换题目为字典格式
    questions_dict = [
        {
            "id": q.id,
            "type": q.type.value,
            "question": q.question,
            "difficulty": q.difficulty,
            "time_minutes": q.time_minutes
        }
        for q in questions
    ]
    
    return GenerateQuestionsResponse(
        session_id=session.id,
        questions=questions_dict
    )


@app.post("/api/interview/start")
async def start_interview(session_id: str):
    """开始面试"""
    try:
        greeting = interview_conductor.start_interview(session_id)
        return {
            "session_id": session_id,
            "interviewer_message": greeting,
            "status": "started"
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/interview/answer", response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """提交回答"""
    try:
        response, is_completed = interview_conductor.process_candidate_response(
            request.session_id,
            request.answer
        )
        
        # 获取下一题信息
        session = interview_conductor.sessions.get(request.session_id)
        next_question = None
        if session and not is_completed:
            current_q = session.get_current_question()
            if current_q:
                next_question = {
                    "id": current_q.id,
                    "type": current_q.type.value,
                    "question": current_q.question
                }
        
        return SubmitAnswerResponse(
            interviewer_response=response,
            is_completed=is_completed,
            next_question=next_question
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/interview/report/{session_id}", response_model=InterviewReportResponse)
async def get_interview_report(session_id: str):
    """获取面试报告"""
    try:
        report = interview_conductor.get_session_report(session_id)
        
        return InterviewReportResponse(
            session_id=report["session_id"],
            candidate_name=report["candidate"]["name"],
            duration_minutes=report["duration_minutes"] or 0,
            overall_score=report["overall_score"],
            strengths=report["strengths"],
            improvements=report["areas_for_improvement"],
            recommendation=report["recommendation"]
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/interview/sessions")
async def list_sessions():
    """列出所有面试会话"""
    sessions = []
    for session_id, session in interview_conductor.sessions.items():
        sessions.append({
            "session_id": session_id,
            "candidate_name": session.candidate_profile.name,
            "state": session.state.value,
            "questions_count": len(session.questions),
            "current_question": session.current_question_index + 1
        })
    return {"sessions": sessions}


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    ) 