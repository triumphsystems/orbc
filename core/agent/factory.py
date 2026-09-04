import logging
from core.config.settings import get_settings

logger = logging.getLogger("core.agent.factory")


def get_orchestrator():
    """
    Returns the active agent orchestrator based on settings.
    Defaults to StrandsAgentOrchestrator for model-driven orchestration on the strands-sdk branch.
    Falls back to legacy AgentOrchestrator if ORCHESTRATOR_ENGINE=legacy.
    """
    settings = get_settings()
    engine = getattr(settings, "orchestrator_engine", "strands").lower()

    if engine == "strands":
        try:
            from core.agent.strands_orchestrator import StrandsAgentOrchestrator

            return StrandsAgentOrchestrator()
        except Exception as e:
            logger.warning("Failed initializing StrandsAgentOrchestrator: %s. Falling back to legacy.", e)

    from core.agent.orchestrator import AgentOrchestrator

    return AgentOrchestrator()
