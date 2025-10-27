---
name: security-input-validation
description: Input validation and sanitization patterns to prevent SQL injection, XSS, command injection, and other input-based attacks
---

# Security: Input Validation

**Scope**: Input validation, sanitization, SQL injection prevention, XSS protection, command injection
**Lines**: ~400
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Processing user input in web applications or APIs
- Preventing SQL injection, XSS, or command injection attacks
- Validating and sanitizing form data
- Building input validation schemas
- Implementing file upload security
- Preventing path traversal attacks
- Designing secure data processing pipelines

## Input Validation Fundamentals

### Defense in Depth

```python
"""
Multi-layer validation strategy:
1. Client-side: UX feedback (not security)
2. Schema validation: Type and format checking
3. Business logic: Domain-specific rules
4. Sanitization: Clean dangerous content
5. Encoding: Context-specific output encoding
"""

from pydantic import BaseModel, validator, Field

class UserInput(BaseModel):
    """Layer 1: Schema validation"""
    username: str = Field(min_length=3, max_length=32)
    email: str
    age: int = Field(ge=18, le=120)

    @validator('username')
    def validate_username(cls, v):
        """Layer 2: Business logic validation"""
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

    @validator('email')
    def validate_email(cls, v):
        """Layer 2: Email format validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v

def process_user_input(data: dict):
    """Layer 3: Sanitization before use"""
    validated = UserInput(**data)

    # Layer 4: Context-specific encoding (when outputting)
    safe_username = html.escape(validated.username)

    return validated
```

## SQL Injection Prevention

### Vulnerable Code Examples

```python
import sqlite3

# ❌ NEVER DO THIS - SQL Injection vulnerable
def get_user_vulnerable(username: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Attacker input: "admin' OR '1'='1"
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)

    return cursor.fetchone()

# Attack payload: username = "admin' OR '1'='1"
# Result: Returns all users (bypasses authentication)

# ❌ ALSO VULNERABLE - String concatenation
def delete_user_vulnerable(user_id: str):
    query = "DELETE FROM users WHERE id = " + user_id
    cursor.execute(query)

# Attack payload: user_id = "1 OR 1=1"
# Result: Deletes all users
```

### Secure Code (Parameterized Queries)

```python
# ✅ CORRECT - Parameterized queries (prepared statements)
def get_user_safe(username: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Database driver handles escaping
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))

    return cursor.fetchone()

# ✅ CORRECT - Named parameters
def get_user_by_email(email: str):
    query = "SELECT * FROM users WHERE email = :email"
    cursor.execute(query, {"email": email})
    return cursor.fetchone()

# ✅ CORRECT - Multiple parameters
def create_user(username: str, email: str, age: int):
    query = """
        INSERT INTO users (username, email, age)
        VALUES (?, ?, ?)
    """
    cursor.execute(query, (username, email, age))
    conn.commit()
```

### ORM Usage (Automatically Safe)

```python
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(100))

engine = create_engine('sqlite:///users.db')
Session = sessionmaker(bind=engine)
session = Session()

# ✅ ORM automatically uses parameterized queries
def get_user_by_username(username: str):
    return session.query(User).filter(User.username == username).first()

# ✅ Safe even with complex queries
def search_users(search_term: str):
    return session.query(User).filter(
        User.username.like(f"%{search_term}%")
    ).all()  # ORM handles escaping
```

### Dynamic Queries (Be Careful)

```python
# ⚠️ When you must build dynamic queries
def search_with_filters(filters: dict):
    """Safe dynamic query construction"""
    query = "SELECT * FROM users WHERE 1=1"
    params = []

    # Whitelist allowed columns
    ALLOWED_COLUMNS = {'username', 'email', 'age', 'created_at'}

    for column, value in filters.items():
        # Validate column name against whitelist
        if column not in ALLOWED_COLUMNS:
            raise ValueError(f"Invalid column: {column}")

        # Use parameterized queries for values
        query += f" AND {column} = ?"  # Column name is whitelisted
        params.append(value)  # Value is parameterized

    cursor.execute(query, tuple(params))
    return cursor.fetchall()
```

## Cross-Site Scripting (XSS) Prevention

### Types of XSS

```python
# Reflected XSS - Input immediately reflected in response
@app.get("/search")
def search(q: str):
    # ❌ VULNERABLE
    return f"<h1>Search results for: {q}</h1>"

    # Attack: q = "<script>alert('XSS')</script>"
    # Result: Script executes in user's browser

# Stored XSS - Malicious input stored in database
@app.post("/comments")
def create_comment(content: str):
    # ❌ VULNERABLE - Stores unsanitized input
    db.execute("INSERT INTO comments (content) VALUES (?)", (content,))

    # Later, when displayed:
    # return f"<p>{comment.content}</p>"  # Script executes

# DOM-based XSS - Client-side JavaScript manipulation
# ❌ VULNERABLE JavaScript
document.getElementById('output').innerHTML = userInput;
```

