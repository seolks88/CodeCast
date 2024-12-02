# CodeCast

A tool that provides real-time monitoring of code changes and AI-based analysis.

## Key Features

- Real-time detection of file changes in specified directories
- Generation and storage of file change diffs
- Code analysis using LLM
- Feedback on code quality, performance, and security
- Analysis result history management


## Main Components

### FileChangeHandler
- File change detection and information collection
- Change verification based on SHA-256 hash
- Asynchronous file processing

### DatabaseManager
- SQLite-based change storage
- File change history management
- Analysis result storage

### CodeAnalyzer
- LLM-based code analysis
- Code quality, performance, and security analysis
- Improvement suggestion generation

## License

MIT License