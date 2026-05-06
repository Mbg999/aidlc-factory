# 🧠 Guía completa: Subagentes con ejecución automática para AI-DLC

## ⚠️ Problema que estás viendo

Si tus agentes:

* intentan ejecutar scripts Python
* piden permisos constantemente
* o directamente no pueden ejecutar nada

👉 **No es un error tuyo. Es por diseño de seguridad.**

Los LLMs (Claude, Copilot, etc.) **NO tienen acceso directo al sistema**.

---

## 🧠 Idea clave

> ❌ Un agente NO debe ejecutar código
> ✅ Un agente decide qué hacer, y tu sistema lo ejecuta

---

## 🏗️ Arquitectura correcta

```text
[Usuario]
   ↓
[Agente (LLM)]
   ↓ (decisión estructurada)
[Orquestador]
   ↓
[Executor seguro]
   ↓
[Scripts Python / Sistema]
```

---

## 🧩 Patrón de diseño

## ❌ Incorrecto

```text
Agente → ejecuta script directamente
```

## ✅ Correcto

```text
Agente → devuelve acción → backend ejecuta
```

---

## ⚙️ Implementación básica en Python

```python
import subprocess

ALLOWED_SCRIPTS = [
    "preprocess.py",
    "train.py",
    "evaluate.py"
]

def run_script(script, args):
    if script not in ALLOWED_SCRIPTS:
        raise Exception(f"Script no permitido: {script}")

    result = subprocess.run(
        ["python", script] + args,
        capture_output=True,
        text=True
    )

    return result.stdout


def orchestrator(agent_output):
    if agent_output["action"] == "run_script":
        return run_script(
            agent_output["script"],
            agent_output.get("args", [])
        )
```

---

## 🤖 Formato que debe devolver el agente

```json
{
  "action": "run_script",
  "script": "train.py",
  "args": ["--epochs", "10"]
}
```

---

## 🧠 Subagentes recomendados (AI-DLC)

Divide tu sistema así:

## 1. Planner

```json
{
  "steps": [
    { "action": "preprocess" },
    { "action": "train", "epochs": 10 },
    { "action": "evaluate" }
  ]
}
```

## 2. Executor (NO es LLM)

* Ejecuta scripts reales
* Controla permisos
* Maneja errores

## 3. Reviewer

* Revisa outputs
* Detecta fallos

## 4. Loop de mejora

```text
code → review → fix → repeat
```

---

## 🔄 Ejemplo completo de flujo

```text
User: "Entrena modelo"

↓
Planner Agent:
{
  "steps": [
    { "script": "preprocess.py" },
    { "script": "train.py", "args": ["--epochs", "10"] }
  ]
}

↓
Orquestador:
→ ejecuta preprocess.py
→ ejecuta train.py --epochs 10
```

---

## 🔐 Seguridad (MUY IMPORTANTE)

## Nunca hagas esto

```python
subprocess.run(agent_output["command"], shell=True)
```

## Siempre usa

* allowlist de scripts
* validación de argumentos
* sin `shell=True`

---

## 🚀 Nivel PRO (recomendado)

## 1. Tool Calling

Define funciones en vez de scripts:

```json
{
  "name": "train_model",
  "parameters": {
    "epochs": "number"
  }
}
```

El agente devuelve:

```json
{
  "tool": "train_model",
  "arguments": {
    "epochs": 10
  }
}
```

---

## 2. Paralelización

```python
from concurrent.futures import ThreadPoolExecutor
```

Ejecutar múltiples tareas a la vez.

---

## 3. Logs + trazabilidad

Guarda todo:

* inputs
* outputs
* errores

---

## 4. Memoria de agentes

Cada agente puede tener:

* contexto propio
* historial
* estado

---

## 🧠 Insight clave

> Los agentes NO son procesos del sistema
> Son motores de decisión

👉 Tú controlas la ejecución real.

---

## 🧩 Estructura recomendada del proyecto

```text
ai-dlc/
│
├── agents/
│   ├── planner.py
│   ├── reviewer.py
│
├── orchestrator/
│   └── main.py
│
├── executors/
│   └── runner.py
│
├── scripts/
│   ├── preprocess.py
│   ├── train.py
│   └── evaluate.py
│
└── logs/
```

---

## 🔥 Resumen

* ❌ No dejes al LLM ejecutar código directamente
* ✅ Usa un orquestador
* ✅ El LLM decide, tu sistema ejecuta
* ✅ Usa allowlists y validación

---

## 🧠 Siguiente paso

Puedes evolucionar esto a:

* multi-agentes colaborando
* pipelines complejos
* sistemas autónomos controlados

---
