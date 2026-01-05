# Security Policy

## Supported Versions

Use the latest version of this project to ensure you have the latest security patches.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of this project seriously. If you find any security vulnerability, please do NOT open a public issue.

Instead, please report it by emailing [SECURITY_EMAIL_PLACEHOLDER] or contacting the maintainers directly.

### Critical Security Reminders

1.  **API Keys**: Never commit your `.env` or `config.json` files.
2.  **Gitignore**: Ensure `.env` is always in `.gitignore`.
3.  **Verification**: Run `./scripts/verify-safety.sh` before pushing to GitHub.