### XSS Prevention Strategies

```python
import html
from markupsafe import escape
from bleach import clean

# Strategy 1: HTML Escaping (for text content)
def display_user_content_safe(content: str) -> str:
    """✅ Escape HTML entities"""
    return html.escape(content)

# Input: "<script>alert('XSS')</script>"
# Output: "&lt;script&gt;alert('XSS')&lt;/script&gt;"
# Displayed as text, not executed

# Strategy 2: Allowlist-based Sanitization (for rich text)
def sanitize_html(content: str) -> str:
    """✅ Allow only safe HTML tags"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
    allowed_attrs = {'a': ['href', 'title']}

    return clean(
        content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True  # Remove disallowed tags
    )

# Strategy 3: Content Security Policy (CSP)
from flask import Flask, make_response

app = Flask(__name__)

@app.after_request
def add_security_headers(response):
    """✅ Add CSP header"""
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.example.com; "
        "style-src 'self' 'unsafe-inline';"
    )
    return response

# Strategy 4: Template Auto-escaping
from jinja2 import Environment, select_autoescape

env = Environment(autoescape=select_autoescape(['html', 'xml']))

# ✅ Jinja2 automatically escapes variables
template = env.from_string("<p>{{ user_input }}</p>")
safe_html = template.render(user_input="<script>alert('XSS')</script>")
# Output: "<p>&lt;script&gt;alert('XSS')&lt;/script&gt;</p>"
```

### Framework-Specific XSS Prevention

```python
# FastAPI with Jinja2 (auto-escaping enabled)
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates", autoescape=True)

@app.get("/profile")
def profile(request: Request, user_id: int):
    user = get_user(user_id)

    # ✅ Template auto-escapes user.bio
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user
    })

# React (auto-escaping)
# ✅ React escapes by default
function UserProfile({ username }) {
  return <div>{username}</div>;  // Automatically escaped
}

# ❌ Dangerous - dangerouslySetInnerHTML
function VulnerableComponent({ html }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;  // XSS risk
}

# ✅ Use sanitization library
import DOMPurify from 'dompurify';

function SafeComponent({ html }) {
  const clean = DOMPurify.sanitize(html);
  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

## Command Injection Prevention

### Vulnerable Code

```python
import os
import subprocess

# ❌ NEVER DO THIS - Command injection vulnerable
def ping_host_vulnerable(hostname: str):
    command = f"ping -c 4 {hostname}"
    os.system(command)

# Attack: hostname = "google.com; rm -rf /"
# Result: Deletes files after ping

# ❌ ALSO VULNERABLE - shell=True
def backup_file_vulnerable(filename: str):
    subprocess.call(f"tar -czf backup.tar.gz {filename}", shell=True)

# Attack: filename = "data.txt; cat /etc/passwd"
# Result: Leaks sensitive files
```

### Safe Code

```python
import subprocess
import shlex
from pathlib import Path

# ✅ CORRECT - Use list arguments (no shell)
def ping_host_safe(hostname: str):
    """Safe command execution"""
    # Validate hostname format
    if not is_valid_hostname(hostname):
        raise ValueError("Invalid hostname")

    # Use list of arguments (no shell interpretation)
    result = subprocess.run(
        ["ping", "-c", "4", hostname],
        shell=False,  # Critical: Don't use shell
        capture_output=True,
        text=True,
        timeout=5
    )

    return result.stdout

def is_valid_hostname(hostname: str) -> bool:
    """Validate hostname format"""
    import re
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return re.match(pattern, hostname) is not None

# ✅ CORRECT - Avoid shell entirely
def compress_file_safe(filename: str):
    """Safe file compression"""
    # Validate filename (no path traversal)
    safe_filename = Path(filename).name

    if not safe_filename or safe_filename.startswith('.'):
        raise ValueError("Invalid filename")

    # Use Python libraries instead of shell commands
    import tarfile

    with tarfile.open("backup.tar.gz", "w:gz") as tar:
        tar.add(safe_filename)

# ✅ If shell is unavoidable, use shlex.quote()
def run_with_shell_safe(user_input: str):
    """Escape shell metacharacters"""
    safe_input = shlex.quote(user_input)
    command = f"echo {safe_input}"

    subprocess.run(command, shell=True)  # Now safe (but avoid if possible)
```

## Path Traversal Prevention

### Vulnerable Code

```python
from flask import send_file

# ❌ VULNERABLE - Path traversal
@app.get("/download")
def download_file(filename: str):
    return send_file(f"/uploads/{filename}")

# Attack: filename = "../../etc/passwd"
# Result: Leaks system files
```

### Safe Code

```python
from pathlib import Path
from flask import send_file, abort

UPLOAD_DIR = Path("/var/app/uploads").resolve()

