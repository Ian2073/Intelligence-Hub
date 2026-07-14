from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class ResearchAgent(Protocol):
    def investigate(self, **kwargs):
        ...

    def reflect(self, **kwargs):
        ...

    def propose_insights(self, **kwargs):
        ...


class RunnableAgent(Protocol):
    metadata: "AgentMetadata"

    def run(self, **kwargs):
        ...


@dataclass(frozen=True)
class AgentMetadata:
    agent_id: str
    domain: str
    ingestor_types: tuple[str, ...]
    workflow: str
    synthesis_policy: str
    publishers: tuple[str, ...]


class FunctionAgent:
    def __init__(self, metadata: AgentMetadata, runner: Callable[..., object]) -> None:
        self.metadata = metadata
        self._runner = runner

    def run(self, **kwargs):
        return self._runner(**kwargs)


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, RunnableAgent] = {}

    def register(self, agent: RunnableAgent) -> None:
        agent_id = agent.metadata.agent_id.strip()
        if not agent_id:
            raise ValueError("agent_id must not be empty.")
        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> RunnableAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"Unknown agent: {agent_id}") from exc

    def list_agents(self) -> tuple[AgentMetadata, ...]:
        return tuple(agent.metadata for agent in self._agents.values())


def build_default_registry(*, daily_runner: Callable[..., object]) -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(
        FunctionAgent(
            AgentMetadata(
                agent_id="ai_intelligence",
                domain="AI Intelligence",
                ingestor_types=("github", "papers", "domain_rss"),
                workflow="daily_intelligence",
                synthesis_policy="hybrid",
                publishers=("obsidian", "notion", "telegram"),
            ),
            daily_runner,
        )
    )
    return registry
