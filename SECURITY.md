# Security Policy

## Supported Versions

Currently, the following versions are being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within Chrome2NAS M3U8 Downloader, please follow these steps:

### Do NOT

- **Do not** open a public GitHub issue
- **Do not** disclose the vulnerability publicly until it has been addressed

### Please DO

1. **Email** the maintainers privately (create a security advisory on GitHub)
2. **Provide** detailed information about the vulnerability:
   - Type of issue (e.g., authentication bypass, SQL injection, XSS)
   - Full paths of affected source files
   - Location of the affected code (tag/branch/commit)
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the vulnerability

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Status Update**: Every 7 days until resolved
- **Fix Release**: Depends on severity (Critical: 7 days, High: 14 days, Medium: 30 days)

## Security Best Practices

### For Users

1. **API Key Security**
   - Generate strong API keys (minimum 32 characters)
   - Use `openssl rand -base64 32` to generate secure keys
   - Never commit `.env` files to version control
   - Rotate API keys periodically

2. **Network Security**
   - Use HTTPS in production (not HTTP)
   - Configure proper firewall rules
   - Limit API access to trusted networks
   - Consider using VPN or Tailscale for remote access

3. **Docker Security**
   - Keep Docker images updated
   - Run containers as non-root users when possible
   - Limit container capabilities
   - Use Docker secrets for sensitive data

4. **Database Security**
   - Use strong database passwords
   - Restrict database access to localhost
   - Regular database backups
   - Enable PostgreSQL SSL connections in production

### For Developers

1. **Code Security**
   - Validate all user inputs
   - Use parameterized queries (already implemented)
   - Sanitize file paths
   - Implement rate limiting (already implemented)

2. **Dependency Security**
   - Regularly update dependencies
   - Use `pip audit` to check for vulnerable packages
   - Review dependencies before adding new ones

3. **Testing**
   - Test with various malicious inputs
   - Check for path traversal vulnerabilities
   - Verify authentication on all endpoints
   - Test CORS configuration

## Known Security Considerations

### Current Implementation

1. **Authentication**: API Key-based (Bearer token)
   - Simple but effective for private NAS deployments
   - Consider OAuth2 for multi-user scenarios

2. **CORS**: Configured for Chrome extensions
   - Default: `chrome-extension://*`
   - Adjust for your specific needs

3. **Rate Limiting**: Basic implementation
   - Default: 10 requests per minute
   - Configurable via environment variables

4. **File System Access**: 
   - Limited to configured download directories
   - No user-provided file paths accepted

### Limitations

1. **DRM Content**: This tool cannot and should not be used to bypass DRM
2. **Copyright**: Users are responsible for ensuring legal rights to download content
3. **Public Exposure**: Not designed for public internet exposure without additional security layers

## Recommended Production Setup

```bash
# Use HTTPS with valid SSL certificate
PROTOCOL=https

# Strong credentials
API_KEY=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 24)

# Network restrictions
ALLOWED_ORIGINS=chrome-extension://your-extension-id

# Rate limiting
RATE_LIMIT_PER_MINUTE=10

# Monitoring
LOG_LEVEL=INFO
```

## Security Checklist

Before deploying to production:

- [ ] Change default passwords
- [ ] Generate strong API keys
- [ ] Configure HTTPS with valid certificate
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure proper CORS
- [ ] Review and restrict file system access
- [ ] Set up log monitoring
- [ ] Regular security updates
- [ ] Backup strategy in place

## Contact

For security concerns, please use GitHub Security Advisories feature or contact the maintainers directly.

---

**Last Updated**: 2025-10-12

