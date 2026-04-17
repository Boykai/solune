# Security Audit Contracts

This directory contains behavioral contracts for the Security, Privacy & Vulnerability Audit feature.

Since this feature is a security hardening effort (not a new API surface), the contracts define security behavioral guarantees rather than new REST/GraphQL endpoints.

## Contract Files

- [security-headers.yaml](security-headers.yaml) — HTTP response header requirements
- [startup-validation.yaml](startup-validation.yaml) — Configuration validation contracts
- [access-control.yaml](access-control.yaml) — Project access authorization contracts
- [rate-limiting.yaml](rate-limiting.yaml) — Rate limiting behavioral contracts
