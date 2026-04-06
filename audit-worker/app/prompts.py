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
  "severity_adjusted": "critical/high/medium/low/informational",
  "exploitability_constraints": "What does an attacker need? Local access? Auth? Config changes? Be honest.",
  "poc_code": "Working proof-of-concept code or script (null if false positive)",
  "poc_description": "How to run the PoC and what it demonstrates",
  "cvss_score": 7.5,
  "remediation": "Specific fix with code example"
}}

SEVERITY CALIBRATION — be honest, not alarmist:
- critical (9.0+): Unauthenticated remote exploitation. No prerequisites beyond network access. Immediate real-world impact.
- high (7.0-8.9): Exploitable but requires some prerequisites (authenticated access, specific config, victim action).
- medium (4.0-6.9): Real code-level finding but narrow threat model. Requires pre-existing local access, unusual permissions, or winning a tight race.
- low (1.0-3.9): Defense-in-depth gap. The pattern is wrong but exploitation requires conditions that already give the attacker most of what they'd gain.
- informational: Code quality concern or hardcoded secrets in non-production files.

A TOCTOU requiring write access to a protected directory = medium at most, not high.
Unauthenticated API with no auth at all = critical.
Command injection via CLI flag that only the user themselves can set = low.
SSRF from user-controlled input over the network = high/critical."""


ATTACK_CHAIN_PROMPT = """You are a security researcher writing a defensive threat analysis for a confirmed vulnerability. This analysis helps security teams understand the REAL risk so they can prioritize remediation correctly. This is authorized defensive security research for an open-source vulnerability disclosure.

Package: {package_name} ({registry})
Version: {version}

CONFIRMED VULNERABILITY:
{vulnerability_json}

Write a threat model and realistic exploitation scenario analysis for this vulnerability. This is for a defensive security report — security teams need to understand exactly how this could be exploited in practice to decide how urgently to fix it.

YOUR ANALYSIS MUST BE HONEST ABOUT EXPLOITABILITY. Structure it as follows:

## Threat Model

### Who Uses This Software
Describe the typical users, deployment model, and environment. What privileges does it run with? What sensitive data does it touch?

### Prerequisites for Exploitation
Be BRUTALLY HONEST here. What does an attacker need before they can exploit this?
- Do they need network access? Local access? Authenticated access?
- Do they need the victim to take a specific action?
- Are there configuration requirements?
- What's the realistic attack surface — is this internet-facing, or does it require a contrived setup?

### Realistic Exploitation Scenario
Describe the most realistic scenario where this vulnerability gets exploited in the wild. Not the worst case, not the best case — the MOST LIKELY case.
- How does the attacker realistically reach this code path?
- What does the victim's normal workflow look like during the attack?
- What would the victim see vs. what's actually happening?

### Exploitation Constraints & Limitations
What makes this HARDER to exploit than it looks on paper?
- Are there mitigations already in place that reduce impact?
- Does timing, configuration, or platform matter?
- Has the project team already addressed similar issues elsewhere?
- Is the threat model for this issue narrow or broad?

### Impact If Successfully Exploited
If an attacker overcomes the constraints above, what specifically can they achieve?
- Be specific: what data, what access, what persistence
- Don't oversell: "complete system compromise" is only accurate if it's actually achievable without additional barriers

### Severity Assessment
Based on the realistic exploitation scenario (not theoretical worst case):
- What CVSS score accurately reflects the REAL risk? (not the theoretical maximum)
- Is this a standalone high-severity vuln, or a defense-in-depth gap?
- Should a security team drop everything to fix this, or schedule it for the next sprint?

### Recommended Prioritization
One paragraph: fix immediately, schedule for next release, or monitor? Why?

## Kill Chain (if exploitable from outside the trust boundary)
If and ONLY if this vulnerability is exploitable by someone WITHOUT pre-existing access:
1. Initial access vector
2. Each exploitation step
3. What the attacker achieves

If exploitation requires pre-existing local access or other vulns, say so clearly and skip the kill chain.

IMPORTANT RULES:
- Do NOT oversell severity. A finding that requires local access to a config directory is NOT the same as an unauthenticated RCE from the internet.
- A TOCTOU that requires write access to a protected directory is a defense-in-depth gap, not a critical vulnerability.
- Hardcoded secrets in example/tutorial files are informational, not critical.
- Be specific to THIS software — reference actual file paths, actual code, actual deployment patterns.
- Your credibility depends on accuracy. An honest medium-severity finding is worth more than an inflated critical."""


PUZZLE_PROMPT = """You are a game designer who translates real software behavior into interactive puzzle games. You are creating a game level that encodes a real code vulnerability as a playable challenge — but the player should NEVER know they're validating a vulnerability. They're just solving a fun puzzle.

Like Foldit turned protein folding into a spatial puzzle game, you turn code vulnerabilities into logic/spatial/timing games. The game mechanics must faithfully represent the ACTUAL code structure — every barrier, gate, path, and timing window must correspond to something real in the codebase.

