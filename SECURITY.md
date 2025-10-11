# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of GCP FinOps Sentinel seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via [GitHub Security Advisories](https://github.com/syalioune/gcp-finops-sentinel/security/advisories/new).

### What to Include

To help us better understand and resolve the issue, please include as much of the following information as possible:

- Type of issue (e.g., privilege escalation, information disclosure, credential exposure)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: We will acknowledge your report within 72 hours
- **Status Update**: We will send you regular updates about our progress
- **Fix Timeline**: We aim to release a fix within 30 days for critical vulnerabilities
- **Disclosure**: We will coordinate with you on the disclosure timeline

### Safe Harbor

We support safe harbor for security researchers who:

- Make a good faith effort to avoid privacy violations, destruction of data, and interruption or degradation of our services
- Only interact with accounts you own or with explicit permission of the account holder
- Do not exploit a security issue for purposes other than verification
- Give us reasonable time to resolve the issue before any disclosure
- Do not violate any other applicable laws or regulations

## Security Best Practices

### For Users

When deploying GCP FinOps Sentinel:

1. **Never commit secrets** - Use Secret Manager for sensitive configuration
2. **Use least-privilege IAM** - Only grant required permissions
3. **Enable audit logging** - Monitor organization policy changes
4. **Test in dry-run mode** - Verify rules before enabling enforcement
5. **Rotate credentials** - Regular rotation of SMTP
6. **Use Workload Identity** - Avoid service account keys where possible
7. **Enable VPC Service Controls** - Additional layer of security (optional)
8. **Review logs regularly** - Monitor for unexpected behavior

### For Contributors

When contributing code:

1. **Never commit credentials** - Use environment variables or mock data
2. **Run pre-commit hooks** - Includes secret detection
3. **Update dependencies** - Keep dependencies current and patched
4. **Follow secure coding practices** - Input validation, error handling
5. **Write security tests** - Test authentication and authorization

## Known Security Considerations

### Organization-Level Permissions

GCP FinOps Sentinel requires organization-level permissions to function:

- `roles/orgpolicy.policyAdmin` - For policy enforcement
- `roles/browser` - For project discovery

These are powerful permissions. Ensure:
- The service account is only used for this purpose
- Audit logs are enabled to track all policy changes
- Rules are tested thoroughly in dry-run mode before production use

### SMTP Credentials

If using email notifications:
- Store SMTP passwords in Secret Manager, not environment variables
- Use app-specific passwords (Gmail) or API keys (SendGrid, SES)
- Rotate credentials regularly
- Use TLS for all SMTP connections

### Budget Alert Data

Budget alerts contain sensitive financial information:
- Ensure Pub/Sub topics have appropriate IAM restrictions
- Consider encrypting data at rest and in transit
- Limit access to action event topics

## Security Updates

We will:
- Release security patches as soon as possible
- Update this SECURITY.md with patch information
- Notify users via GitHub Security Advisories
- Update CHANGELOG.md with security fixes

## Contact

For non-security issues:
- [GitHub Issues](https://github.com/syalioune/gcp-finops-sentinel/issues)
- [GitHub Discussions](https://github.com/syalioune/gcp-finops-sentinel/discussions)

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged in our CHANGELOG (unless they prefer to remain anonymous).

---

**Last Updated**: 2025-10-23
