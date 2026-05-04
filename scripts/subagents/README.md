# Subagentes (Subagents) — uso rápido

Breve guía para el ejemplo de subagentes incluido en este repositorio.

Archivos clave
- `aidlc-rules/aidlc-rule-details/extensions/subagents/agents.yaml` — lista declarativa de agentes (metadatos).
- `aidlc-rules/aidlc-rule-details/extensions/subagents/agents.json` — fallback JSON si PyYAML no está instalado.
- `aidlc-rules/aidlc-rule-details/extensions/subagents/code-reviewer.opt-in.md` — prompt de opt‑in para activar la regla.
- `aidlc-rules/aidlc-rule-details/extensions/subagents/code-reviewer.md` — definición completa de la regla/agent.
- `scripts/subagents/manager.py` — dispatcher que carga la metadata y ejecuta el entrypoint `run(context)` de cada agente.
- `scripts/subagents/code_reviewer.py` — subagente de ejemplo (implementación mínima; expone `run(context)`).

Cómo funciona (resumen)
1. El manager carga `agents.yaml` (o `agents.json`) y obtiene la lista de agentes.
2. Para cada agente habilitado por su `enforce_in_phases`, el manager ejecuta el script `entrypoint` y llama a `run(context)`.
3. En el pipeline de evaluación, `scripts/aidlc-evaluator/scripts/run_evaluation.py` invoca los subagentes después
   de la ejecución de AIDLC y escribe los resultados en `runs/<timestamp>/subagents-results.yaml`.

Ejecutar localmente (comprobación rápida)
```bash
# desde la raíz del repo (asegúrate de activar tu venv)
python scripts/subagents/manager.py code-reviewer '{"sample":"x"}'
```

Uso dentro del pipeline
- El runner de evaluación (`run_evaluation.py`) llama a los agentes para las fases `construction` y
  `build-and-test`. Los resultados se guardan en el run folder como `subagents-results.yaml`.

Agregar un nuevo subagente
1. Crear un archivo opt‑in `extensions/subagents/<id>.opt-in.md` (si quieres soporte de opt‑in en la UI).
2. Añadir la definición `extensions/subagents/<id>.md` con la documentación de la regla/agente.
3. Añadir la entrada en `agents.yaml` (o `agents.json`) indicando `id`, `entrypoint` y `enforce_in_phases`.
4. Implementar el script `scripts/subagents/<entrypoint>.py` exponiendo `def run(context) -> dict`.

Seguridad y aislamiento
- Ejecución aislada: el `manager` ejecuta ahora cada subagente en un proceso Python separado
  (subprocess) con un `cwd` temporal y un entorno minimalista (PATH/HOME/LANG preservados).
  Esto evita que el código top-level del subagente se ejecute dentro del proceso del manager
  y reduce el riesgo de efectos secundarios o fugas de estado.
- Recomendación de contenedores: para análisis de terceros o tareas con acceso a la red
  use contenedores (Docker) o sandboxes dedicados. Ejecutar agentes en contenedores permite
  aplicar límites de recursos, políticas de red y volúmenes montados de forma controlada.
- Permisos y scope: `permissions` en `agents.yaml` es metadata. El `manager` ahora
  resuelve esas reglas y realiza comprobaciones estáticas antes de ejecutar un
  agente in-process. Para aislamiento fuerte monte los volúmenes permitidos en
  contenedores Docker (ver abajo).

Auditoría y límites
- Logs estructurados: el manager escribe logs JSON por ejecución en
  `runs/<run-folder>/subagents-logs/` (si se ejecuta dentro de un `run_folder`) o
  a nivel de repo en `subagents-logs/` si no hay `run_folder`. Los ficheros contienen:
  `agent_entrypoint`, `agent_hash`, `started_at`, `finished_at`, `duration_seconds`,
  `returncode`, `stdout`, `stderr`, `parsed_result`, y `context` (saneado).
- Límite por agente: puedes declarar `timeout` y `limits` en la definición del agente
  (`agents.yaml`) y el manager los respetará cuando estén presentes. Ejemplo:

```yaml
agents:
  - id: example-agent
    entrypoint: scripts/subagents/example.py
    timeout: 60            # segundos
    limits:
      memory_mb: 256
      cpu_seconds: 30
```

- El wrapper establece `RLIMIT_AS` (memoria virtual) y `RLIMIT_CPU` antes de cargar
  el script del agente cuando `limits` está configurado. Esto ayuda a limitar el impacto
  de agentes fallidos o maliciosos.

Contexto y saneamiento
- El manager sanea el `context` antes de pasarlo al subagente: claves sensibles
  (p. ej. que contienen `secret`, `token`, `password`, `aws`, `credentials`, `key`)
  se redactan y valores muy largos se truncan. Esto protege secretos y reduce la
  cantidad de datos transferidos al proceso del agente.

Configuración de ejecución
- `SUBAGENTS_USE_DOCKER=1`: fuerza que el manager intente ejecutar agentes en
  contenedores Docker (si está disponible). Si el agente declara `use_docker: true`
  en su entrada, el manager también intentará usar Docker para ese agente.

Validación de salida
- Se realiza una validación mínima de la salida JSON de `run(context)` (campos
  `agent_id` y `status` requeridos). Si tiene `jsonschema` instalado, el manager
  podrá validar la salida contra un esquema más estricto si el agente provee
  `output_schema` en su definición.

Notas finales
- Esta integración es un ejemplo del patrón "plugins declarativos + dispatcher". Puedes ampliarlo para:
  - Respetar respuestas de opt‑in guardadas en `aidlc-docs/aidlc-state.md`.
  - Ejecutar agentes en paralelo o en contenedores separados.
  - Añadir roles/permiso más estrictos y auditoría.
  - Validar la salida de los agentes con un esquema JSON para evitar formatos inesperados.
  - Registrar y auditar la ejecución (stdout/stderr, duración, returncode) para análisis forense.