@app.get("/download")
def download_file_safe(filename: str):
    """✅ Prevent path traversal"""

    # Resolve full path
    requested_path = (UPLOAD_DIR / filename).resolve()

    # Check if path is within allowed directory
    if not str(requested_path).startswith(str(UPLOAD_DIR)):
        abort(403, "Forbidden")

    # Check if file exists
    if not requested_path.is_file():
        abort(404, "File not found")

    # Whitelist allowed extensions
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.png', '.txt'}
    if requested_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        abort(403, "File type not allowed")

    return send_file(requested_path)
```

## File Upload Security

### Secure File Upload Implementation

```python
from werkzeug.utils import secure_filename
import magic  # python-magic library
from pathlib import Path
import uuid

UPLOAD_FOLDER = Path("/var/app/uploads")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/gif'
}

def validate_file_upload(file) -> Path:
    """Comprehensive file upload validation"""

    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset

    if size > MAX_FILE_SIZE:
        raise ValueError("File too large")

    # Sanitize filename
    original_filename = secure_filename(file.filename)

    if not original_filename:
        raise ValueError("Invalid filename")

    # Validate extension
    extension = Path(original_filename).suffix.lower()[1:]
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type not allowed: {extension}")

    # Verify MIME type (don't trust extension)
    file_content = file.read(2048)  # Read first 2KB
    file.seek(0)  # Reset

    mime_type = magic.from_buffer(file_content, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Invalid file content: {mime_type}")

    # Generate unique filename (prevent overwrites)
    unique_filename = f"{uuid.uuid4()}.{extension}"
    save_path = UPLOAD_FOLDER / unique_filename

    # Save file
    file.save(save_path)

    # Set restrictive permissions
    save_path.chmod(0o644)

    return save_path

@app.post("/upload")
def upload_file():
    """✅ Secure file upload endpoint"""
    if 'file' not in request.files:
        return {"error": "No file provided"}, 400

    file = request.files['file']

    try:
        save_path = validate_file_upload(file)
        return {"filename": save_path.name}, 200
    except ValueError as e:
        return {"error": str(e)}, 400
```

## Input Validation Patterns

### Schema Validation (Pydantic)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str
    password: str = Field(min_length=12)
    age: Optional[int] = Field(None, ge=18, le=120)
    website: Optional[str] = None

    @validator('username')
    def validate_username(cls, v):
        """Alphanumeric and underscore only"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric')
        return v

    @validator('email')
    def validate_email(cls, v):
        """Email format validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        """Password complexity"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain special character')
        return v

    @validator('website')
    def validate_website(cls, v):
        """URL validation"""
        if v is None:
            return v

        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        if not re.match(url_pattern, v):
            raise ValueError('Invalid URL')
        return v

# Usage
@app.post("/users")
def create_user(user: CreateUserRequest):
    # Pydantic automatically validates
    # If validation fails, returns 422 Unprocessable Entity
    return create_user_in_db(user)
```

### Whitelist Validation

```python
from enum import Enum

class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"

class SortField(Enum):
    NAME = "name"
    EMAIL = "email"
    CREATED_AT = "created_at"

@app.get("/users")
def list_users(
    sort_by: SortField = SortField.CREATED_AT,
    order: SortOrder = SortOrder.DESC,
    limit: int = Field(10, ge=1, le=100)
):
    """✅ Enum validation prevents SQL injection"""

    # Enums ensure only valid values
    query = f"""
        SELECT * FROM users
        ORDER BY {sort_by.value} {order.value}
        LIMIT {limit}
    """

    # Safe because sort_by and order are validated enums
    return db.execute(query)
```

## Security Best Practices

### Input Validation Checklist

**General**:
- [ ] Validate all inputs (including headers, cookies, query params)
- [ ] Use allowlists over blocklists
- [ ] Validate on server-side (never trust client)
- [ ] Fail securely (reject invalid input)
- [ ] Log validation failures

**SQL Injection Prevention**:
- [ ] Always use parameterized queries
- [ ] Use ORM when possible
- [ ] Validate column/table names with whitelist
- [ ] Escape dynamic SQL (last resort)
- [ ] Use least-privilege database accounts

**XSS Prevention**:
- [ ] Enable template auto-escaping
- [ ] Use Content Security Policy (CSP)
- [ ] Sanitize rich text with allowlist
- [ ] Set X-XSS-Protection header
- [ ] Use httpOnly and secure cookies

**Command Injection Prevention**:
- [ ] Avoid shell execution (use libraries)
- [ ] Never use shell=True with user input
- [ ] Use subprocess with list arguments
- [ ] Validate all arguments
- [ ] Use shlex.quote() as last resort

**File Upload Security**:
- [ ] Validate file size
- [ ] Verify MIME type (not just extension)
- [ ] Use secure_filename()
- [ ] Generate unique filenames
- [ ] Store outside web root
- [ ] Set restrictive permissions

## Related Skills

- `security-authentication.md` - Validating authentication credentials
- `security-authorization.md` - Validating authorization inputs
- `security-headers.md` - CSP and other protective headers
- `api-error-handling.md` - Handling validation errors

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