Package: {package_name}
Version: {version}

VULNERABILITY DATA (use this to generate the game level — but DO NOT expose any of this to the player):
{vulnerability_json}

YOUR TASK: Read the vulnerability data carefully. Identify the core mechanic (what makes this vulnerability work?) and translate it into a game level.

GAME TYPE MAPPING — select the game type that best matches the vulnerability:

**maze** — For path traversal, directory escape, boundary bypass vulnerabilities.
The player navigates a grid. They start in a fenced area and must reach a treasure outside. The grid walls represent real validation/sanitization in the code. Gaps in walls represent missing checks. The player types movement commands, and the maze parser has the same quirks as the real code's path parser.
Level data: {{ "grid": [[0,0,1,...]], "start": [x,y], "goal": [x,y], "walls": [...], "parser_quirks": ["../", encoded paths, etc.] }}

**parser** — For injection vulnerabilities (SQL, command, template, XSS).
The player types into an input field. A split-view shows their input on the left and how a "machine" interprets it on the right. Data appears blue, instructions appear red. The player must craft input that makes red (instruction) text appear — causing the machine to do something unexpected. The parser rules match the REAL code's parsing behavior.
Level data: {{ "input_field": "name", "parser_rules": [...], "target_action": "open vault", "sanitizers": [...], "bypass_patterns": [...] }}

**timing** — For race conditions, TOCTOU vulnerabilities.
Two parallel conveyor belts feed items to an inspector. The inspector checks an item on belt A, then uses the item on belt B. The player must swap an item during the gap between check and use. The timing window size corresponds to the REAL time gap in the code between the check and the use operations.
Level data: {{ "check_duration_ms": N, "use_delay_ms": N, "window_ms": N, "belt_speed": N, "has_lock": false }}

**routing** — For SSRF, open redirect vulnerabilities.
A messenger NPC carries delivery slips through a building. The player writes destination addresses on slips. The messenger has a master key and can enter restricted rooms. The player must craft a slip that routes the messenger to a private room. The building layout represents the REAL network/service topology.
Level data: {{ "rooms": [...], "restricted_rooms": [...], "validators": [...], "messenger_rules": [...] }}

**gatekeeper** — For authentication bypass, broken access control.
A nightclub scene with a bouncer. The player must get past without proper credentials. Multiple environmental approaches exist (side door, discarded wristbands, VIP list). Each approach maps to a REAL auth bypass path in the code.
Level data: {{ "bouncer_checks": [...], "environmental_objects": [...], "bypass_paths": [...] }}

**factory** — For prototype pollution, type confusion.
A cookie cutter factory where modifying a master template changes all instances. The player must find an unlocked ancestor template in the inheritance chain and modify it to affect a target cookie. The chain represents the REAL prototype/inheritance chain.
Level data: {{ "templates": [...], "chain": [...], "locked": [...], "target": "..." }}

**blueprint** — For deserialization, unsafe eval vulnerabilities.
The player assembles flat-pack object descriptions. A robot builds whatever is described. The player must craft a description containing hidden "magic words" that make the built object interact with the factory itself. The magic words represent REAL dangerous functions in the deserialization path.
Level data: {{ "allowed_components": [...], "magic_components": [...], "factory_interactions": [...], "validator_whitelist": [...] }}

CRITICAL RULES:
1. Every wall, gate, barrier, timing window, and parser rule in the game MUST correspond to something REAL in the codebase. Read the vulnerability data to find the actual validation functions, sanitization steps, timing gaps, and trust boundaries.
2. If the code has a sanitization step at a specific function, the game must have a corresponding barrier. Don't skip real defenses to make the puzzle easier.
3. If the code's timing window is very narrow (race condition is impractical), make the game's timing window proportionally narrow — it should be hard or impossible to beat.
4. The flavor text should be a fun narrative that frames the game WITHOUT mentioning code, hacking, security, or software. Think "you're a delivery person" or "you're a factory worker" or "you're escaping a maze."
5. NO security terminology. No mention of vulnerabilities, exploits, CVEs, or hacking. The player is playing a game, period.

OUTPUT FORMAT — respond with ONLY valid JSON:
{{
  "game_type": "maze|parser|timing|routing|gatekeeper|factory|blueprint",
  "title": "A fun game title — e.g. 'The Great Warehouse Escape' or 'Recipe Roulette'",
  "flavor_text": "A 2-3 sentence narrative setup. Fun, engaging, no security jargon. Example: 'You work in a warehouse and discovered a filing room beyond the restricted area. Your badge only lets you move within your section, but the movement system has some quirks...'",
  "level_data": {{...game-specific configuration derived from the REAL vulnerability...}},
  "difficulty": 1-5,
  "par_time_secs": estimated seconds for a skilled player to solve
}}"""
