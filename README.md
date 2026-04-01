# Self.AI

Self.AI is a comprehensive, self-hosted AI platform that integrates multiple open-source AI components into a unified Docker-based infrastructure. Designed for researchers, developers, and organizations seeking a complete AI development and deployment environment.

## Features

- **🤖 LLM Inference & Training**: GPU-accelerated inference with llama.cpp, Ollama, and LoRA/QLoRA fine-tuning via DeepSpeed (through llamolotl container)
- **💬 Web Interface**: Full-featured UI with chat, RAG, web search, image generation, and voice/video calls
- **📊 Evaluation Frameworks**: Extensive benchmarks for general LLMs and code generation models
- **🔍 RAG Support**: Vector search with Qdrant, PostgreSQL pgvector, and local document processing
- **🎤 Speech Recognition**: Local ASR with Wyoming-Whisper
- **🔐 Multi-tenant**: Role-based access control, OAuth/LDAP authentication
- **🌐 Multi-language**: i18n support and multilingual model capabilities

## Architecture

```
opt/self.ai/
├── docker-compose.yml          # Main orchestration
├── self.UI/                    # WebUI (SvelteKit + FastAPI)
├── self.llamolotl/             # LLM inference + training (llama.cpp + DeepSpeed)
├── self.lm-evaluation-harness/ # General LLM benchmarks
├── self.bigcode-eval/          # Code generation evaluation
├── self.qdrant/                # Vector database
├── postgres/                   # PostgreSQL + pgvector
├── valkey/                     # Cache layer
├── traefik/                    # Reverse proxy
└── wyoming-whisper/            # Speech recognition
```

## Quick Start

```bash
docker-compose up -d
```

## Technologies

- **Frontend**: SvelteKit, Svelte, TypeScript, Vite
- **Backend**: FastAPI, Python, SQLAlchemy, Pydantic
- **AI/ML**: HuggingFace, Transformers, PEFT, TRL, DeepSpeed, Flash Attention
- **Inference**: llama.cpp, Ollama, vLLM, OpenAI API
- **Databases**: PostgreSQL, pgvector, Qdrant, Valkey
- **Containerization**: Docker, Docker Compose

## License

- **Self.AI UI**: MIT (forked from Open-WebUI)
- **LM Evaluation Harness**: MIT
- **BigCode Evaluation**: Apache 2.0
- **DeepSpeed**: Apache 2.0
