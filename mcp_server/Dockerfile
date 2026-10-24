# LivingOps MCP Access Gateway. Build from the repository root:
#   docker build -f mcp_server/Dockerfile .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MCP_HOST=0.0.0.0 MCP_PORT=8765
WORKDIR /app

COPY mcp_server/requirements.txt ./mcp_server/requirements.txt
RUN pip install --no-cache-dir -r mcp_server/requirements.txt
COPY mcp_server ./mcp_server

EXPOSE 8765
CMD ["python", "-m", "mcp_server"]
