# Context7 Architecture

## System Overview

The Context7 system is a multi-layered architecture designed for autonomous learning and intelligent documentation caching. The system has evolved from metric-based learning to **LLM-powered conversation analysis**.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Session                      │
├─────────────────────────────────────────────────────────────┤
│  User Request → LLM → Tool Use (Write/Edit/MultiEdit)      │
└─────────────────────────┬───────────────────────────────────┘
                         │
┌─────────────────────────▼───────────────────────────────────┐
│                  PreToolUse Hook                           │
├─────────────────────────────────────────────────────────────┤
│  • Framework Detection                                     │
│  • Cache Lookup                                            │
│  • Context Provision or Documentation Fetch Request       │
│  • Exit Code 2 = Block + Provide Context                  │
└─────────────────────────┬───────────────────────────────────┘
                         │
┌─────────────────────────▼───────────────────────────────────┐
│                Tool Execution                               │
├─────────────────────────────────────────────────────────────┤
│  • File operations proceed with context                    │
│  • LLM has documentation to work with                      │
└─────────────────────────┬───────────────────────────────────┘
                         │
┌─────────────────────────▼───────────────────────────────────┐
│            PostToolUse Hook (Intelligent Mode)             │
├─────────────────────────────────────────────────────────────┤
│  • Conversation Context Capture                            │
│  • LLM Feedback Analysis                                   │
│  • Immediate Rule Updates                                  │
│  • Autonomous Learning                                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Core Components

#### 1. Hook Layer

**PreToolUse Hook** (`context7_cache_hook.py`)
- Entry point for all Write/Edit/MultiEdit operations
- Framework and operation detection
- Cache lookup and context provision
- Transcript awareness to prevent loops

**PostToolUse Hook** (Two Modes):
- **Intelligent**: `intelligent_posttooluse_hook.py` (NEW)
- **Legacy**: `session_tracker.py`

#### 2. Detection Layer (`src/detectors/`)

```python
DetectionEngine
├── FrameworkDetector     # Identifies React, FastAPI, etc.
├── OperationDetector     # Determines create, edit, delete, etc.
└── ContentAnalyzer       # Analyzes file content and intent
```

#### 3. Cache Layer (`src/db/`)

```python
DatabaseManager
├── SQLite Cache          # Local documentation storage
├── Session Logging       # Tracks all operations
├── Rule Storage          # Configuration management
└── Analytics Data        # Learning insights
```

#### 4. Learning Layer (`src/analyzers/`)

**Intelligent Mode** (NEW):
```python
IntelligentSessionAnalyzer
├── ConversationParser    # Extracts user intent and LLM feedback
├── ContextAnalyzer       # Detects documentation mismatches
├── RuleUpdater          # Immediately updates configuration
└── SafetyEngine         # Backup and error handling
```

**Legacy Mode**:
```python
LLMEffectivenessAnalyzer
├── MetricsCollector     # Session success/failure tracking
├── PatternAnalyzer      # Statistical pattern detection
├── BatchProcessor       # Delayed learning cycles
└── ThresholdEngine      # Statistical significance testing
```

#### 5. Rule Engine (`src/learning/`)

```python
RuleManager
├── ExtractionRules      # Which sections to include
├── TokenBudgets         # Content size limits
├── FrameworkMapping     # Operation-specific rules
└── ConfigValidator      # Rule integrity checking
```

## Data Flow

### Intelligent Learning Flow

```
1. User Request
   "Create a Redis setup script"
   
2. PreToolUse Detection
   Framework: fastapi (detected from file path)
   Operation: create
   Cache Key: fastapi:redis_setup
   
3. Cache Lookup
   Found: FastAPI web framework documentation
   Action: Block with FastAPI context
   
4. LLM Response
   "The hook is providing FastAPI context but I'm creating a Redis setup script"
   
5. PostToolUse Analysis
   Conversation: User wanted Redis, got FastAPI docs
   Decision: Documentation mismatch detected
   
6. Immediate Rule Update
   Cache Key: fastapi:redis_setup
   New Sections: ["redis_client", "setup", "configuration"]
   Reasoning: "Cache provided web framework docs for Redis client setup"
   
7. Next Occurrence
   Same operation now gets Redis-specific documentation
```

### Legacy Learning Flow

```
1-4. [Same as above]

5. PostToolUse Metrics
   Session: Complete/Incomplete
   Tokens Used: 188
   Follow-up Actions: None
   
6. Effectiveness Scoring
   Score: 0.4 (low token usage penalty)
   Status: Below threshold (0.6)
   
7. Batch Learning
   After 73+ similar sessions...
   Statistical Analysis: Pattern detected
   Rule Update: Maybe (if confidence > threshold)
```

