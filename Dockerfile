FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python3", "src/servers/mcp_github_tool_server.py"]

EXPOSE 8000
