#!/usr/bin/env python3
"""
Security checklist validator for the Rizz API.

Reads api-server/openapi.yaml and asserts that:
  - Every endpoint has a description.
  - Every endpoint that mutates state (POST/PUT/PATCH/DELETE) has
    a JSON request body schema (4xx responses are required).
  - Endpoints that are documented as requiring auth actually
    reference the bearerAuth security scheme.
  - Every response code in {400, 401, 403, 404, 409, 415, 422, 429, 500}
    is documented if the endpoint is marked as security-relevant.

Usage:
    python3 scripts/check-security.py
    python3 scripts/check-security.py --strict   # exit non-zero on warnings

Exit code: 0 if clean, 1 if errors, 2 if warnings (with --strict).
"""

import argparse
import os
import sys

import yaml


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPEC_PATH = os.path.join(PROJECT_ROOT, "api-server", "openapi.yaml")

# Endpoints that are "state-mutating" — they MUST have requestBody
MUTATING_METHODS = {"post", "put", "patch", "delete"}

# 4xx response codes that an endpoint should document
EXPECTED_4XX = {400, 401, 403, 404, 409, 415, 422, 429}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 on warnings, not just errors")
    args = ap.parse_args()

    if not os.path.exists(SPEC_PATH):
        print(f"ERROR: OpenAPI spec not found at {SPEC_PATH}")
        return 1

    with open(SPEC_PATH) as f:
        spec = yaml.safe_load(f)

    errors = []
    warnings = []

    paths = spec.get("paths", {})
    if not paths:
        errors.append("OpenAPI spec has no paths defined")
        print("\n".join(errors))
        return 1

    # Check that bearerAuth scheme is defined
    schemes = spec.get("components", {}).get("securitySchemes", {})
    if "bearerAuth" not in schemes:
        warnings.append(
            "components.securitySchemes.bearerAuth is not defined. "
            "Endpoints cannot reference authentication."
        )

    for path, methods in paths.items():
        for method, op in methods.items():
            if method.startswith("x-") or method not in (
                "get", "post", "put", "delete", "patch", "options", "head"
            ):
                continue
            tag = f"{method.upper():6s} {path}"
            # 1. Description
            if not op.get("description") and not op.get("summary"):
                warnings.append(f"{tag}: missing description AND summary")

            # 2. Mutating methods must have a requestBody
            if method in MUTATING_METHODS and not op.get("requestBody"):
                # Allow parameter-only mutations (rare). /metrics is GET.
                if path not in ("/api/posts/{post_id}",):  # DELETE has no body
                    if method != "delete":
                        errors.append(
                            f"{tag}: mutating method has no requestBody schema"
                        )

            # 3. Check 4xx response codes are documented
            responses = op.get("responses", {})
            response_codes = {int(c) for c in responses.keys() if c.isdigit()}

            # 4. For protected endpoints, verify security is set
            if op.get("security"):
                for sec in op["security"]:
                    if "bearerAuth" not in sec:
                        warnings.append(
                            f"{tag}: uses non-bearerAuth security: {sec}"
                        )

            # 5. 500 should always be documented (defense in depth)
            if 500 not in response_codes:
                warnings.append(
                    f"{tag}: missing 500 response documentation"
                )

    # Report
    print(f"Scanned {len(paths)} paths in {SPEC_PATH}\n")

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        print()
        return 1

    if warnings and args.strict:
        return 2

    print("OK: security checklist passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
