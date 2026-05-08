# AI-DLC Adaptive Workflow Overview

**Purpose**: Technical ref for AI and devs to understand workflow.

## The Three-Phase Lifecycle:
- **INCEPTION PHASE**: Planning & architecture (Workspace Detection + conditional phases + Workflow Planning)
- **CONSTRUCTION PHASE**: Design, implement, build & test (per-unit design + Code Generation + Build & Test)
- **OPERATIONS PHASE**: Placeholder for future deploy & monitoring

## The Adaptive Workflow:
- **Workspace Detection** (always) → **Reverse Engineering** (brownfield only) → **Requirements Analysis** (always, adaptive depth) → **Conditional Phases** (as needed) → **Workflow Planning** (always) → **Code Generation** (always, per-unit) → **Build and Test** (always)

## How It Works:
- AI analyzes request, workspace, complexity → pick needed stages
- Always: Workspace Detection; Requirements Analysis (adaptive); Workflow Planning; Code Generation (per-unit); Build & Test
- Conditional: Reverse Eng, User Stories, App Design, Units Generation, per-unit design (Functional, NFR Req, NFR Design, Infra Design)
- No fixed sequence — run stages in logical order per task

## Your Team's Role:
- Answer questions in dedicated question files using [Answer]: tags (A, B, C, D, E)
- Option E = Other — describe custom response
- Review & approve each phase as team
- Decide architecture collectively when needed
- Team effort — involve stakeholders per phase

## AI-DLC Three-Phase Workflow:

```mermaid
flowchart TD
    Start(["User Request"])
    
    subgraph INCEPTION["🔵 INCEPTION PHASE"]
        WD["Workspace Detection<br/><b>ALWAYS</b>"]
        RE["Reverse Engineering<br/><b>CONDITIONAL</b>"]
        RA["Requirements Analysis<br/><b>ALWAYS</b>"]
        Stories["User Stories<br/><b>CONDITIONAL</b>"]
        WP["Workflow Planning<br/><b>ALWAYS</b>"]
        AppDesign["Application Design<br/><b>CONDITIONAL</b>"]
        UnitsG["Units Generation<br/><b>CONDITIONAL</b>"]
    end
    
    subgraph CONSTRUCTION["🟢 CONSTRUCTION PHASE"]
        FD["Functional Design<br/><b>CONDITIONAL</b>"]
        NFRA["NFR Requirements<br/><b>CONDITIONAL</b>"]
        NFRD["NFR Design<br/><b>CONDITIONAL</b>"]
        ID["Infrastructure Design<br/><b>CONDITIONAL</b>"]
        CG["Code Generation<br/><b>ALWAYS</b>"]
        BT["Build and Test<br/><b>ALWAYS</b>"]
    end
    
    subgraph OPERATIONS["🟡 OPERATIONS PHASE"]
        OPS["Operations<br/><b>PLACEHOLDER</b>"]
    end
    
    Start --> WD
    WD -.-> RE
    WD --> RA
    RE --> RA
    
    RA -.-> Stories
    RA --> WP
    Stories --> WP
    
    WP -.-> AppDesign
    WP -.-> UnitsG
    AppDesign -.-> UnitsG
    UnitsG --> FD
    FD -.-> NFRA
    NFRA -.-> NFRD
    NFRD -.-> ID
    
    WP --> CG
    FD --> CG
    NFRA --> CG
    NFRD --> CG
    ID --> CG
    CG -.->|Next Unit| FD
    CG --> BT
    BT -.-> OPS
    BT --> End(["Complete"])
    
    style WD fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style RA fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style WP fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff

    style CG fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style BT fill:#4CAF50,stroke:#1B5E20,stroke-width:3px,color:#fff
    style OPS fill:#BDBDBD,stroke:#424242,stroke-width:2px,stroke-dasharray: 5 5,color:#000
    style RE fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style Stories fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style AppDesign fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000

    style UnitsG fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style FD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style NFRA fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style NFRD fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style ID fill:#FFA726,stroke:#E65100,stroke-width:3px,stroke-dasharray: 5 5,color:#000
    style INCEPTION fill:#BBDEFB,stroke:#1565C0,stroke-width:3px, color:#000
    style CONSTRUCTION fill:#C8E6C9,stroke:#2E7D32,stroke-width:3px, color:#000
    style OPERATIONS fill:#FFF59D,stroke:#F57F17,stroke-width:3px, color:#000
    style Start fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    style End fill:#CE93D8,stroke:#6A1B9A,stroke-width:3px,color:#000
    
    linkStyle default stroke:#333,stroke-width:2px
```

**Stage Descriptions:**

**🔵 INCEPTION PHASE** - Planning and Architecture
- Workspace Detection: Analyze workspace state & project type (ALWAYS)
- Reverse Engineering: Analyze existing codebase (CONDITIONAL - Brownfield only)
- Requirements Analysis: Gather & validate requirements (ALWAYS - adaptive depth)
- User Stories: Create user stories & personas (CONDITIONAL)
- Workflow Planning: Create execution plan (ALWAYS)
- Application Design: High-level component identification & service-layer design (CONDITIONAL)
- Units Generation: Decompose into units of work (CONDITIONAL)

**🟢 CONSTRUCTION PHASE** - Design, Implementation, Build and Test
- Functional Design: Business-logic design per unit (CONDITIONAL, per-unit)
- NFR Requirements: Define NFRs & pick tech stack (CONDITIONAL, per-unit)
- NFR Design: Add NFR patterns & logical components (CONDITIONAL, per-unit)
- Infrastructure Design: Map to infra services (CONDITIONAL, per-unit)
- Code Generation: Generate code (Planning → Generation) (ALWAYS, per-unit)
- Build and Test: Build units & run tests (ALWAYS)

**🟡 OPERATIONS PHASE** - Placeholder
- Operations: Placeholder for future deploy & monitoring workflows (PLACEHOLDER)

**Key Principles:**
- Run phases only when they add value
- Evaluate phases independently
- INCEPTION = what + why
- CONSTRUCTION = how + build & test
- OPERATIONS = placeholder for future
- Simple changes may skip conditional INCEPTION steps
- Complex changes get full INCEPTION + CONSTRUCTION

## Glossary

| Term | Meaning |
|------|---------|
| **Phase** | High-level lifecycle bucket: INCEPTION, CONSTRUCTION, OPERATIONS |
| **Stage** | Individual activity within a phase (e.g., Code Generation) |
| **Unit of Work** | Logical story grouping for planning/decomposition |
| **Service** | Independently deployable component (microservices) |
| **Module** | Logical grouping inside a service/monolith |
| **Component** | Reusable building block (class, function, package) |
| **Planning** | Create plans with questions + checkboxes for approval |
| **Generation** | Execute approved plans to produce artifacts |
| **NFR** | Non-Functional Requirements |
| **AI-DLC** | AI-Driven Development Life Cycle |

**Terminology rules**: Use "phase" for INCEPTION/CONSTRUCTION/OPERATIONS; "stage" for activities within phases. Never say "Requirements phase" (it's a stage) or "CONSTRUCTION stage" (it's a phase).