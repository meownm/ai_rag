import pytest

from app.services.agent_pipeline import (
    AgentExecutionError,
    AgentPipeline,
    AgentPipelineRequest,
    AnalysisAgentInput,
    AnswerAgentInput,
    RetrievalAgentInput,
    RewriteAgentInput,
    RewriteAgentOutput,
)


def _request(*, clarification_needed=False, clarification_depth=0, confidence=0.9, debug=False):
    return AgentPipelineRequest(
        query="vacation policy",
        rewrite_input=RewriteAgentInput(
            query="vacation policy",
            execute=lambda _q: {
                "resolved_query_text": "vacation policy resolved",
                "clarification_needed": clarification_needed,
                "clarification_question": "Уточните подразделение?" if clarification_needed else None,
                "confidence": 0.4 if clarification_needed else 0.9,
            },
        ),
        retrieval_input=RetrievalAgentInput(
            query="vacation policy resolved",
            execute=lambda _q: {"ranked_candidates": [{"chunk_id": "c1", "final_score": confidence}]},
        ),
        analysis_input_builder=lambda ranked: AnalysisAgentInput(
            ranked_candidates=ranked,
            execute=lambda _r: {"selected_candidates": ranked[:1], "confidence": confidence},
        ),
        answer_input_builder=lambda selected: AnswerAgentInput(
            query="vacation policy",
            selected_candidates=selected,
            execute=lambda _q, _selected: {"answer": "Готовый ответ", "only_sources_verdict": "PASS"},
        ),
        max_clarification_depth=2,
        clarification_depth=clarification_depth,
        confidence_fallback_threshold=0.5,
        debug=debug,
    )


def test_pipeline_happy_path_runs_all_agents():
    result = AgentPipeline().run(_request(confidence=0.91))

    assert result.answer == "Готовый ответ"
    assert result.only_sources_verdict == "PASS"
    assert result.fallback_reason is None
    assert [t.stage for t in result.stage_traces] == ["rewrite_agent", "retrieval_agent", "analysis_agent", "answer_agent"]


def test_pipeline_returns_clarification_when_depth_within_limit():
    result = AgentPipeline().run(_request(clarification_needed=True, clarification_depth=2))

    assert result.needs_clarification is True
    assert "Уточните" in result.answer
    assert result.only_sources_verdict == "PASS"
    assert [t.stage for t in result.stage_traces] == ["rewrite_agent"]


def test_pipeline_returns_controlled_fallback_when_clarification_depth_exceeded():
    result = AgentPipeline().run(_request(clarification_needed=True, clarification_depth=3))

    assert result.needs_clarification is False
    assert result.only_sources_verdict == "FAIL"
    assert result.fallback_reason == "clarification_depth_exceeded"


def test_pipeline_routes_low_confidence_to_controlled_fallback():
    result = AgentPipeline().run(_request(confidence=0.2))

    assert result.only_sources_verdict == "FAIL"
    assert result.fallback_reason == "low_confidence"
    assert "недостаточно информации" in result.answer


def test_pipeline_stage_error_is_explicit():
    request = _request()
    request = AgentPipelineRequest(
        query=request.query,
        rewrite_input=RewriteAgentInput(query="vacation policy", execute=lambda _q: {"resolved_query_text": "x", "clarification_needed": False, "clarification_question": None, "confidence": 0.9}),
        retrieval_input=RetrievalAgentInput(query="x", execute=lambda _q: (_ for _ in ()).throw(RuntimeError("db unavailable"))),
        analysis_input_builder=request.analysis_input_builder,
        answer_input_builder=request.answer_input_builder,
        max_clarification_depth=request.max_clarification_depth,
        clarification_depth=request.clarification_depth,
        confidence_fallback_threshold=request.confidence_fallback_threshold,
        debug=request.debug,
    )

    with pytest.raises(AgentExecutionError) as exc:
        AgentPipeline().run(request)
    assert "retrieval_agent failed" in str(exc.value)


def test_rewrite_output_validation_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        RewriteAgentOutput(
            resolved_query_text="q",
            clarification_needed=False,
            clarification_question=None,
            confidence=1.5,
        )


def test_pipeline_debug_trace_contains_outputs():
    result = AgentPipeline().run(_request(confidence=0.91, debug=True))

    assert result.stage_traces[0].output["resolved_query_text"] == "vacation policy resolved"
