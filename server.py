import os
import logging
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from mcp.server.fastmcp.prompts.base import Message

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@dataclass
class RAGContext:
    """Context for RAG operations"""
    files: list[bytearray]

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[BRContext]:
    """Manage application lifecycle with type-safe context"""

    # Yield the context to the server
    try:
        yield RAGContext(files=[])
    finally:
        # Cleanup resources on shutdown
        pass  # Add cleanup code here if needed

# Create an MCP server with lifespan management
mcp = FastMCP("RAGorama",
              version="1.0.0",
              lifespan=server_lifespan,
              dependencies=["pydantic", "pandas"], # Add any dependencies your server needs
              stateless_http=True, # fix from https://github.com/jlowin/fastmcp/issues/435#issuecomment-2888502679
            #   auth_server_provider=MSAuthProvider(),
            #   auth=AuthSettings(
            #       issuer_url="https://auth.example.com",
            #       client_id=os.getenv("CLIENT_ID"),
            #       client_secret=os.getenv("CLIENT_SECRET"),
            #       redirect_uri=os.getenv("REDIRECT_URI"),
            #       scopes=["openid", "profile", "email"],)
            )

@mcp.tool(description="This uploads a file to the server for RAG operations. Accepts bytes and will convert it to a vector database")
async def vectorize_file(file: bytearray, ctx: Context) -> str:
    """Returns the BR database query

    Args:
        query: The business request query parameters

    Returns:
        The generated SQL query string
    """
    # VECTORIZE THE FILE HERE ....
    # STORE IT IN THE CONTEXT FOR LATER USE
    # PROFIT ???
    return "File successfully vectorized and stored in context. *clicks tongue*"
    #await ctx.info(f"Validated query: {query}")
    

@mcp.tool(description="""Search context files for a specific term.""")
def search_files(term: str, ctx: Context) -> str:
    """Searches the context files for a specific term"""
    if not ctx.request_context.lifespan_context.files:
        return "No files available in context."
    
    # Simulate searching through files
    results = [f"Found '{term}' in file {i}" for i, file in enumerate(ctx.request_context.lifespan_context.files) if term in file.decode('utf-8', errors='ignore')]
    
    if not results:
        return f"No occurrences of '{term}' found in context files."
    
    return "\n".join(results)

@mcp.prompt(description="""This is the system prompt that will be used to generate the business request query""")
def business_request_prompt(language: str) -> list[Message]:
    """Prompt for business request"""
    return [{
        "role": "user",
        "content": "blahblah fix me Monarch" if language == "fr" else "blahblah fix me Monarch"
    }]

if __name__ == "__main__":
    mcp.run(transport="streamable-http") # supported since 2.3.0