## Storage Architecture

### Database Schema

**Session Logs** (`session_logs` table):
```sql
CREATE TABLE session_logs (
    log_id INTEGER PRIMARY KEY,
    session_id TEXT,
    cache_key TEXT,
    operation_type TEXT,
    sections_provided JSON,
    tokens_used INTEGER,
    tool_name TEXT,
    tool_input JSON,
    file_path TEXT,
    timestamp TIMESTAMP,
    
    -- Outcome tracking
    session_complete BOOLEAN,
    follow_up_actions JSON,
    
    -- Analysis results
    effectiveness_score REAL,
    effectiveness_reason TEXT,
    confidence_score REAL,
    analyzed_at TIMESTAMP
);
```

**Context Cache** (`context_cache` table):
```sql
CREATE TABLE context_cache (
    cache_key TEXT PRIMARY KEY,
    framework TEXT,
    full_content TEXT,
    sections JSON,
    cached_at TIMESTAMP,
    last_used TIMESTAMP,
    usage_count INTEGER
);
```

### File System Layout

```
~/.claude/
├── context7_cache.db              # Main SQLite database
├── context7_rules.json            # Rule configuration
├── context7_rules_history/        # Rule backup history
├── autonomous_updates.log         # Real-time learning log
├── hook_debug.log                 # Hook operation log
├── hook_errors.log                # Error tracking
└── conversations/                 # Conversation transcripts (if available)
```

## Configuration Architecture

### Rules Structure

```json
{
  "framework": {
    "operation": {
      "sections": ["section1", "section2"],
      "max_tokens": 2000,
      "_autonomous_update": {
        "updated_at": "timestamp",
        "reasoning": "why this rule was created/updated",
        "confidence": 0.8,
        "was_effective": false
      }
    }
  }
}
```

### Learning Modes

**Intelligent Mode Configuration**:
```python
LEARNING_CONFIG = {
    "mode": "intelligent",
    "analyzer": "IntelligentSessionAnalyzer",
    "trigger": "immediate",
    "threshold": "none",
    "confidence_required": 0.3,
    "update_policy": "immediate"
}
```

**Legacy Mode Configuration**:
```python
LEARNING_CONFIG = {
    "mode": "legacy",
    "analyzer": "LLMEffectivenessAnalyzer",
    "trigger": "batch",
    "threshold": 0.6,
    "confidence_required": 0.6,
    "sessions_required": 3
}
```

## Security Architecture

### Safety Mechanisms

1. **Code Isolation**: Rules only modify JSON configuration, never Python code
2. **Backup System**: All rule changes backed up with timestamps
3. **Graceful Failure**: Errors never disrupt user workflow
4. **Input Sanitization**: All user input sanitized before processing
5. **Path Validation**: File path traversal protection

### Audit Trail

```json
{
  "timestamp": "2025-07-23T10:49:59.741678",
  "action": "rule_updated",
  "cache_key": "fastapi:redis_setup",
  "old_rule": {...},
  "new_rule": {...},
  "reasoning": "Cache provided web framework docs for Redis client setup",
  "confidence": 0.8,
  "source": "intelligent_analyzer"
}
```

## Performance Architecture

### Optimization Strategies

1. **SQLite with Indexes**: Fast cache lookups
2. **Transcript Awareness**: Prevents redundant context provision
3. **Lazy Loading**: Components loaded only when needed
4. **Background Processing**: Non-blocking operations
5. **Token Budget Management**: Prevents oversized context

### Scalability

- **Local Storage**: No external dependencies for core functionality
- **Async Sync**: Optional Supabase sync for distributed setups
- **Modular Design**: Components can be replaced or extended
- **Hook Isolation**: Each operation processed independently

## Extension Points

### Adding New Frameworks

1. **Detector**: Add framework detection patterns
2. **Rules**: Define default extraction rules
3. **Patterns**: Add operation type mappings

### Custom Learning Logic

1. **Analyzer Interface**: Implement `SessionAnalyzer` interface
2. **Hook Integration**: Plug into PostToolUse hook
3. **Rule Updates**: Use `RuleManager` for safe updates

### External Integration

1. **Database Sync**: Extend `DatabaseManager` for external storage
2. **API Integration**: Add web API for remote management
3. **Analytics**: Export data for external analysis tools

The architecture is designed for autonomous operation with intelligent adaptation to user patterns while maintaining safety and reliability.