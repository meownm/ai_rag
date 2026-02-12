from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar


class AgentValidationError(ValueError):
    pass


class AgentExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class RewriteAgentInput:
    query: str
    execute: Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class RewriteAgentOutput:
    resolved_query_text: str
    clarification_needed: bool
    clarification_question: str | None
    confidence: float

    def __post_init__(self) -> None:
        if not self.resolved_query_text.strip():
            raise AgentValidationError("resolved_query_text must be non-empty")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise AgentValidationError("confidence must be in [0, 1]")


@dataclass(frozen=True)
class RetrievalAgentInput:
    query: str
    execute: Callable[[str], dict[str, Any]]


@dataclass(frozen=True)
class RetrievalAgentOutput:
    ranked_candidates: list[dict[str, Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.ranked_candidates, list):
            raise AgentValidationError("ranked_candidates must be a list")


@dataclass(frozen=True)
class AnalysisAgentInput:
    ranked_candidates: list[dict[str, Any]]
    execute: Callable[[list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class AnalysisAgentOutput:
    selected_candidates: list[dict[str, Any]]
    confidence: float

    def __post_init__(self) -> None:
        if not isinstance(self.selected_candidates, list):
            raise AgentValidationError("selected_candidates must be a list")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise AgentValidationError("confidence must be in [0, 1]")


@dataclass(frozen=True)
class AnswerAgentInput:
    query: str
    selected_candidates: list[dict[str, Any]]
    execute: Callable[[str, list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class AnswerAgentOutput:
    answer: str
    only_sources_verdict: str

    def __post_init__(self) -> None:
        if self.only_sources_verdict not in {"PASS", "FAIL"}:
            raise AgentValidationError("only_sources_verdict must be PASS or FAIL")


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    @abstractmethod
    def run(self, data: InputT) -> OutputT:
        raise NotImplementedError


class RewriteAgent(BaseAgent[RewriteAgentInput, RewriteAgentOutput]):
    def run(self, data: RewriteAgentInput) -> RewriteAgentOutput:
        payload = data.execute(data.query)
        return RewriteAgentOutput(
            resolved_query_text=str(payload["resolved_query_text"]),
            clarification_needed=bool(payload.get("clarification_needed", False)),
            clarification_question=payload.get("clarification_question"),
            confidence=float(payload.get("confidence", 1.0)),
        )


class RetrievalAgent(BaseAgent[RetrievalAgentInput, RetrievalAgentOutput]):
    def run(self, data: RetrievalAgentInput) -> RetrievalAgentOutput:
        payload = data.execute(data.query)
        return RetrievalAgentOutput(ranked_candidates=list(payload.get("ranked_candidates", [])))


class AnalysisAgent(BaseAgent[AnalysisAgentInput, AnalysisAgentOutput]):
    def run(self, data: AnalysisAgentInput) -> AnalysisAgentOutput:
        payload = data.execute(data.ranked_candidates)
        return AnalysisAgentOutput(
            selected_candidates=list(payload.get("selected_candidates", [])),
            confidence=float(payload.get("confidence", 0.0)),
        )


class AnswerAgent(BaseAgent[AnswerAgentInput, AnswerAgentOutput]):
    def run(self, data: AnswerAgentInput) -> AnswerAgentOutput:
        payload = data.execute(data.query, data.selected_candidates)
        return AnswerAgentOutput(answer=str(payload.get("answer", "")), only_sources_verdict=str(payload.get("only_sources_verdict", "PASS")))


@dataclass(frozen=True)
class AgentPipelineRequest:
    query: str
    rewrite_input: RewriteAgentInput
    retrieval_input: RetrievalAgentInput
    analysis_input_builder: Callable[[list[dict[str, Any]]], AnalysisAgentInput]
    answer_input_builder: Callable[[list[dict[str, Any]]], AnswerAgentInput]
    max_clarification_depth: int
    clarification_depth: int
    confidence_fallback_threshold: float
    debug: bool = False


@dataclass(frozen=True)
class AgentStageTrace:
    stage: str
    latency_ms: int
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentPipelineResult:
    answer: str
    only_sources_verdict: str
    selected_candidates: list[dict[str, Any]]
    confidence: float
    needs_clarification: bool
    clarification_question: str | None
    fallback_reason: str | None
    stage_traces: list[AgentStageTrace]


class AgentPipeline:
    def __init__(
        self,
        rewrite_agent: RewriteAgent | None = None,
        retrieval_agent: RetrievalAgent | None = None,
        analysis_agent: AnalysisAgent | None = None,
        answer_agent: AnswerAgent | None = None,
    ):
        self.rewrite_agent = rewrite_agent or RewriteAgent()
        self.retrieval_agent = retrieval_agent or RetrievalAgent()
        self.analysis_agent = analysis_agent or AnalysisAgent()
        self.answer_agent = answer_agent or AnswerAgent()

    def _run_stage(self, name: str, fn: Callable[[], Any], traces: list[AgentStageTrace], debug: bool) -> Any:
        t0 = time.perf_counter()
        try:
            output = fn()
        except Exception as exc:  # noqa: BLE001
            raise AgentExecutionError(f"{name} failed: {exc}") from exc
        latency_ms = int((time.perf_counter() - t0) * 1000)
        traces.append(
            AgentStageTrace(
                stage=name,
                latency_ms=latency_ms,
                output=output.__dict__ if debug and hasattr(output, "__dict__") else {},
            )
        )
        return output

    def run(self, request: AgentPipelineRequest) -> AgentPipelineResult:
        traces: list[AgentStageTrace] = []

        rewrite_output = self._run_stage(
            "rewrite_agent",
            lambda: self.rewrite_agent.run(request.rewrite_input),
            traces,
            request.debug,
        )

        if rewrite_output.clarification_needed and request.clarification_depth > request.max_clarification_depth:
            fallback_message = "Похоже, недостаточно информации для ответа... Попробуйте уточнить вопрос и сузить область поиска."
            return AgentPipelineResult(
                answer=fallback_message,
                only_sources_verdict="FAIL",
                selected_candidates=[],
                confidence=0.0,
                needs_clarification=False,
                clarification_question=None,
                fallback_reason="clarification_depth_exceeded",
                stage_traces=traces,
            )

        if rewrite_output.clarification_needed and request.clarification_depth <= request.max_clarification_depth:
            clarification_text = (rewrite_output.clarification_question or "Please clarify your request.").strip()
            return AgentPipelineResult(
                answer=clarification_text,
                only_sources_verdict="PASS",
                selected_candidates=[],
                confidence=rewrite_output.confidence,
                needs_clarification=True,
                clarification_question=clarification_text,
                fallback_reason=None,
                stage_traces=traces,
            )

        retrieval_input = RetrievalAgentInput(query=rewrite_output.resolved_query_text, execute=request.retrieval_input.execute)
        retrieval_output = self._run_stage(
            "retrieval_agent",
            lambda: self.retrieval_agent.run(retrieval_input),
            traces,
            request.debug,
        )

        analysis_input = request.analysis_input_builder(retrieval_output.ranked_candidates)
        analysis_output = self._run_stage(
            "analysis_agent",
            lambda: self.analysis_agent.run(analysis_input),
            traces,
            request.debug,
        )

        answer_input = request.answer_input_builder(analysis_output.selected_candidates)
        answer_output = self._run_stage(
            "answer_agent",
            lambda: self.answer_agent.run(answer_input),
            traces,
            request.debug,
        )

        if analysis_output.confidence < request.confidence_fallback_threshold:
            fallback_message = "Похоже, недостаточно информации для ответа... Попробуйте сузить область запроса."
            return AgentPipelineResult(
                answer=fallback_message,
                only_sources_verdict="FAIL",
                selected_candidates=analysis_output.selected_candidates,
                confidence=analysis_output.confidence,
                needs_clarification=False,
                clarification_question=None,
                fallback_reason="low_confidence",
                stage_traces=traces,
            )

        return AgentPipelineResult(
            answer=answer_output.answer,
            only_sources_verdict=answer_output.only_sources_verdict,
            selected_candidates=analysis_output.selected_candidates,
            confidence=analysis_output.confidence,
            needs_clarification=False,
            clarification_question=None,
            fallback_reason=None,
            stage_traces=traces,
        )
