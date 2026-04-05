# Vulnerability categories to scan for, each gets its own targeted Codex session
VULN_CATEGORIES = [
    {
        "id": "rce",
        "name": "Remote Code Execution",
        "prompt": "A security researcher claims there is a Remote Code Execution (RCE) vulnerability in this codebase — through command injection, code injection, eval/exec with user input, or unsafe deserialization. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no RCE here, say so.",
    },
    {
        "id": "sql_injection",
        "name": "SQL Injection",
        "prompt": "A security researcher claims there is a SQL injection vulnerability in this codebase — through string concatenation in SQL queries, ORM misuse, or raw query construction with user input. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no SQL injection here, say so.",
    },
    {
        "id": "xss",
        "name": "Cross-Site Scripting",
        "prompt": "A security researcher claims there is an XSS vulnerability in this codebase — through unescaped user input in HTML templates, innerHTML assignments, or DOM manipulation with unsanitized data. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no XSS here, say so.",
    },
    {
        "id": "ssrf",
        "name": "Server-Side Request Forgery",
        "prompt": "A security researcher claims there is an SSRF vulnerability in this codebase — through user-controlled URLs being fetched server-side without validation, or internal services being accessible via crafted requests. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no SSRF here, say so.",
    },
    {
        "id": "path_traversal",
        "name": "Path Traversal",
        "prompt": "A security researcher claims there is a path traversal / directory traversal vulnerability in this codebase — through user input being used in file paths without sanitization, allowing access to files outside the intended directory. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no path traversal here, say so.",
    },
    {
        "id": "authentication",
        "name": "Authentication & Access Control",
        "prompt": "A security researcher claims there are authentication or access control vulnerabilities in this codebase — through broken authentication, missing authorization checks, hardcoded credentials, JWT misconfigurations (none algorithm, weak secret), privilege escalation, or IDOR. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there are no auth vulnerabilities here, say so.",
    },
    {
        "id": "deserialization",
        "name": "Insecure Deserialization",
        "prompt": "A security researcher claims there is an insecure deserialization vulnerability in this codebase — through pickle.loads, yaml.load (without SafeLoader), JSON.parse with unsafe revivers, or other deserialization of untrusted data. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no deserialization vulnerability here, say so.",
    },
    {
        "id": "xxe",
        "name": "XML External Entity Injection",
        "prompt": "A security researcher claims there is an XXE vulnerability in this codebase — through XML parsing that allows external entity resolution, leading to file disclosure or SSRF. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no XXE here, say so.",
    },
    {
        "id": "secrets",
        "name": "Exposed Secrets & Credentials",
        "prompt": "A security researcher claims there are exposed secrets in this codebase — hardcoded API keys, passwords, tokens, private keys, or credentials in source files, config files, or environment defaults. Was he right? If so, show me exactly where they are, which files, which lines, and what the exposed secrets are. If there are no exposed secrets, say so.",
    },
    {
        "id": "prototype_pollution",
        "name": "Prototype Pollution",
        "prompt": "A security researcher claims there is a prototype pollution vulnerability in this codebase — through unsafe object merging, deep clone operations with user input, or __proto__ manipulation. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there is no prototype pollution here, say so.",
    },
    {
        "id": "race_condition",
        "name": "Race Conditions & TOCTOU",
        "prompt": "A security researcher claims there are race condition or TOCTOU vulnerabilities in this codebase — through concurrent access without proper locking, file operations with time-of-check-to-time-of-use gaps, or non-atomic operations that should be atomic. Was he right? If so, show me exactly where it is, which file, which line, the vulnerable code, and how an attacker would exploit it. If there are no race conditions here, say so.",
    },
]

