from langchain.tools import tool
from langchain_core.tools import BaseTool

from app.core.logging import get_logger
from app.services.documentation.service import DocumentationService

logger = get_logger(__name__)


def build_documentation_tools(service: DocumentationService) -> tuple[BaseTool]:
    """Create the official NRP documentation tool available to the agent."""

    @tool
    def search_nrp_documentation(query: str) -> str:
        """Search official NRP documentation for a question or topic.

        Use this for NRP policies, services, tutorials, and usage guidance. Base
        answers only on the returned excerpts and cite the returned source URL.
        """
        logger.info(
            "documentation_tool_invoked", tool="search_nrp_documentation", query=query
        )
        return (
            "["
            + ",".join(page.model_dump_json() for page in service.search(query))
            + "]"
        )

    return (search_nrp_documentation,)
