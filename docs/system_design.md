# GenAI Operations Assistant – System Design

## Architecture Overview

The system separates responsibilities between the LLM and deterministic business logic.

### Domain Logic
Deterministic functions perform calculations such as production capacity and defect adjustments.

### Tool Layer
Domain logic functions are exposed as callable tools for the model.

### LLM Layer
The LLM interprets user questions and explains the results returned by deterministic tools.

### Guardrails
The system refuses responses when:
- required parameters are missing
- documentation confidence is below threshold