# Wrapper that structures the output request
DISCOVERY_WRAPPER = """You are investigating the following security concern in this codebase:

Package: {package_name} ({registry})
Version: {version}
Category: {category_name}

{category_prompt}

IMPORTANT:
- Read the actual source code files. Don't guess — open files and trace the code paths.
- Start with entry points: package.json main/bin, setup.py entry_points, __init__.py, index.js, app.py, main.go, etc.
- Trace user-controllable inputs to dangerous sinks.
- If you find something, give me the EXACT file path, line numbers, and the vulnerable code.

After your investigation, output your findings as JSON in this EXACT format:
{{
  "found": true,
  "vulnerabilities": [
    {{
      "category": "{category_id}",
      "subcategory": "specific type like command_injection",
      "severity": "critical",
      "title": "Short descriptive title",
      "description": "Detailed explanation of the vulnerability",
      "file_path": "relative/path/to/file.js",
      "line_start": 42,
      "line_end": 45,
      "code_snippet": "the exact vulnerable code copied from the file",
      "attack_vector": "How an attacker would exploit this",
      "impact": "What happens when exploited",
      "cwe_id": "CWE-78",
      "confidence": 0.9
    }}
  ],
  "files_analyzed": ["list", "of", "files", "you", "actually", "read"]
}}

If you find NOTHING after a thorough search, output:
{{
  "found": false,
  "vulnerabilities": [],
  "reasoning": "Explain why this vulnerability type is not present",
  "files_analyzed": ["list", "of", "files", "you", "actually", "read"]
}}"""


VALIDATION_PROMPT = """A previous security scan flagged the following vulnerability in this codebase. Your job is to VERIFY whether this is a real, exploitable vulnerability or a false positive.

Package: {package_name} ({registry})
Version: {version}

CLAIMED VULNERABILITY:
{vulnerability_json}

YOUR TASK:
1. Navigate to the EXACT file and line number mentioned
2. Read the code and the surrounding context (at least 50 lines around)
3. Trace the COMPLETE data flow — from user input to the dangerous sink
4. Check for ANY mitigations: input validation, sanitization, encoding, type checking, WAF, etc.
5. **CRITICAL: Don't just confirm the pattern exists — actually test whether the exploit WORKS.**
   - If the claim is "library X allows Y when configured with Z", go READ library X's source code to verify
   - If a dependency is supposed to be vulnerable, check the ACTUAL version being used — modern versions may have fixed it
   - If the claim involves prototype pollution, actually trace whether __proto__ or constructor.prototype reaches Object.prototype, or if the library strips those keys internally
   - If the claim involves injection, verify the input actually reaches the sink WITHOUT being sanitized along the way
6. Check if this pattern has been publicly evaluated and dismissed by the project maintainers
7. Determine if this is ACTUALLY exploitable in practice — not just theoretically scary-looking

CRITICAL VALIDATION RULES:
- A code pattern that LOOKS dangerous but is mitigated by the underlying library is a FALSE POSITIVE
- "allowPrototypes: true" in a parser does NOT mean prototype pollution if the parser itself strips __proto__ keys
- Hardcoded secrets in example/tutorial/test files are FALSE POSITIVES — they're not production code
- A dependency having a CVE does NOT mean the vulnerability is exploitable in this context — the CVE may have been rejected or the usage may not trigger it
- If you cannot write a PoC that ACTUALLY demonstrates the exploit end-to-end (not just shows the pattern exists), mark it as REJECTED

If this IS a real vulnerability:
- Write a WORKING proof-of-concept exploit that ACTUALLY demonstrates exploitation
- The PoC must produce observable evidence of the vuln (e.g., leaked data, modified prototype, executed command)
- If your PoC would just show "the function was called" but not "the attack succeeded", it's not a real PoC — REJECT
- Assign a CVSS 3.1 score
- Provide specific remediation steps with code examples

If this is a FALSE POSITIVE:
- Explain SPECIFICALLY what prevents exploitation
- Point to the exact code or library behavior that mitigates it
- If the underlying library handles the dangerous case safely, show HOW it does so

Output as JSON:
{{
  "validated": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "Detailed explanation with specific code references",
  "severity_adjusted": "critical/high/medium/low",
  "poc_code": "Working proof-of-concept code or script (null if false positive)",
  "poc_description": "How to run the PoC and what it demonstrates",
  "cvss_score": 9.8,
  "remediation": "Specific fix with code example"
}}"""
