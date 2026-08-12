"""
NOVA Ollama Low-Level REST Client with Streaming Support
"""
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Generator, List, Optional, Tuple

from nova.utils.constants import OllamaClientError

logger = logging.getLogger("NOVA.OllamaClient")


class OllamaClient:
    """
    Dedicated HTTP REST client for communicating exclusively with local Ollama daemon.
    Encapsulates network request handling, retries, model queries, streaming, and API response parsing.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 11434,
        timeout: int = 300,
        max_retries: int = 2,
        keep_alive: str = "30m",
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.keep_alive = keep_alive
        self.base_url = f"http://{self.host}:{self.port}"

    def check_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Tests reachability of local Ollama REST server.
        Returns tuple of (is_connected, version_string).
        """
        url = f"{self.base_url}/api/version"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOVA-AIEngine/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return True, data.get("version", "unknown")
        except Exception as e:
            logger.debug(f"Ollama health probe failed: {e}")
        return False, None

    def list_models(self) -> List[str]:
        """
        Fetches list of model names currently pulled and available in local Ollama instance.
        """
        url = f"{self.base_url}/api/tags"
        models: List[str] = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOVA-AIEngine/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("models", []):
                        if "name" in m:
                            models.append(m["name"])
        except Exception as e:
            logger.error(f"Failed to query Ollama tags API: {e}")
        return models

    def is_model_available(self, model_name: str) -> bool:
        """
        Checks if specified model is installed locally.
        """
        installed = self.list_models()
        target = model_name.lower()
        for m in installed:
            m_lower = m.lower()
            if m_lower == target or target.split(":")[0] in m_lower and target.split(":")[-1] in m_lower:
                return True
        return False

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Sends structured message thread to Ollama /api/chat endpoint (non-streaming).
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
        }
        if options:
            payload["options"] = options

        return self._post_with_retry(url, payload)

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Generator[str, None, Dict[str, Any]]:
        """
        Streams token chunks in real-time from Ollama /api/chat endpoint.
        Yields string token chunks as they arrive from LLM.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "keep_alive": self.keep_alive,
        }
        if options:
            payload["options"] = options

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "NOVA-AIEngine/1.0"},
            method="POST",
        )

        full_content: List[str] = []
        last_meta: Dict[str, Any] = {}

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for line in resp:
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str:
                            try:
                                chunk_json = json.loads(line_str)
                                msg = chunk_json.get("message", {})
                                token = msg.get("content", "")
                                if token:
                                    full_content.append(token)
                                    yield token

                                if chunk_json.get("done", False):
                                    last_meta = chunk_json
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Streaming error from Ollama: {e}")
            raise OllamaClientError(f"Ollama streaming connection failed: {e}") from e

        # Final return metadata
        return {"content": "".join(full_content), "metadata": last_meta}

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends single completion prompt to Ollama /api/generate endpoint.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        return self._post_with_retry(url, payload)

    def _post_with_retry(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes HTTP POST request with automatic retry logic on network glitches.
        """
        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(1, self.max_retries + 2):
            try:
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "NOVA-AIEngine/1.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8")
                        return json.loads(raw_body)
                    else:
                        raise OllamaClientError(f"HTTP {resp.status} received from Ollama API: {url}")

            except (urllib.error.URLError, TimeoutError, SocketError, ConnectionResetError) as e:
                logger.warning(f"Ollama request attempt {attempt} failed: {e}")
                if attempt > self.max_retries:
                    raise OllamaClientError(
                        f"Failed to connect to Ollama server at {self.base_url} after {attempt} attempts: {e}"
                    ) from e
                time.sleep(1.0 * attempt)
            except json.JSONDecodeError as e:
                raise OllamaClientError(f"Invalid JSON returned from Ollama server: {e}") from e


from socket import error as SocketError
