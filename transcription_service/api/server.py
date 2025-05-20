import threading

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .processor import VideoProcessor
from .routes import setup_routes
from ..transcription.translator import Translator
from ..utils.network import is_port_available


class TranscriptionServer:
    """FastAPI server for streaming video transcription and translation."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Video Transcription Streaming API")
        self.processor = VideoProcessor()
        self.translator = Translator()
        self.server_thread = None
        self.setup_middleware()
        setup_routes(self.app, self.processor, self.translator)

    def setup_middleware(self):
        """Configure CORS middleware for the FastAPI application."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def start(self):
        """Start the FastAPI server."""
        if not self.server_thread or not self.server_thread.is_alive():
            while not is_port_available(self.port):
                print(f"Port {self.port} in use, trying next...")
                self.port += 1
            self.server_thread = threading.Thread(target=self.run_api, daemon=True)
            self.server_thread.start()
            print(f"Server started at http://{self.host}:{self.port}")
        else:
            print("Server already running.")

    def run_api(self):
        """Run the Uvicorn server."""
        uvicorn.run(self.app, host=self.host, port=self.port)

    def stop(self):
        """Stop the FastAPI server."""
        if self.server_thread and self.server_thread.is_alive():
            print("Stopping transcription server...")
            self.server_thread = None
            print("Transcription server stopped.")
