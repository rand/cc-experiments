"""Streaming Chat Server with DSPy and FastAPI."""

import dspy
import asyncio
from typing import List, Dict, AsyncIterator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel


# ============================================================================
# STREAMING CHAT
# ============================================================================

class StreamingChat(dspy.Module):
    """Chat with streaming responses."""

    def __init__(self, max_history: int = 10):
        super().__init__()
        self.generate = dspy.ChainOfThought("history, message -> response")
        self.history: List[Dict[str, str]] = []
        self.max_history = max_history

    def forward(self, message: str) -> dspy.Prediction:
        """Generate response (non-streaming)."""
        history_text = self._format_history()

        result = self.generate(
            history=history_text,
            message=message
        )

        # Update history
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result.response})

        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]

        return result

    async def stream(self, message: str) -> AsyncIterator[str]:
        """Generate response with streaming.

        Yields:
            Token chunks
        """
        history_text = self._format_history()

        # For demo: simulate streaming by yielding word by word
        result = self.generate(
            history=history_text,
            message=message
        )

        response = result.response

        # Update history
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": response})

        # Simulate streaming
        words = response.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.05)  # Simulate network delay

    def _format_history(self) -> str:
        """Format conversation history."""
        if not self.history:
            return "No previous conversation."

        lines = []
        for turn in self.history[-self.max_history * 2:]:
            lines.append(f"{turn['role']}: {turn['content']}")
        return "\n".join(lines)

    def clear_history(self):
        """Clear conversation history."""
        self.history = []


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="Streaming Chat")

# Global chat instance
chat: StreamingChat = None


@app.on_event("startup")
async def startup():
    """Initialize chat on startup."""
    global chat

    # Configure DSPy
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    chat = StreamingChat(max_history=10)

    print("✓ Chat initialized")


# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

class MessageRequest(BaseModel):
    """Message request."""
    message: str


@app.post("/chat")
async def chat_endpoint(request: MessageRequest):
    """Non-streaming chat endpoint."""
    result = chat(message=request.message)

    return {
        "response": result.response,
        "reasoning": result.reasoning if hasattr(result, "reasoning") else None
    }


@app.post("/chat/stream")
async def stream_endpoint(request: MessageRequest):
    """Streaming chat endpoint."""

    async def generate():
        async for chunk in chat.stream(request.message):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )


@app.post("/clear")
async def clear_history():
    """Clear conversation history."""
    chat.clear_history()
    return {"status": "cleared"}


# ============================================================================
# WEBSOCKET
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            # Stream response
            async for chunk in chat.stream(message):
                await websocket.send_json({
                    "type": "token",
                    "content": chunk
                })

            # Send completion signal
            await websocket.send_json({
                "type": "done"
            })

    except WebSocketDisconnect:
        print("Client disconnected")


# ============================================================================
# WEB UI
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve web UI."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Streaming Chat</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; }
        #chat { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin-bottom: 10px; }
        .message { margin: 10px 0; }
        .user { color: blue; }
        .assistant { color: green; }
        #input { width: 80%; padding: 10px; }
        #send { padding: 10px 20px; }
    </style>
</head>
<body>
    <h1>Streaming Chat</h1>
    <div id="chat"></div>
    <input type="text" id="input" placeholder="Type a message..." />
    <button id="send">Send</button>
    <button id="clear">Clear</button>

    <script>
        const ws = new WebSocket('ws://localhost:8000/ws');
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('send');
        const clearBtn = document.getElementById('clear');

        let currentMessage = null;

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'token') {
                if (!currentMessage) {
                    currentMessage = document.createElement('div');
                    currentMessage.className = 'message assistant';
                    currentMessage.innerHTML = '<strong>Assistant:</strong> ';
                    chat.appendChild(currentMessage);
                }
                currentMessage.innerHTML += data.content;
                chat.scrollTop = chat.scrollHeight;
            } else if (data.type === 'done') {
                currentMessage = null;
            }
        };

        function sendMessage() {
            const message = input.value.trim();
            if (!message) return;

            // Display user message
            const userDiv = document.createElement('div');
            userDiv.className = 'message user';
            userDiv.innerHTML = '<strong>You:</strong> ' + message;
            chat.appendChild(userDiv);

            // Send via WebSocket
            ws.send(JSON.stringify({ message: message }));

            input.value = '';
            chat.scrollTop = chat.scrollHeight;
        }

        sendBtn.onclick = sendMessage;
        input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
        clearBtn.onclick = () => {
            fetch('/clear', { method: 'POST' });
            chat.innerHTML = '';
        };
    </script>
</body>
</html>
"""


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("Starting Streaming Chat Server...")
    print("Open http://localhost:8000 in your browser")

    uvicorn.run(app, host="0.0.0.0", port=8000)
