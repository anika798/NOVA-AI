# NOVA (Neural Online Virtual Assistant) - Enterprise AI Platform

NOVA is a production-quality, modular, privacy-focused AI Assistant and Operating System platform. Built on Clean Architecture and Solid design principles, NOVA provides a local-first AI engine, session management, resilient memory persistence, controlled permission management, path security, and telemetry monitoring.

---

## 🏗️ Architecture Diagram

```mermaid
graph TD
    App[main.py / CLI Interface] --> Bootstrap[ApplicationBootstrap]
    Bootstrap --> Config[ConfigManager]
    Bootstrap --> Logger[LoggerManager]
    Bootstrap --> Services[ServiceManager]

    subgraph Service Registry
        Services --> FS[FileSystemService]
        Services --> Mem[MemoryService]
        Services --> OllamaCheck[OllamaService]
        Services --> AIEngine[AIEngineService]
        Services --> Perms[PermissionManager]
    end

    subgraph AI Engine Subsystem
        AIEngine --> Client[OllamaClient REST]
        AIEngine --> Prompt[PromptBuilder]
        AIEngine --> Identity[SystemPromptManager]
        AIEngine --> Session[SessionManager]
        AIEngine --> Processor[ResponseProcessor]
        AIEngine --> Status[AIStatusManager]
    end

    subgraph Security & Permissions
        Perms --> PathCheck[Path Traversal & Boundary Safety]
        Perms --> Policy[SAFE / CONFIRM / BLOCKED Policy]
    end

    subgraph Persistent Storage
        Mem --> MemoryFiles[data/memory/*.json]
        Session --> SessionFiles[data/memory/sessions/*.json]
        Logger --> LogFiles[data/logs/nova.log]
    end

    Client -->|HTTP localhost:11434| Ollama[Local Ollama Server / qwen2.5:14b]
```

---

## 🌟 Progress & Feature Summary

### Day 1 Summary (Infrastructure Foundation)
- **Bootstrap Pipeline**: Sequential initialization sequence with robust exception boundaries.
- **Folder Auto-Creation**: Automatically creates `config`, `data`, `data/memory`, and `data/logs`.
- **Config & Logging System**: JSON-based settings with default fallback merging, ANSI colored console logs, and rotating file logs.
- **Memory Infrastructure**: JSON memory files (`short_term.json`, `long_term.json`, `user_profile.json`, `system_state.json`) with auto-repair capability.
- **Service Manager**: Dynamic service registry facilitating dependency injection and health lifecycle.

### Day 2 Summary (AI Engine & Brain Integration)
- **Dedicated AI Engine (`AIEngineService`)**: Central gateway managing all LLM communication, registered into `ServiceManager`.
- **Ollama REST Client (`OllamaClient`)**: Low-level client for Ollama API (`/api/chat`, `/api/generate`, `/api/tags`, `/api/version`), featuring retries, timeouts, and connection failure handling.
- **Prompt Builder (`PromptBuilder`)**: Merges System Prompt + Conversation History + User Input + Memory Context into clean Ollama payloads.
- **Permanent Identity (`SystemPromptManager`)**: Defines NOVA's personality, senior coding engineer role, local-first privacy rules, permission philosophy, and custom user instruction merging.
- **Multi-Session Management (`SessionManager`)**: Supports multiple independent named sessions (e.g. "Python Project", "Interview", "Default") saved to disk under `data/memory/sessions/*.json`.
- **Response Processor (`ResponseProcessor`)**: Normalizes whitespace, extracts fenced code blocks, and calculates word/character telemetry.
- **AI Status Telemetry (`AIStatusManager`)**: Tracks response latency, request counts, error counts, loaded model, and active session state.
- **Interactive CLI & Command Mode**: Provides `--chat` interactive session loop and `--prompt "<text>"` execution modes.

### Day 3 Summary (Tool Architecture, Security & Automated Testing)
- **Permission Manager (`PermissionManager`)**: Action risk classifier (`SAFE`, `CONFIRM`, `BLOCKED`) preventing execution of dangerous commands (e.g., `rm -rf /`, `format`, destructive system commands).
- **Security & Path Protection**: Enforces workspace boundary validation (`is_safe_path`), blocking path traversal attacks (`../secret.txt`) and unauthorized external absolute paths.
- **Enhanced Memory Operations**: Dynamic store creation, retrieval, listing, deletion, and auto-discovery of custom memory stores.
- **Automated Test Suite**: Built-in test suite covering AI engine, memory, permission manager, security path protection, and multi-session subsystems.

---

## 📂 Project Structure

