# self.ai
An entirely self hosted AI stack, built to work with NVIDIA GPU's. 

An entirely self-hosted AI stack centered around [LibreChat](https://github.com/danny-avila/LibreChat) as the front-end. The goal is to provide a complete server that offers both a user-friendly web interface and an OpenAI-compatible API endpoint.

## Features

- **LLM Management**: Load and run models locally with [Ollama](https://github.com/jmorganca/ollama).
  Future support is planned for additional backends such as `llama.cpp`, `mistral.rs`, and more.
- **Web Scraping**: Gather information from the web using tools like Playwright, Firecrawl, and SearxNG.
- **Image Generation**: Generate images through [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
  and access it directly from LibreChat via an extension.

The stack is intended for self-hosted deployments and aims to work well on systems equipped with NVIDIA GPUs.