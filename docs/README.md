# SOFIA Documentation

Comprehensive technical documentation for SOFIA (Sort of Functional Interactive Agent), a multimodal AI assistant platform with desktop automation, email/calendar integration, and flexible AI backend support.

## Documentation Overview

This documentation covers SOFIA's modular architecture, implementation details, and optimization strategies. Each guide provides in-depth technical information for developers and advanced users.

## Core System Documentation

### [Architecture](architecture.md)
Complete system design overview including the multi-interface architecture (web, desktop, MCP server), Brain Factory pattern for AI backend switching, tool system implementation, and security boundaries.

### [Desktop App](desktop-app.md)
Detailed guide to the PyQt6-based desktop interface featuring transparent overlay design, computer vision integration with OmniParser, and real-time UI automation capabilities.

## AI Backend Documentation

### [Ollama Brain](ollama-brain.md)
Local AI model integration guide covering Ollama setup, custom model creation, performance optimization for CUDA GPUs, and privacy-focused deployment strategies.

### [OpenAI Brain](openai-brain.md)
Cloud AI integration documentation including API configuration, model selection (GPT-4o, GPT-4, GPT-3.5), cost optimization, and advanced prompt engineering techniques.

## Performance & Optimization

### [Screenshot Optimization](screenshot-optimization.md)
Technical deep-dive into memory management, screenshot capture optimization, PIL/NumPy integration, and strategies for reducing latency in computer vision workflows.

## Quick Navigation

- **Getting Started**: See main [README](../README.md) for installation and basic usage
- **Configuration**: Check `config/` directory for YAML configuration files
- **Tools**: Review `config/tools.yaml` for available tool definitions
- **Examples**: Find usage examples in individual documentation files
