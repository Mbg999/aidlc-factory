# Reverse Engineering

**Purpose**: Analyze codebase; produce design artifacts

**Execute when**: Brownfield project (existing code present)

**Skip when**: Greenfield project (no code)

**Rerun behavior**: Controlled by `workspace-detection.md`: load current artifacts and skip. If artifacts stale (older than last significant code change) or user requests rerun, rerun to refresh artifacts

## Step 1: Multi-Package Discovery

### 1.1 Scan Workspace

### 1.2 Understand the Business Context

### 1.3 Infrastructure Discovery

### 1.4 Build System Discovery

### 1.5 Service Architecture Discovery

### 1.6 Code Quality Analysis

## Step 2: Generate Business Overview Documentation

Create `aidlc-docs/inception/reverse-engineering/<run-id>-business-overview.md`:

```markdown
# Business Overview

## Business Context Diagram
[Mermaid diagram showing the Business Context]

## Business Description

## Component Level Business Descriptions
### [Package/Component Name]
```

## Step 3: Generate Architecture Documentation

Create `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md`:

```markdown
# System Architecture

## System Overview
[High-level description of the system]

## Architecture Diagram
[Mermaid diagram showing all packages, services, data stores, relationships]

## Component Descriptions
### [Package/Component Name]

## Data Flow
[Mermaid sequence diagram of key workflows]

## Integration Points

## Infrastructure Components
```

## Step 4: Generate Code Structure Documentation

Create `aidlc-docs/inception/reverse-engineering/<run-id>-code-structure.md`:

```markdown
# Code Structure

## Build System

## Key Classes/Modules
[Mermaid class diagram or module hierarchy]

### Existing Files Inventory
[List all source files with their purposes - these are candidates for modification in brownfield projects]

**Example format**:

## Design Patterns
### [Pattern Name]

## Critical Dependencies
### [Dependency Name]
```

## Step 5: Generate API Documentation

Create `aidlc-docs/inception/reverse-engineering/<run-id>-api-documentation.md`:

```markdown
# API Documentation

## REST APIs
### [Endpoint Name]

## Internal APIs
### [Interface/Class Name]

## Data Models
### [Model Name]
```

## Step 6: Generate Component Inventory

Create `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md`:

```markdown
# Component Inventory

## Application Packages

## Infrastructure Packages

## Shared Packages

## Test Packages

## Total Count
```

## Step 7: Generate Technology Stack Documentation

Create `aidlc-docs/inception/reverse-engineering/<run-id>-technology-stack.md`:

```markdown
# Technology Stack

## Programming Languages

## Frameworks

## Infrastructure

## Build Tools

## Testing Tools
```

## Step 8: Generate Dependencies Documentation

Create `aidlc-docs/inception/reverse-engineering/<run-id>-dependencies.md`:

```markdown
# Dependencies

## Internal Dependencies
[Mermaid diagram showing package dependencies]

### [Package A] depends on [Package B]

## External Dependencies
### [Dependency Name]
```

## Step 9: Generate Code Quality Assessment

Create `aidlc-docs/inception/reverse-engineering/<run-id>-code-quality-assessment.md`:

```markdown
# Code Quality Assessment

## Test Coverage

## Code Quality Indicators

## Technical Debt

## Patterns and Anti-patterns
```

## Step 10: Create Timestamp File

Create `aidlc-docs/inception/reverse-engineering/<run-id>-reverse-engineering-timestamp.md`:

```markdown
# Reverse Engineering Metadata

**Analysis Date**: [ISO timestamp]
**Analyzer**: AI-DLC
**Workspace**: [Workspace path]
**Total Files Analyzed**: [Number]

## Artifacts Generated
```

## Step 11: Skills Discovery (Conditional)

**Execute IF**: Skills not yet installed in `.agents/skills/`

**Skip IF**: Skills already installed or user declined

When needed, recommend installing skills:

```bash
python scripts/install_aidlc.py --tool <tool> --with-agent-skills --dest .
```

## Step 12: Update State Tracking

Update `aidlc-docs/aidlc-state.md`:

```markdown
## Reverse Engineering Status
```

## Step 13: Present Completion Message to User

```markdown
# 🔍 Reverse Engineering Complete

[AI-generated summary of key findings from analysis in the form of bullet points]

> **📋 <u>**REVIEW REQUIRED:**</u>**  
> Please examine the reverse engineering artifacts at: `aidlc-docs/inception/reverse-engineering/`

> **🚀 <u>**WHAT'S NEXT?**</u>**
>
> **You may:**
>
> 🔧 **Request Changes** - Ask for modifications to the reverse engineering analysis if required
> ✅ **Approve & Continue** - Approve analysis and proceed to **Requirements Analysis**
```

## Step 14: Wait for User Approval

