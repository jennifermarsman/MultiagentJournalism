import asyncio
import datetime
import os
from collections.abc import Mapping, Sequence
from dotenv import load_dotenv
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential


def _normalize_query_values(value):
    """Return a flat list of query strings from arbitrary nested values."""
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        normalized = []
        for item in value:
            normalized.extend(_normalize_query_values(item))
        return normalized
    return [str(value).strip()]


def _collect_search_queries(payload):
    """Search recursively for fields that contain search query information."""
    if payload is None:
        return []
    if isinstance(payload, str):
        lowered = payload.lower()
        if "query" in lowered:
            return [payload.strip()]
        return []
    if isinstance(payload, Mapping):
        collected = []
        for key, value in payload.items():
            key_lower = str(key).lower()
            if key_lower in {"query"}:
                collected.extend(_normalize_query_values(value))
            else:
                collected.extend(_collect_search_queries(value))
        return collected
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        collected = []
        for item in payload:
            collected.extend(_collect_search_queries(item))
        return collected
    if hasattr(payload, "__dict__"):
        return _collect_search_queries(vars(payload))
    return []


def _extract_search_queries_from_update(update):
    """Deduplicate and preserve the order of any search queries found."""
    raw_queries = _collect_search_queries(update)
    deduped = []
    seen = set()
    for query in raw_queries:
        normalized = query.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


async def main() -> None:
    # Create Azure OpenAI chat client for all agents
    # Try to use Azure CLI credentials, fall back to API key
    credential = DefaultAzureCredential()

    nonreasoning_client = AzureOpenAIResponsesClient(
        endpoint=azure_oai_endpoint,
        deployment_name=azure_nonreasoning_deployment,
        api_version=azure_api_version,
        credential=credential
    )

    reasoning_client = AzureOpenAIResponsesClient(
        endpoint=azure_oai_endpoint,
        deployment_name=azure_reasoning_deployment,
        api_version=azure_api_version,
        credential=credential
    )

    # TODO: error handling if API key is missing or invalid, or other env variables not set
    
    # Initialize console for rich output
    console = Console()
    
    # Define agents using Microsoft Agent Framework
    
    # Web Search Researcher - provides additional information
    web_search_agent = nonreasoning_client.create_agent(
        name="web_search_agent",
        instructions="You are a research agent. You always use the web search tool to find relevant, current information that could enhance the article. Do not write the article, but rather provide specific facts, statistics, quotes from experts, or recent developments that the writer should incorporate.  Include citations with full links for all information found.",
        tools=[{"type": "web_search_preview"}], 
    )
    
    # Writer - creates first draft
    writer_agent = nonreasoning_client.create_agent(
        name="writer_agent", 
        instructions="You are a high-quality journalist who writes compelling articles. Based on the article requirements provided and related research, write a complete first draft. Write an actual article with an introduction, body paragraphs, and conclusion - NOT just bullet points or an outline. Make it engaging and well-structured."
    )
    
    # Editor - provides editorial feedback
    editor_agent = reasoning_client.create_agent(
        name="editor_agent", 
        instructions="You are an expert editor. Review the article draft and the research provided. Give specific editorial feedback on structure, clarity, flow, and content. Suggest improvements and identify any gaps that need to be filled."
    )
    
    # Writer Revision - incorporates feedback
    writer_revision_agent = reasoning_client.create_agent(
        name="writer_revision_agent", 
        instructions="You are the writer making revisions. Review your original draft, the research findings, and the editor's feedback. Write an improved, complete version of the article that incorporates the research and addresses the editorial suggestions. Output the full revised article."
    )

    # Verifier - fact-checks the article
    verifier_agent = nonreasoning_client.create_agent(
        name="verifier_agent", 
        tools=[{"type": "web_search_preview"}],
        instructions="You are a fact-checker. Verify the key claims and facts in the revised article using web search. Explicitly state whether you APPROVE or REJECT the article based on accuracy. If you find inaccuracies, list them specifically."
    )
    
    # Final Reviewer - makes final determination
    final_review_agent = nonreasoning_client.create_agent(
        name="final_review_agent", 
        instructions="You are the final reviewer. Check if the article meets all requirements: (1) it's a complete, well-written article (not bullet points), (2) it has been fact-checked and approved by the verifier, (3) it addresses the original requirements. If all conditions are met, declare the article COMPLETE and ready for publication. Otherwise, state what's missing."
    )
    
    # Get user input for article requirements
    console.print("\n[bold cyan]Starting Article Creation Workflow[/bold cyan]\n")
    text = Text()
    text.append("User Input: ", style="bold magenta")
    text.append("\nWhat article would you like me to write? Please describe the topic, key questions, and any starting points.")
    console.print(text)
    
    # Human in the loop for initial requirements
    console.print("\nHuman Journalist:", style="bold magenta")
    user_requirements = input(">> ")
    # Include today's date for context - in the news world, recency matters
    user_requirements += " Today's date is " + str(datetime.date.today())
    
    conversation_history = []
    
    # Agent order for round-robin conversation
    agents = [
        ("Web Search Researcher", web_search_agent),
        ("Writer", writer_agent),
        ("Editor", editor_agent),
        ("Writer Revision", writer_revision_agent),
        ("Verifier", verifier_agent),
        ("Final Reviewer", final_review_agent)
    ]
    
    for agent_name, agent in agents:
        # Prepare the input for this agent
        if not conversation_history:
            # First agent gets the original task
            input_message = user_requirements
        else:
            # Subsequent agents get the full conversation history
            # Plus a prompt to continue the discussion
            input_message = f"{user_requirements}\n\nPrevious discussion:\n"
            for msg in conversation_history:
                input_message += f"{msg}\n"
            input_message += f"\n{agent_name}, please complete your task:"
        
        # Print agent header
        text = Text()
        text.append(f"\n🤖 {agent_name}:", style="bold magenta")
        console.print(text)
    
        # Stream the agent's response
        full_response = ""
        async for update in agent.run_stream(input_message):
            search_queries = _extract_search_queries_from_update(update)
            if search_queries:
                query_text = ", ".join(search_queries)
                console.print(Text(f"\n🔍 Search query: {query_text}\n", style="bold yellow"))

            # Print streaming output
            if update.text:
                print(update.text, end="", flush=True)
                full_response += update.text
        
        print()  # New line after streaming completes
        
        # Add to conversation history
        conversation_history.append(f"{agent_name}: {full_response.strip()}")

    console.print("\n[bold green]Article creation process completed![/bold green]")


# Load env variables
load_dotenv()
azure_oai_endpoint = os.getenv("AZURE_OPENAI_API_ENDPOINT")
azure_oai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_reasoning_deployment = os.getenv("AZURE_OPENAI_REASONING_DEPLOYMENT_NAME")
azure_nonreasoning_deployment = os.getenv("AZURE_OPENAI_NONREASONING_DEPLOYMENT_NAME")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# Run
asyncio.run(main())
