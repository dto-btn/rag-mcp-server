print("Hello, World")

# #!/usr/bin/env python
# """
# MCP Client for Business Requests Server

# This client connects to the Business Requests MCP server and uses OpenAI
# to interact with business requests data.
# """

# import asyncio
# from contextlib import AsyncExitStack
# import json
# import logging
# import os
# from typing import Any, Dict, List, Optional
# from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# # Load environment variables - for Azure OpenAI credentials
# from dotenv import load_dotenv
# # MCP Client SDK
# from mcp import ClientSession
# from mcp.client.streamable_http import streamablehttp_client
# from mcp.types import PromptMessage, TextContent
# # OpenAI SDK
# from openai import AsyncOpenAI, AzureOpenAI

# # Set up logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# # Load environment variables from .env file
# load_dotenv()

# token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
# azure_openai_uri        = os.getenv("AZURE_OPENAI_ENDPOINT")
# api_version             = os.getenv("AZURE_OPENAI_VERSION", "2024-05-01-preview")
# mcp_server_url         = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

# aoi = AzureOpenAI(
#     api_version=api_version,
#     azure_endpoint=str(azure_openai_uri),
#     azure_ad_token_provider=token_provider,
# )

# class MCPClient:
#     """MCP Client for interacting with an MCP Streamable HTTP server
#     code heavily based off:
#     https://github.com/invariantlabs-ai/mcp-streamable-http/blob/main/python-example/client/client.py
#     """

#     def __init__(self):
#         # Initialize session and client objects
#         self.session: Optional[ClientSession] = None
#         self.exit_stack = AsyncExitStack()
#         self.aoi = AzureOpenAI(
#                             api_version=api_version,
#                             azure_endpoint=str(azure_openai_uri),
#                             azure_ad_token_provider=token_provider,
#                         )

#     async def connect_to_streamable_http_server(
#         self, server_url: str, headers: Optional[dict] = None
#     ):
#         """Connect to an MCP server running with HTTP Streamable transport"""
#         self._streams_context = streamablehttp_client(  # pylint: disable=W0201
#             url=server_url,
#             headers=headers or {},
#         )
#         read_stream, write_stream, _ = await self._streams_context.__aenter__()  # pylint: disable=E1101
#         self._session_context = ClientSession(read_stream, write_stream)  # pylint: disable=W0201
#         self.session: ClientSession = await self._session_context.__aenter__()  # pylint: disable=C2801

#         await self.session.initialize()

#     async def process_query(self, query: str) -> str:
#         """Process a query using OpenAI and available tools"""
#         system_prompt = await self.session.get_prompt("business_request_prompt", {"language": "en"})
#         messages = []
#         for message in system_prompt.messages:
#             if message.content.type == "text":
#                 messages.append(
#                     {
#                         "role": message.role,
#                         "content": message.content.text,
#                     }
#                 )
#         messages.append({"role": "user", "content": query})

#         response = await self.session.list_tools()
#         #logger.debug(f"Available tools: {response.tools}")
#         # should be a fasterway to do this, such as using the tool.inputSchema directly, but couldn't do it quickly.
#         # mcp is also supported directly in OpenAI API now ... you can just pass the server directly.
#         available_tools = [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": tool.name,
#                     "description": tool.description,
#                     "parameters": {
#                         "type": "object",
#                         "properties": tool.inputSchema.get("properties", {}),
#                         "required": tool.inputSchema.get("required", []),
#                     },
#                 },
#             }
#             for tool in response.tools
#             if tool.name != "get_business_requests_context"
#         ]

#         # available_tools.append([
#         #     [{
#         #         "type": "mcp",
#         #         "server_label": "business_requests",
#         #         "server_url": mcp_server_url,
#         #     }]
#         # ])

#         additional_tools_required = True
#         final_text = []
#         while additional_tools_required:

#             response = self.aoi.chat.completions.create(
#                 model="gpt-4o",
#                 messages=messages,
#                 tools=available_tools,
#             )
#             message = response.choices[0].message
#             #logger.debug(f"Message Received: {message}")

#             if message.content:
#                 final_text.append(message.content)

#             if hasattr(message, "tool_calls") and message.tool_calls:
#                 #logger.debug(f"Tool calls: {message.tool_calls}")
#                 for tool_call in message.tool_calls:
#                     tool_name = tool_call.function.name
#                     tool_args = json.loads(tool_call.function.arguments)
#                     result = await self.session.call_tool(tool_name, tool_args)
#                     logger.debug(f"[Called tool {tool_name} with args {tool_args}]")
#                     final_text.append(f"[Called tool {tool_name} with args {tool_args}]")
#                     # Continue conversation with tool results
#                     if hasattr(message, "content") and message.content:
#                         messages.append({"role": "assistant", "content": message.content})
#                     messages.append({"role": "user", "content": result.content})
#             else:
#                 additional_tools_required = False #exit clause

#         return "\n".join(final_text)

#     async def chat_loop(self):
#         """Run an interactive chat loop"""
#         print("\nMCP Client Started!")
#         print("Type your queries or 'quit' to exit.")

#         while True:
#             try:
#                 query = input("\nQuery: ").strip()

#                 if query.lower() == "quit":
#                     break

#                 if query.lower() == "context":
#                     # Get context from the server
#                     result = await self.session.call_tool('get_business_requests_context', {})
#                     result = json.loads(result.content[0].text)
#                     if 'metadata' in result:
#                         print("\nContext: \n", result['metadata'])
#                     continue

#                 response = await self.process_query(query)
#                 print("\n" + response)

#             except Exception as e:
#                 print(f"\nError: {str(e)}")

#     async def cleanup(self):
#         """Properly clean up the session and streams"""
#         if self._session_context:
#             await self._session_context.__aexit__(None, None, None)
#         if self._streams_context:  # pylint: disable=W0125
#             await self._streams_context.__aexit__(None, None, None)  # pylint: disable=E1101

# async def main():
#     """Main function to demonstrate the client"""

#     client = MCPClient()

#     try:
#         await client.connect_to_streamable_http_server(mcp_server_url)
#         await client.chat_loop()
#     finally:
#         await client.cleanup()

# if __name__ == "__main__":
#     asyncio.run(main())