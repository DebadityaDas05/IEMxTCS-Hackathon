"""
/api/ask — Question-answering endpoint.
"""

from fastapi import APIRouter, HTTPException, Request

from app.config import MAX_QUESTION_LENGTH
from app.models.schemas import QuestionRequest, AnswerResponse

router = APIRouter(tags=["Q&A"])


@router.post("/api/ask", response_model=AnswerResponse)
async def ask_question(request: Request, body: QuestionRequest):
    """
    Ask a question and get a grounded answer with source citations.
    
    If no relevant documents are found, returns an "I couldn't find this"
    response instead of fabricating an answer.
    """
    question = body.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please type a question to get started.",
        )

    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Question exceeds maximum allowed length of {MAX_QUESTION_LENGTH} characters.",
        )

    try:
        # Route through LangGraph Agent if enabled (Phase 5 Bonus)
        if body.use_agent and hasattr(request.app.state, "agent") and request.app.state.agent:
            agent_result = request.app.state.agent.run(question)
            return AnswerResponse(
                answer=agent_result["answer"],
                sources=agent_result["sources"],
                is_grounded=agent_result["is_grounded"],
                workflow_steps=agent_result.get("workflow_steps"),
                relevance_score=agent_result.get("relevance_score"),
            )

        # Fallback to standard RAG pipeline
        retriever = request.app.state.retriever
        response = retriever.answer_question(question)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your question: {str(e)}",
        )