```
Nova-ai/
├── config/
│   └── settings.json           # Global configuration file
├── data/
│   ├── logs/
│   │   └── nova.log            # Rotating application log
│   └── memory/
│       ├── long_term.json      # Persistent knowledge & facts
│       ├── short_term.json     # Active session buffer
│       ├── system_state.json   # Boot & execution telemetry
│       ├── user_profile.json   # User identity & custom directives
│       └── sessions/           # Multi-session chat history storage
│           ├── default.json
│           └── ...
├── nova/
│   ├── __init__.py
│   ├── __main__.py             # Module entry point
│   ├── banner.py               # Visual startup banner renderer
│   ├── bootstrap.py            # Application bootstrap orchestrator
│   ├── ai/                     # Day 2 AI Subsystem
│   │   ├── __init__.py
│   │   ├── ai_status_manager.py # Performance telemetry
│   │   ├── conversation_manager.py # In-memory message history
│   │   ├── engine.py           # AIEngineService orchestrator
│   │   ├── exceptions.py       # AI specific exceptions
│   │   ├── ollama_client.py    # Low-level REST client
│   │   ├── prompt_builder.py   # Prompt assembly
│   │   ├── response_processor.py # Output cleanup & code extraction
│   │   ├── session_manager.py  # Multi-session persistence
│   │   └── system_prompt.py    # NOVA identity & directives
│   ├── core/
│   │   ├── __init__.py
│   │   ├── base_service.py     # BaseService contract & ServiceStatus
│   │   ├── config.py           # ConfigManager
│   │   ├── logger.py           # LoggerManager & ColoredConsoleFormatter
│   │   └── service_manager.py  # Service registry & health monitoring
│   ├── permissions/            # Day 3 Permissions & Security
│   │   ├── __init__.py
│   │   └── permission_manager.py # Permission classification & path safety
│   ├── services/
│   │   ├── __init__.py
│   │   ├── filesystem_service.py # Workspace directory verification & path safety
│   │   ├── memory_service.py   # Memory store management & dynamic discovery
│   │   └── ollama_service.py   # Ollama daemon probe
│   └── utils/
│       ├── __init__.py
│       └── constants.py         # System constants & exception hierarchy
├── tests/                      # Automated Unit & Integration Tests
│   ├── __init__.py
│   ├── test_ai_engine.py       # AI Engine initialization & mock LLM tests
│   ├── test_memory.py          # Memory CRUD, persistence, & recovery tests
│   ├── test_permissions.py     # Permission classification & rule safety tests
│   ├── test_security.py        # Path traversal & boundary security tests
│   └── test_sessions.py       # Multi-session creation, loading, & isolation tests
├── .gitignore                  # Git ignore rules
├── main.py                     # Root CLI entry point
├── requirements.txt            # Project dependencies
└── README.md                   # System documentation
```

---

## 🛠️ Technology Stack

- **Language**: Python 3.9+ (Clean Architecture, Type Hints, Dataclasses)
- **LLM Runtime**: Local [Ollama](https://ollama.com/) Server (`http://localhost:11434`)
- **Default LLM Model**: `qwen2.5:14b`
- **Network Client**: Standard Library (`urllib.request`) with zero-dependency execution
- **Storage**: Structured Local JSON (`data/memory/`, `data/memory/sessions/`)
- **Testing**: Built-in `unittest` Framework (Zero External Test Dependencies)

---

## 🚀 How to Run NOVA

### 1. Single Prompt Execution
```bash
python main.py --prompt "Explain the architectural pattern used in NOVA."
```

### 2. Interactive Conversation CLI
```bash
python main.py --chat
```

#### Interactive Commands in Chat Mode:
- `/session` - List all session threads
- `/session create <name>` - Create and switch to a new session (e.g. `/session create Python Project`)
- `/session switch <id>` - Switch to an existing session
- `/status` - Display AI Engine latency and telemetry
- `/clear` - Clear history for active session
- `/exit` - Exit chat mode

---

## 🧪 Running Automated Tests

NOVA includes a comprehensive automated test suite built with Python's built-in `unittest` framework.

To discover and execute all unit and integration tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### What the Test Suite Verifies:
1. **`test_ai_engine.py`**: Verifies `AIEngineService` initialization, prompt handling, empty prompt guards, and graceful handling of Ollama daemon errors via mocks without making external API calls.
2. **`test_memory.py`**: Verifies memory creation, retrieval, listing, deletion, disk persistence, and automatic repair of corrupted memory JSON files.
3. **`test_permissions.py`**: Verifies that `PermissionManager` accepts safe commands (`git status`, `ls`), requests confirmation for state-changing commands, and strictly blocks dangerous system commands (e.g., `rm -rf /`, `format C:`) **without ever executing them**.
4. **`test_security.py`**: Verifies path traversal protection (`../secret.txt`) and prevents access to files outside the permitted workspace directory.
5. **`test_sessions.py`**: Verifies independent multi-session creation, switching, disk persistence, and conversation isolation.

---

## 🗺️ Next Day Roadmap (Day 4 & Beyond)

- **Day 4 (Autonomous Code & Execution Context)**: File reading/writing tool execution, workspace context injection into Prompt Builder, sandbox execution boundaries.
- **Day 5 (Voice & Multi-Modal Processing)**: Voice recognition, wake word, speech synthesis.
- **Day 6 (Multi-Agent & Task Systems)**: Autonomous sub-agent orchestration and background task runner.

---

## 📌 Version & Changelog

- **v1.0.0-day1**: Initial foundation (Config, Logger, ServiceManager, FileSystem, Memory, Ollama Probe).
- **v1.0.0-day2**: Added AI Engine (`AIEngineService`), OllamaClient, PromptBuilder, SystemPromptManager, SessionManager, ConversationManager, ResponseProcessor, and interactive CLI.
- **v1.0.0-day3**: Added `PermissionManager`, path security validation (`is_safe_path`), memory store listing/deletion/recovery, and automated test suite (`tests/`).
