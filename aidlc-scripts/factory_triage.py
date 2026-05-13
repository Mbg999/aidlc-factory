#!/usr/bin/env python3
"""factory_triage.py — Pre-pipeline complexity scorer for AIDLC Orchestrator.

Determines whether a user request qualifies for FAST_PATH (TINY tier, bypasses
multi-agent) or needs the full pipeline (SMALL/MEDIUM/LARGE).

Usage
-----
    factory_triage.py "<user-request>" [--explain]

Output (stdout JSON):
    {
      "score": 1,
      "tier": "TINY",
      "factors": { ... 8 factor scores ... },
      "explanation": "...",
      "recommended_pipeline": "fast"
    }

Exit codes:
    0 — TINY (FAST_PATH recommended)
    1 — SMALL
    2 — MEDIUM
    3 — LARGE
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# Each factor has keywords mapped to +1 or +2 signals.
# Order matters: first match wins the higher value.

FACTOR_KEYWORDS: dict[str, list[tuple[int, list[str]]]] = {
    "file_count_signal": [
        (2, [
            "across the codebase", "across all services", "across all",
            "across every", "6 files", "7 files", "8 files", "9 files",
            "10+ files", "dozens of files", "many files",
            "multiple services",
        ]),
        (1, [
            "2 files", "3 files", "4 files", "5 files",
            "two files", "three files", "four files", "five files",
            "create a file", "modify a file", "update a file",
        ]),
    ],
    "architecture_signal": [
        (2, [
            "system architecture", "architectural", "microservices",
            "service mesh", "event-driven architecture", "cqrs",
            "multiple services", "service decomposition",
        ]),
        (1, [
            "microservice", "new module", "service boundary",
            "extract module", "split service", "new service",
            "api gateway",
        ]),
    ],
    "concurrency_signal": [
        (2, [
            "race condition", "race", "deadlock", "distributed lock",
            "distributed transaction", "saga", "consensus",
            "thread safety", "concurrent access",
        ]),
        (1, [
            "async", "asynchronous", "queue", "worker", "stream",
            "background job", "event bus", "kafka", "rabbitmq",
            "pub/sub", "webhook", "callback",
        ]),
    ],
    "external_api_signal": [
        (2, [
            "multi-vendor", "multiple apis", "aggregate",
            "payment gateway", "stripe and", "aws and", "azure and",
            "integration hub",
        ]),
        (1, [
            "stripe", "s3", "github api", "slack api", "twilio",
            "sendgrid", "postmark", "api integration",
            "external service", "third-party", "rest api call",
            "graphql api", "webhook receiver",
        ]),
    ],
    "security_signal": [
        (2, [
            "oauth", "oauth2", "oidc", "rbac", "abac",
            "key rotation", "secret rotation", "zero trust",
            "mfa", "2fa", "saml", "sso", "identity provider",
            "permission model", "access control list",
        ]),
        (1, [
            "auth", "authentication", "authorization",
            "jwt", "token", "login", "logout", "signup",
            "password", "hash", "encrypt", "decrypt",
            "api key", "secret", "credential",
        ]),
    ],
    "infrastructure_signal": [
        (2, [
            "ci/cd", "ci/cd pipeline", "github actions", "gitlab ci",
            "deploy pipeline", "terraform", "pulumi", "cloudformation",
            "kubernetes", "k8s", "helm", "istio", "envoy",
            "infrastructure as code",
        ]),
        (1, [
            "docker", "dockerfile", "containerize", "container",
            "docker-compose", "nginx", "reverse proxy",
            "load balancer", "alb", "nlb",
        ]),
    ],
    "domain_logic_signal": [
        (2, [
            "pricing engine", "pricing", "fraud detection",
            "fraud", "state machine", "workflow engine",
            "rules engine", "calculation engine",
            "billing system", "billing", "subscription",
            "recommendation", "ranking algorithm",
        ]),
        (1, [
            "business rule", "business logic", "validation rule",
            "calculation", "compute", "derive",
            "eligibility", "approval workflow", "invoice",
        ]),
    ],
    "scope_breadth_signal": [
        (2, [
            "refactor across", "migrate", "rewrite",
            "across all", "every service", "replace",
        ]),
        (1, [
            "refactor", "restructure", "reorganize",
            "module", "component", "layer",
            "add endpoint", "new endpoint", "add route",
            "new route", "new api", "add api",
        ]),
    ],
}


def score_request(text: str) -> tuple[int, dict[str, int], str]:
    """Score a user request across 8 factors. Returns (total, factors, explanation)."""
    lower = text.lower()
    factors: dict[str, int] = {}
    explanations: list[str] = []

    for factor, rules in FACTOR_KEYWORDS.items():
        score = 0
        for value, keywords in rules:
            for kw in keywords:
                if re.search(rf'(?<!\w){re.escape(kw)}(?!\w)', lower):
                    score = max(score, value)
        factors[factor] = score
        if score == 0:
            explanations.append(f"{factor}=0")
        elif score == 1:
            explanations.append(f"{factor}=1 (moderate)")
        else:
            explanations.append(f"{factor}=2 (strong)")

    total = sum(factors.values())
    return total, factors, "; ".join(explanations)


def tier_from_score(score: int) -> tuple[str, str, int]:
    """Map total score to tier and pipeline name.

    Returns (tier, pipeline, exit_code).
    """
    # TINY only for score 0 (zero complexity signals fired).
    # Score >= 1 means at least one governance flag triggered -> SMALL+.
    if score == 0:
        return "TINY", "fast", 0
    if score <= 5:
        return "SMALL", "full", 1
    if score <= 8:
        return "MEDIUM", "full", 2
    return "LARGE", "full", 3


def main() -> None:
    p = argparse.ArgumentParser(
        description="AIDLC Orchestrator — Complexity Triage"
    )
    p.add_argument("request", help="User request text")
    p.add_argument("--explain", action="store_true",
                   help="Print human-readable explanation to stderr")
    p.add_argument("--dry-run", action="store_true",
                   help="Print human-readable summary instead of JSON (for /factory-spec)")
    args = p.parse_args()

    total, factors, explanation = score_request(args.request)
    tier, pipeline, exit_code = tier_from_score(total)

    if args.dry_run:
        stage_count = 1 if pipeline == "fast" else 7
        est_tokens = "~50K" if pipeline == "fast" else "~800K"
        est_time = "~8 min" if pipeline == "fast" else "~40 min"
        pipeline_label = "FAST_PATH" if pipeline == "fast" else "FULL pipeline"
        path = f"{'workspace-scout → requirements-analyst → workflow-planner → code-generator → build-test-agent → review → ship' if pipeline == 'full' else 'code-generator'}"
        print(f"Triage: {tier} (score {total}) → {pipeline_label}")
        print(f"  {stage_count} spawn(s) via {path}")
        print(f"  ~{est_tokens} tokens, ~{est_time} wall clock")
        print(f"  Factors: {', '.join(f'{k}={v}' for k, v in sorted(factors.items()) if v > 0) or 'none'}")
        sys.exit(exit_code)

    result = {
        "score": total,
        "tier": tier,
        "factors": factors,
        "explanation": explanation,
        "recommended_pipeline": pipeline,
    }
    print(json.dumps(result, indent=2))

    if args.explain:
        print(f"TRIAGE: score={total} tier={tier} pipeline={pipeline}",
              file=sys.stderr)
        for factor, score in sorted(factors.items()):
            bar = "#" * score + "." * (2 - score)
            print(f"  {factor:25s} [{bar}] {score}", file=sys.stderr)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
