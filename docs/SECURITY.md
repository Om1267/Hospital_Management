# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Yes    |

## Reporting a Vulnerability

If you discover a security vulnerability, please do NOT open a public GitHub issue.

Instead, please email the maintainer directly or use GitHub's private security advisory feature.

## Security Features

- **CSRF Protection**: All POST forms are protected with Flask-WTF CSRF tokens
- **Password Hashing**: All passwords are hashed using Werkzeug's generate_password_hash
- **Role-Based Access Control**: Admin, Doctor, and Nurse roles with route-level restrictions
- **Session Management**: Secure session handling via Flask-Login
- **Input Validation**: Server-side validation on all user inputs
- **SQL Injection Prevention**: ORM-based queries via SQLAlchemy (no raw SQL)

## Best Practices for Deployment

1. Always set SECRET_KEY to a long, random string
2. Set DEBUG=False in production
3. Use HTTPS in production
4. Regularly back up the database
5. Keep all dependencies updated
