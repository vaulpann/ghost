# Critical Open Source Vulnerabilities: Mid-2025 to Early 2026

**Compiled: April 2, 2026**
**Scope:** Confirmed, validated, and patched vulnerabilities in widely-used open source projects

---

## Table of Contents

1. [CVE-2025-55182 -- React2Shell: React Server Components RCE](#1-cve-2025-55182--react2shell-react-server-components-rce)
2. [CVE-2025-29927 -- Next.js Middleware Authorization Bypass](#2-cve-2025-29927--nextjs-middleware-authorization-bypass)
3. [CVE-2025-1974 -- IngressNightmare: Kubernetes Ingress-NGINX RCE](#3-cve-2025-1974--ingressnightmare-kubernetes-ingress-nginx-rce)
4. [CVE-2025-30066 -- tj-actions/changed-files GitHub Actions Supply Chain Compromise](#4-cve-2025-30066--tj-actionschanged-files-github-actions-supply-chain-compromise)
5. [CVE-2025-30154 -- reviewdog/action-setup GitHub Actions Supply Chain Compromise](#5-cve-2025-30154--reviewdogaction-setup-github-actions-supply-chain-compromise)
6. [CVE-2025-30065 -- Apache Parquet Java Deserialization RCE](#6-cve-2025-30065--apache-parquet-java-deserialization-rce)
7. [CVE-2025-3248 -- Langflow Unauthenticated RCE via Code Injection](#7-cve-2025-3248--langflow-unauthenticated-rce-via-code-injection)
8. [CVE-2026-33017 -- Langflow Unauthenticated RCE (Second Occurrence)](#8-cve-2026-33017--langflow-unauthenticated-rce-second-occurrence)
9. [CVE-2025-34291 -- Langflow CORS/CSRF Chain to Account Takeover and RCE](#9-cve-2025-34291--langflow-corscrsf-chain-to-account-takeover-and-rce)
10. [CVE-2025-68613 -- n8n Expression Injection RCE](#10-cve-2025-68613--n8n-expression-injection-rce)
11. [CVE-2025-54313 -- eslint-config-prettier Supply Chain Compromise](#11-cve-2025-54313--eslint-config-prettier-supply-chain-compromise)
12. [CVE-2025-27407 -- graphql-ruby RCE via Malicious Schema Loading](#12-cve-2025-27407--graphql-ruby-rce-via-malicious-schema-loading)
13. [CVE-2025-25291 / CVE-2025-25292 -- ruby-saml SAML Authentication Bypass](#13-cve-2025-25291--cve-2025-25292--ruby-saml-saml-authentication-bypass)
14. [CVE-2025-27520 -- BentoML Insecure Deserialization RCE](#14-cve-2025-27520--bentoml-insecure-deserialization-rce)
15. [CVE-2025-27607 -- python-json-logger Dependency Hijacking RCE](#15-cve-2025-27607--python-json-logger-dependency-hijacking-rce)
16. [CVE-2025-68664 -- LangGrinch: LangChain Core Serialization Injection](#16-cve-2025-68664--langgrinch-langchain-core-serialization-injection)
17. [CVE-2025-64439 -- LangGraph Checkpoint Deserialization RCE](#17-cve-2025-64439--langgraph-checkpoint-deserialization-rce)
18. [CVE-2025-31125 -- Vite Arbitrary File Read via server.fs.deny Bypass](#18-cve-2025-31125--vite-arbitrary-file-read-via-serverfsdeny-bypass)
19. [CVE-2025-62518 -- TARmageddon: Rust async-tar/tokio-tar RCE](#19-cve-2025-62518--tarmageddon-rust-async-tartokio-tar-rce)
20. [Shai-Hulud / CVE-2026-34841 -- npm Self-Replicating Worm and Axios Supply Chain Attack](#20-shai-hulud--cve-2026-34841--npm-self-replicating-worm-and-axios-supply-chain-attack)

---

## 1. CVE-2025-55182 -- React2Shell: React Server Components RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-55182 (related: CVE-2025-66478 for Next.js downstream impact, later deduplicated) |
| **Package/Project** | React (react-server-dom-webpack, react-server-dom-parcel, react-server-dom-turbopack) |
| **Ecosystem** | npm |
| **Severity** | **CVSS 10.0 (Critical)** |
| **CWE** | CWE-502 (Deserialization of Untrusted Data) |
| **Affected Versions** | React 19.0.0, 19.1.0, 19.1.1, 19.2.0 |
| **Patched Versions** | React 19.0.1, 19.1.2, 19.2.1; Next.js 15.0.5+ |
| **Discovered** | November 29, 2025 (disclosed to Meta) |
| **Patched** | December 3, 2025 |
| **Discoverer** | Lachlan Davidson |

### Technical Description

React2Shell is a pre-authentication remote code execution vulnerability caused by insecure deserialization within the React Server Components (RSC) architecture, specifically in the RSC "Flight" protocol. The flaw allows arbitrary server-side code execution by exploiting the `$@` self-reference mechanism and prototype chain traversal to access the global `Function` constructor. An attacker can achieve RCE via a single malicious HTTP request -- no authentication required.

### Exploitation

An attacker crafts a malicious Flight protocol payload that, when deserialized by the server, traverses the prototype chain to gain access to the `Function` constructor, enabling arbitrary code execution. Exploitation was detected in the wild by December 5, 2025 -- approximately 30 hours after public disclosure. Multiple threat actor groups (including China-nexus groups per AWS reporting) were observed exploiting the flaw, with the majority deploying coin miners, though more sophisticated payloads were also observed.

### Fix/Patch Details

The React team patched the Flight protocol deserialization logic to prevent prototype chain traversal and restrict the types of objects that can be constructed during deserialization. Patched versions: react-server-dom-webpack, react-server-dom-parcel, and react-server-dom-turbopack 19.0.1, 19.1.2, 19.2.1. For Next.js users: `npm install next@15.0.5` or the `npx fix-react2shell-next` automated tool.

---

## 2. CVE-2025-29927 -- Next.js Middleware Authorization Bypass

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-29927 |
| **Package/Project** | Next.js |
| **Ecosystem** | npm |
| **Severity** | **CVSS 9.1 (Critical)** |
| **CWE** | CWE-284 (Improper Access Control) |
| **Affected Versions** | All Next.js < 12.3.5, < 13.5.9, < 14.2.25, < 15.2.3 |
| **Patched Versions** | 12.3.5, 13.5.9, 14.2.25, 15.2.3 |
| **Discovered** | March 2025 |
| **Patched** | March 21, 2025 |
| **Discoverer** | Rachid Allam (Zhero Web Security), also credited: Yaser Alam |

### Technical Description

The vulnerability stems from improper trust of the `x-middleware-subrequest` HTTP header, which Next.js uses internally to prevent infinite middleware recursion loops. If this header is present with a specific value, the middleware execution is skipped entirely and the request is forwarded directly to its destination -- bypassing all middleware-based authentication and authorization checks.

### Exploitation

Trivially exploitable. An attacker adds the header `x-middleware-subrequest: middleware:middleware:middleware:middleware:middleware` to any HTTP request, causing the framework to skip all middleware logic. This bypasses authentication, authorization, rate limiting, and any other security controls implemented in Next.js middleware. Only self-hosted deployments were affected; Vercel and Netlify cloud deployments were not vulnerable.

### Fix/Patch Details

The patch verifies that the `x-middleware-subrequest` header is legitimate and originates from the framework itself, not from an external request. The header is now validated server-side and cannot be spoofed by external clients.

---

## 3. CVE-2025-1974 -- IngressNightmare: Kubernetes Ingress-NGINX RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-1974 (family includes CVE-2025-1097, CVE-2025-1098, CVE-2025-24514) |
| **Package/Project** | ingress-nginx (Kubernetes Ingress Controller) |
| **Ecosystem** | Kubernetes / Go |
| **Severity** | **CVSS 9.8 (Critical)** |
| **CWE** | CWE-94 (Code Injection) |
| **Affected Versions** | ingress-nginx < 1.11.5, < 1.12.1 |
| **Patched Versions** | 1.11.5, 1.12.1 |
| **Discovered** | December 31, 2024 (reported privately) |
| **Patched** | March 24, 2025 (public disclosure) |
| **Discoverer** | Wiz Research (Nir Ohfeld, Ronen Shustin, Sagi Tzadik, Hillai Ben-Sasson) |

### Technical Description

Part of the "IngressNightmare" vulnerability family. The vulnerability allows unauthenticated remote code execution via the Validating Admission Controller of ingress-nginx. The `uid` field from an Ingress Object is directly inserted into the NGINX configuration template, creating a configuration injection point. An attacker on the pod network can send a crafted Ingress object directly to the admission controller, injecting arbitrary NGINX directives that lead to RCE.

### Exploitation

An attacker with network access to the admission webhook (often exposed to the entire pod network, and in 6,500+ clusters publicly exposed to the internet) can craft a malicious Ingress object with injected NGINX configuration directives. Because ingress-nginx typically has access to all Secrets cluster-wide, successful exploitation leads to complete cluster takeover. Wiz estimated ~43% of cloud environments were vulnerable.

### Fix/Patch Details

Upgrade to ingress-nginx v1.11.5 or v1.12.1+. The patch sanitizes the `uid` field and other injectable configuration parameters. If immediate upgrade is not possible, disable the Validating Admission Controller feature.

---

## 4. CVE-2025-30066 -- tj-actions/changed-files GitHub Actions Supply Chain Compromise

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-30066 |
| **Package/Project** | tj-actions/changed-files (GitHub Action) |
| **Ecosystem** | GitHub Actions |
| **Severity** | **High (CVSS 8.6)** |
| **CWE** | CWE-506 (Embedded Malicious Code) |
| **Affected Versions** | All versions (all tags were retroactively modified) |
| **Patched Versions** | v46.0.1 |
| **Discovered** | March 14, 2025 (by StepSecurity) |
| **Patched** | March 15, 2025 |
| **Discoverer** | StepSecurity |

### Technical Description

An attacker compromised a GitHub Personal Access Token (PAT) used by a bot account with write access to the tj-actions/changed-files repository. The attacker then modified all existing version tags to point to malicious code, meaning every version of the action was compromised simultaneously. The injected code executed a Python script that extracted secrets from the GitHub Actions Runner Worker process memory and printed them to build logs.

### Exploitation

Any CI/CD workflow using tj-actions/changed-files (over 23,000 repositories) would execute the malicious code during workflow runs. For repositories with public workflow logs, extracted secrets (GitHub PATs, npm tokens, AWS keys, RSA private keys) were visible in plaintext. The attack originated from the compromise of reviewdog/action-setup (CVE-2025-30154), which was used to pivot to the tj-actions compromise.

### Fix/Patch Details

The maintainer revoked the compromised PAT, removed the malicious code, and published v46.0.1 as a clean release. Organizations should rotate all secrets that may have been exposed in workflow logs during the March 14-15 window. Pin GitHub Actions to specific commit SHAs rather than tags.

---

## 5. CVE-2025-30154 -- reviewdog/action-setup GitHub Actions Supply Chain Compromise

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-30154 |
| **Package/Project** | reviewdog/action-setup (GitHub Action) |
| **Ecosystem** | GitHub Actions |
| **Severity** | **High** |
| **CWE** | CWE-506 (Embedded Malicious Code) |
| **Affected Versions** | v1 tag (March 11, 2025 18:42-20:31 UTC) |
| **Patched Versions** | Reverted after ~2 hours |
| **Discovered** | March 11, 2025 |
| **Patched** | March 11, 2025 |
| **Discoverer** | StepSecurity / Palo Alto Networks Unit 42 |

### Technical Description

The `v1` tag of reviewdog/action-setup was modified to inject malicious code into the `install.sh` file. The injected payload exfiltrated CI/CD secrets by printing them to workflow logs, double-encoding in base64 to bypass GitHub's automatic log masking mechanisms. Any reviewdog action that depended on action-setup@v1 was transitively compromised.

### Exploitation

Approximately 1,500 repositories were affected during the ~2-hour window. The compromise of a reviewdog maintainer account enabled the attacker to subsequently pivot to the tj-actions/changed-files compromise (CVE-2025-30066), which had far broader impact. CISA added this to the KEV catalog on March 24, 2025.

### Fix/Patch Details

The malicious tag was reverted within 2 hours. The compromised user account was secured. All affected organizations should rotate secrets from CI/CD environments that ran during the compromised window.

---

## 6. CVE-2025-30065 -- Apache Parquet Java Deserialization RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-30065 |
| **Package/Project** | Apache Parquet Java (parquet-avro module) |
| **Ecosystem** | Maven / Java |
| **Severity** | **CVSS 10.0 (Critical)** |
| **CWE** | CWE-502 (Deserialization of Untrusted Data) |
| **Affected Versions** | All versions <= 1.15.0 |
| **Patched Versions** | 1.15.1 |
| **Discovered** | Disclosed April 1, 2025 |
| **Patched** | March 16, 2025 (silent fix in 1.15.1 release) |
| **Discoverer** | Keyi Li (Amazon) |

### Technical Description

A critical deserialization vulnerability in the parquet-avro module where the library fails to restrict which Java classes can be instantiated when reading Avro data embedded in Parquet files. An attacker can craft a Parquet file with metadata fields containing serialized Java objects that are instantiated during parsing via the `getDefaultValue()` mechanism, achieving arbitrary code execution.

### Exploitation

An attacker supplies a crafted `.parquet` file to any data pipeline that automatically processes Parquet files from untrusted sources. Frameworks affected include Apache Spark, Apache Hive, Presto/Trino, and Python data libraries relying on the vulnerable Java module. While practical exploitation is somewhat constrained (the instantiated class must have exploitable side effects during construction), PoC tools have been released by F5 Labs.

### Fix/Patch Details

Upgrade to Apache Parquet 1.15.1. Additionally, configure `org.apache.parquet.avro.SERIALIZABLE_PACKAGES` to restrict which packages are allowed for deserialization.

---

## 7. CVE-2025-3248 -- Langflow Unauthenticated RCE via Code Injection

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-3248 |
| **Package/Project** | Langflow |
| **Ecosystem** | PyPI / Python |
| **Severity** | **CVSS 9.8 (Critical)** |
| **CWE** | CWE-94 (Improper Control of Generation of Code / Code Injection) |
| **Affected Versions** | All versions < 1.3.0 |
| **Patched Versions** | 1.3.0 |
| **Discovered** | Early 2025 |
| **Patched** | March 3, 2025 (PR #6911) |
| **Discoverer** | Multiple researchers; CISA added to KEV May 2025 |

### Technical Description

Langflow's `/api/v1/validate/code` endpoint was designed to validate Python code snippets for custom components. Before version 1.3.0, this endpoint was accessible without any authentication and invoked Python's `exec()` on user-supplied code without sandboxing. Python's decorator evaluation at parse time made it possible to embed malicious payloads inside decorators that execute during code parsing.

### Exploitation

Unauthenticated RCE. An attacker sends a crafted POST request to `/api/v1/validate/code` with Python code containing malicious decorators. The code is executed server-side. Actively exploited in the wild, including for delivery of the Flodrix botnet. Added to CISA KEV in May 2025.

### Fix/Patch Details

The fix (PR #6911) adds an authentication requirement to the vulnerable endpoint by adding a `_current_user: CurrentActiveUser` parameter to the `post_validate_code` function. Upgrade to Langflow >= 1.3.0.

---

## 8. CVE-2026-33017 -- Langflow Unauthenticated RCE (Second Occurrence)

| Field | Details |
|---|---|
| **CVE ID** | CVE-2026-33017 |
| **Package/Project** | Langflow |
| **Ecosystem** | PyPI / Python |
| **Severity** | **CVSS 9.3 (Critical)** |
| **CWE** | CWE-94 (Code Injection) |
| **Affected Versions** | All versions through 1.8.1 |
| **Patched Versions** | 1.9.0 |
| **Discovered** | Disclosed March 17, 2026 |
| **Patched** | March 2026 (version 1.9.0) |
| **Discoverer** | Aviral Srivastava |

### Technical Description

A different unauthenticated RCE path in Langflow, this time via the `POST /api/v1/build_public_tmp/{flow_id}/flow` endpoint. This endpoint, designed for building public flows, accepts attacker-supplied flow data containing arbitrary Python code in node definitions, which is then executed server-side without sandboxing. Essentially the same class of bug as CVE-2025-3248 (unsandboxed `exec()`) but on a different endpoint that was missed in the previous fix.

### Exploitation

Exploitation was observed in the wild within 20 hours of advisory publication on March 17, 2026. Attackers scanned for vulnerable instances within 20 hours, executed Python exploit scripts within 21 hours, and began harvesting `.env` and `.db` files within 24 hours. Added to CISA KEV March 2026.

### Fix/Patch Details

Upgrade to Langflow 1.9.0 or later. The patch removes the ability for public flow endpoints to execute arbitrary code.

---

## 9. CVE-2025-34291 -- Langflow CORS/CSRF Chain to Account Takeover and RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-34291 |
| **Package/Project** | Langflow |
| **Ecosystem** | PyPI / Python |
| **Severity** | **CVSS 9.4 (Critical, v4.0)** |
| **CWE** | CWE-346 (Origin Validation Error) |
| **Affected Versions** | All versions <= 1.6.9 |
| **Patched Versions** | 1.7.0 |
| **Discovered** | Mid-2025 |
| **Patched** | Version 1.7.0 |
| **Discoverer** | Obsidian Security |

### Technical Description

A chained vulnerability combining three weaknesses: (1) an overly permissive CORS configuration (`allow_origins='*'` with `allow_credentials=True`), (2) lack of CSRF protection on the token refresh endpoint with `SameSite=None` cookies, and (3) a code validation endpoint that executes code by design. An attacker can achieve complete account takeover and RCE by having a victim visit a malicious webpage.

### Exploitation

A victim visits an attacker-controlled webpage. The page makes cross-origin requests to the Langflow instance, which are accepted due to the permissive CORS policy. The refresh token cookie is sent automatically (SameSite=None), allowing the attacker to obtain fresh access_token/refresh_token pairs. The attacker then uses the hijacked session to execute arbitrary code via the code validation endpoint. Active exploitation observed starting January 23, 2026.

### Fix/Patch Details

Langflow 1.7.0 corrects the CORS configuration defaults and adds CSRF protections to the token refresh endpoint.

---

## 10. CVE-2025-68613 -- n8n Expression Injection RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-68613 |
| **Package/Project** | n8n (workflow automation platform) |
| **Ecosystem** | npm / Node.js |
| **Severity** | **CVSS 9.9 (Critical)** |
| **CWE** | CWE-913 (Improper Control of Dynamically-Managed Code Resources) |
| **Affected Versions** | 0.211.0 through < 1.120.4, < 1.121.1, < 1.122.0 |
| **Patched Versions** | 1.120.4, 1.121.1, 1.122.0 |
| **Discovered** | 2025 |
| **Patched** | 2025 |
| **Discoverer** | Orca Security |

### Technical Description

A critical sandbox escape vulnerability in n8n's server-side expression evaluation engine. Function expressions within evaluated workflow code could gain access to the Node.js global `this` object, which provides access to `process`, enabling `process.mainModule.require('child_process').execSync(...)` to execute arbitrary OS-level commands with the privileges of the n8n process.

### Exploitation

Requires authentication with workflow create/edit permissions (no elevated privileges needed). An attacker crafts a workflow containing malicious expressions that escape the sandbox and execute system commands. Because n8n often serves as a central orchestration layer connecting internal systems, cloud services, and third-party APIs, compromise cascades across the entire organization. Over 103,000 potentially vulnerable instances were identified on the internet. Added to CISA KEV March 2026.

### Fix/Patch Details

The patch introduces a new `ASTBeforeHook` called `FunctionThisSanitizer` that properly hardens expression evaluation and prevents sandbox escapes. Upgrade to n8n 1.120.4, 1.121.1, or 1.122.0.

---

## 11. CVE-2025-54313 -- eslint-config-prettier Supply Chain Compromise

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-54313 |
| **Package/Project** | eslint-config-prettier (also: eslint-plugin-prettier, synckit) |
| **Ecosystem** | npm |
| **Severity** | **High** |
| **CWE** | CWE-506 (Embedded Malicious Code) |
| **Affected Versions** | eslint-config-prettier 8.10.1, 9.1.1, 10.1.6, 10.1.7; eslint-plugin-prettier 4.2.2, 4.2.3; synckit 0.11.9 |
| **Patched Versions** | eslint-config-prettier 8.10.2+, 9.1.2+, 10.1.8+ |
| **Discovered** | July 18, 2025 |
| **Patched** | July 2025 (malicious versions deprecated, clean releases published) |
| **Discoverer** | Community / ZeroPath |

### Technical Description

A maintainer of eslint-config-prettier fell victim to a phishing email spoofed from `support@npmjs.com` (actually from the malicious `npnjs.com` domain). The stolen npm token was used to publish compromised versions of eslint-config-prettier and related packages. The malicious versions include an `install.js` post-install script that deploys `node-gyp.dll` malware on Windows systems.

### Exploitation

Installing any of the affected versions on Windows triggers the malicious post-install script, which loads and executes a Windows DLL. The attack is Windows-only -- the malicious code exits immediately on non-Windows platforms. eslint-config-prettier has approximately 30 million weekly downloads, making the blast radius significant for Windows development environments. Added to CISA KEV January 2026.

### Fix/Patch Details

The maintainer revoked the stolen token, deprecated the malicious versions, and published clean releases. Users should ensure they are on the clean versions and scan Windows development machines for `node-gyp.dll` artifacts.

---

## 12. CVE-2025-27407 -- graphql-ruby RCE via Malicious Schema Loading

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-27407 |
| **Package/Project** | graphql-ruby |
| **Ecosystem** | RubyGems |
| **Severity** | **CVSS 9.1 (Critical)** |
| **CWE** | CWE-94 (Improper Control of Generation of Code / Code Injection) |
| **Affected Versions** | 1.11.5 through < 1.11.8, < 1.12.25, < 1.13.24, < 2.0.32, < 2.1.14, < 2.2.17, < 2.3.21 |
| **Patched Versions** | 1.11.8, 1.12.25, 1.13.24, 2.0.32, 2.1.14, 2.2.17, 2.3.21 |
| **Discovered** | March 2025 |
| **Patched** | March 12, 2025 (via GitLab patch release 17.9.2, 17.8.5, 17.7.7) |
| **Discoverer** | GitLab Security Team |

### Technical Description

Loading a malicious schema definition via `GraphQL::Schema.from_introspection` or `GraphQL::Schema::Loader.load` can result in remote code execution. The vulnerability is exploitable over the network without requiring privileges or user interaction, and a successful exploit can compromise resources beyond the graphql-ruby library. In GitLab, this could be triggered by an attacker-controlled authenticated user transferring a malicious project via the Direct Transfer feature.

### Exploitation

An attacker prepares a crafted GraphQL introspection response and causes the target application to load it. For GitLab users specifically, the attack vector is through the Direct Transfer project migration feature, where an authenticated attacker provides a malicious project containing a poisoned GraphQL schema.

### Fix/Patch Details

Upgrade graphql-ruby to the patched versions listed above. For GitLab, upgrade to 17.9.2, 17.8.5, or 17.7.7. As a mitigation, GitLab administrators can disable Direct Transfer if they cannot patch immediately.

---

## 13. CVE-2025-25291 / CVE-2025-25292 -- ruby-saml SAML Authentication Bypass

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-25291, CVE-2025-25292 |
| **Package/Project** | ruby-saml |
| **Ecosystem** | RubyGems |
| **Severity** | **CVSS 8.8 (High)** |
| **CWE** | CVE-2025-25291: CWE-347 (Improper Verification of Cryptographic Signature); CVE-2025-25292: CWE-436 (Interpretation Conflict) |
| **Affected Versions** | ruby-saml < 1.12.4 and < 1.18.0 |
| **Patched Versions** | 1.12.4, 1.18.0 |
| **Discovered** | November 2024 (reported to maintainers) |
| **Patched** | March 12, 2025 |
| **Discoverer** | GitHub Security Lab |

### Technical Description

A parser differential between ReXML and Nokogiri XML parsers causes them to generate entirely different document structures from the same XML input. An attacker exploits this with a Signature Wrapping attack: they craft a malicious SAML response where the `ds:Signature` is placed within a manipulated namespace scope. The validation logic (using one parser) sees a validly signed element, while the authentication logic (using the other parser) processes a different, unsigned, attacker-controlled element.

### Exploitation

An attacker in possession of a single valid signed SAML document from the identity provider can construct arbitrary SAML assertions and log in as any user, achieving full account takeover. This is particularly dangerous for applications using SAML SSO (including GitLab, Terraform Enterprise, and numerous other Ruby applications that depend on ruby-saml).

### Fix/Patch Details

Upgrade ruby-saml to 1.12.4 or 1.18.0. The fix ensures consistent XML parsing and validates that the signed element is the same element used for authentication.

---

## 14. CVE-2025-27520 -- BentoML Insecure Deserialization RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-27520 |
| **Package/Project** | BentoML |
| **Ecosystem** | PyPI / Python |
| **Severity** | **CVSS 9.8 (Critical)** |
| **CWE** | CWE-502 (Deserialization of Untrusted Data) |
| **Affected Versions** | 1.3.8 through 1.4.2 |
| **Patched Versions** | 1.4.3 |
| **Discovered** | April 2025 |
| **Patched** | April 2025 (commit b35f4f4f) |
| **Discoverer** | Community / Checkmarx |

### Technical Description

The `deserialize_value()` function in BentoML's `serde.py` deserializes input data without validation. An unauthenticated attacker can send an HTTP request to any valid BentoML endpoint with a `Content-Type` of `application/vnd.bentoml+pickle` containing a malicious pickle payload, triggering arbitrary code execution during deserialization.

### Exploitation

An unauthenticated attacker sends an HTTP request with a crafted pickle payload. A public PoC and Metasploit module (`exploit/linux/http/bentoml_rce_cve_2025_27520`) are available. Any BentoML deployment exposed to the network is directly exploitable.

### Fix/Patch Details

Upgrade to BentoML 1.4.3. The patch (commit b35f4f4f) blocks HTTP requests with Content-Type `application/vnd.bentoml+pickle`, preventing deserialization of pickle data from HTTP requests entirely. As a workaround, configure a WAF rule to block requests containing this Content-Type.

---

## 15. CVE-2025-27607 -- python-json-logger Dependency Hijacking RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-27607 |
| **Package/Project** | python-json-logger |
| **Ecosystem** | PyPI / Python |
| **Severity** | **Critical (potential RCE)** |
| **CWE** | CWE-427 (Uncontrolled Search Path Element) / Supply Chain Dependency Hijack |
| **Affected Versions** | 3.2.0, 3.2.1 |
| **Patched Versions** | 3.3.0 |
| **Discovered** | March 2025 |
| **Patched** | March 4, 2025 (version 3.3.0) |
| **Discoverer** | Community |

### Technical Description

python-json-logger versions 3.2.0 and 3.2.1 listed an optional development dependency called `msgspec-python313-pre`. The original owner of this package deleted it from PyPI, leaving the package name available for anyone to claim. An attacker could register a new package with this name on PyPI and inject arbitrary malicious code. Between December 30, 2024 and March 4, 2025, anyone installing python-json-logger's dev dependencies on Python 3.13 (`pip install python-json-logger[dev]`) was at risk.

### Exploitation

An attacker registers the abandoned `msgspec-python313-pre` package name on PyPI and publishes a malicious version. Any developer running `pip install python-json-logger[dev]` on Python 3.13 would install the attacker's package, achieving RCE. Over 43 million Python installations were potentially exposed.

### Fix/Patch Details

Version 3.3.0 removes the reference to the abandoned `msgspec-python313-pre` package and properly handles Python 3.13 support. The abandoned package name was also claimed by a security researcher to prevent malicious use.

---

## 16. CVE-2025-68664 -- LangGrinch: LangChain Core Serialization Injection

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-68664 |
| **Package/Project** | langchain-core |
| **Ecosystem** | PyPI / Python |
| **Severity** | **CVSS 9.3 (Critical)** |
| **CWE** | CWE-502 (Deserialization of Untrusted Data) |
| **Affected Versions** | langchain-core < 0.3.81, < 1.2.5 |
| **Patched Versions** | 0.3.81, 1.2.5 |
| **Discovered** | December 4, 2025 (reported by researcher) |
| **Patched** | December 2025 |
| **Discoverer** | Yarden Porat / Cyata |

### Technical Description

Codenamed "LangGrinch," this is a serialization injection vulnerability in LangChain's `dumps()` and `dumpd()` functions. LangChain uses a special internal serialization format where dictionaries containing an `lc` marker represent LangChain objects. The vulnerability is that `dumps()` and `dumpd()` did not properly escape user-controlled dictionaries that happened to include the reserved `lc` key, allowing an attacker to inject objects into the deserialization pipeline.

### Exploitation

An attacker causes a LangChain orchestration loop to serialize and later deserialize content including an `lc` key. This enables: (1) secret extraction from environment variables when `secrets_from_env=True` (previously the default), (2) instantiation of classes within pre-approved trusted namespaces (langchain_core, langchain, langchain_community), and (3) potentially arbitrary code execution via Jinja2 templates.

### Fix/Patch Details

The patch introduces an allowlist parameter `allowed_objects` in `load()` and `loads()` to specify which classes can be serialized/deserialized. Jinja2 templates are blocked by default. `secrets_from_env` is set to `False` by default. Upgrade to langchain-core 0.3.81 or 1.2.5.

---

## 17. CVE-2025-64439 -- LangGraph Checkpoint Deserialization RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-64439 |
| **Package/Project** | langgraph-checkpoint |
| **Ecosystem** | PyPI / Python |
| **Severity** | **Critical (RCE)** |
| **CWE** | CWE-502 (Deserialization of Untrusted Data) |
| **Affected Versions** | langgraph-checkpoint < 3.0 |
| **Patched Versions** | langgraph-checkpoint 3.0; langgraph-api 0.5+ |
| **Discovered** | 2025 |
| **Patched** | 2025 |
| **Discoverer** | LangChain Security Team |

### Technical Description

LangGraph's `JsonPlusSerializer` (the default serialization protocol for all checkpointing) contains a remote code execution vulnerability when deserializing payloads saved in the "json" serialization mode. If illegal Unicode surrogate values cause serialization to fail, the system falls back to "json" mode. In this mode, the deserializer supports a constructor-style format for custom objects that allows arbitrary function execution upon load.

### Exploitation

An attacker who can influence the data being checkpointed (e.g., via crafted LLM responses or user inputs that contain Unicode surrogate values) can trigger the fallback to json mode and inject a malicious payload that, when deserialized from a checkpoint, executes arbitrary functions on the server.

### Fix/Patch Details

Upgrade to langgraph-checkpoint 3.0, which prevents deserialization of custom objects saved in json mode. If using langgraph-api, version 0.5+ is also safe.

---

## 18. CVE-2025-31125 -- Vite Arbitrary File Read via server.fs.deny Bypass

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-31125 |
| **Package/Project** | Vite (Vitejs) |
| **Ecosystem** | npm |
| **Severity** | **CVSS 5.3 (Medium)** -- but added to CISA KEV due to active exploitation |
| **CWE** | CWE-200 (Exposure of Sensitive Information) / CWE-22 (Path Traversal) |
| **Affected Versions** | Vite < 6.2.4, < 6.1.3, < 6.0.13, < 5.4.16, < 4.5.11 |
| **Patched Versions** | 6.2.4, 6.1.3, 6.0.13, 5.4.16, 4.5.11 |
| **Discovered** | March 2025 |
| **Patched** | March/April 2025 |
| **Discoverer** | Community |

### Technical Description

Vite's `server.fs.deny` access control can be bypassed using the `?inline&import` or `?raw?import` query parameters. Flaws in Vite's regular expression and URL parameter handling allow an attacker to craft URLs like `http://localhost:5173/@fs/C:/windows/win.ini?import&?inline=1.wasm?init` to read arbitrary files from the filesystem, bypassing the server.fs.deny file access control.

### Exploitation

An attacker with network access to a Vite development server (exposed via `--host` or `server.host` configuration) can read arbitrary files, including `.env` files with API keys and secrets, source code, and system configuration files. While this only affects development servers, many developers expose their dev servers to the network, and the vulnerability was actively exploited in the wild. Added to CISA KEV January 22, 2026.

### Fix/Patch Details

Upgrade to the patched versions. The fix corrects the URL parsing regex to properly handle the malicious query parameter combinations.

---

## 19. CVE-2025-62518 -- TARmageddon: Rust async-tar/tokio-tar RCE

| Field | Details |
|---|---|
| **CVE ID** | CVE-2025-62518 |
| **Package/Project** | async-tar, tokio-tar (and forks including astral-tokio-tar) |
| **Ecosystem** | crates.io / Rust |
| **Severity** | **CVSS 8.1 (High)** |
| **CWE** | CWE-22 (Path Traversal) leading to file overwrite / RCE |
| **Affected Versions** | All versions of async-tar and tokio-tar before patches |
| **Patched Versions** | astral-tokio-tar 0.5.6 (recommended migration target) |
| **Discovered** | Late August 2025 |
| **Patched** | October 2025 |
| **Discoverer** | Edera |

### Technical Description

A boundary-parsing bug in tar file processing. When a tar file contains PAX extended headers that override the file size, the library uses the octal size field from the ustar header (often zero) instead of the PAX override for position calculations. If the ustar header specifies size zero, the parser advances 0 bytes, fails to skip the actual file data (a nested TAR archive), and incorrectly interprets the inner archive's headers as entries belonging to the outer archive. This allows an attacker to "smuggle" extra files during extraction.

### Exploitation

An attacker provides a crafted tar file containing nested archives with PAX extended headers. During extraction, smuggled files are written to arbitrary paths, enabling configuration overwrite and RCE. Affected downstream projects include `uv` (Astral's Python package manager), testcontainers, and wasmCloud. The original `async-tar` library is abandoned, making this a systemic supply chain risk.

### Fix/Patch Details

Edera provided patches for astral-tokio-tar (0.5.6) and krata-tokio-tar. Since tokio-tar is unmaintained, migration to astral-tokio-tar >= 0.5.6 is recommended. Organizations should implement strict path whitelists, sandboxed extraction with least-privilege, and artifact provenance checks.

---

## 20. Shai-Hulud / CVE-2026-34841 -- npm Self-Replicating Worm and Axios Supply Chain Attack

| Field | Details |
|---|---|
| **CVE ID** | Multiple: Shai-Hulud family (CVE-2025-10894, CVE-2025-59037, CVE-2025-59140, CVE-2025-59143, CVE-2025-59162, and others); Axios: CVE-2026-34841 |
| **Package/Project** | npm ecosystem-wide (500+ packages including supports-color, debug, chalk); Axios (March 2026) |
| **Ecosystem** | npm |
| **Severity** | **Critical (ecosystem-wide supply chain compromise)** |
| **CWE** | CWE-506 (Embedded Malicious Code), CWE-912 (Hidden Functionality) |
| **Affected Versions** | Shai-Hulud: 500+ packages with malicious versions; Axios: 1.14.1, 0.30.4 |
| **Patched Versions** | Malicious versions unpublished from npm; Axios: safe versions 1.14.0, 0.30.3 |
| **Discovered** | Shai-Hulud: September 8-15, 2025; Shai-Hulud 2.0: November 24, 2025; Axios: March 31, 2026 |
| **Patched** | Ongoing npm takedowns; Axios malicious versions removed within ~3 hours |
| **Discoverer** | Shai-Hulud: StepSecurity, Socket; Axios: Socket, Microsoft Threat Intelligence |

### Technical Description

**Shai-Hulud (September 2025):** The first successful self-replicating supply chain worm in the npm ecosystem. Attackers phished npm maintainer Josh Junon (Qix-) using a spoofed npm support email (`npmjs.help` domain), stealing npm credentials. Malicious post-install scripts were injected into compromised packages. The worm uses TruffleHog to scan for secrets, exfiltrates credentials to public GitHub repositories, and if it finds npm tokens, authenticates as the compromised developer and publishes malicious versions of their other packages -- self-replicating without C2 infrastructure.

**Shai-Hulud 2.0 (November 2025):** An evolved variant that successfully backdoored 796 npm packages totaling over 20 million weekly downloads, abusing the `preinstall` lifecycle script to execute before installation even completes.

**Axios (March 31, 2026):** Attributed by Microsoft Threat Intelligence to Sapphire Sleet (North Korean state actor, also tracked as UNC1069 by Google). Malicious versions 1.14.1 and 0.30.4 injected dependency `plain-crypto-js@4.2.1` with a post-install script that downloads a cross-platform RAT (Windows, macOS, Linux). The attack was live for approximately 3 hours.

### Exploitation

Any `npm install` of compromised packages executes the malicious scripts. For Shai-Hulud, the worm spreads exponentially through stolen tokens. For Axios, any project auto-updating to `^1.14.0` or `0.30.0` would connect to Sapphire Sleet C2 and download a second-stage RAT.

### Fix/Patch Details

npm has unpublished malicious versions and revoked compromised tokens. For Axios specifically, downgrade to 1.14.0 or 0.30.3 and rotate all secrets/credentials on affected machines. CISA issued a specific advisory for the Shai-Hulud compromise on September 23, 2025. npm has since accelerated adoption of provenance attestations and mandatory 2FA.

---

## Summary Table

| # | CVE | Project | CVSS | Type | Date |
|---|---|---|---|---|---|
| 1 | CVE-2025-55182 | React RSC | 10.0 | Deserialization RCE | Dec 2025 |
| 2 | CVE-2025-29927 | Next.js | 9.1 | Auth Bypass | Mar 2025 |
| 3 | CVE-2025-1974 | ingress-nginx | 9.8 | Config Injection RCE | Mar 2025 |
| 4 | CVE-2025-30066 | tj-actions/changed-files | 8.6 | Supply Chain (CI/CD) | Mar 2025 |
| 5 | CVE-2025-30154 | reviewdog/action-setup | High | Supply Chain (CI/CD) | Mar 2025 |
| 6 | CVE-2025-30065 | Apache Parquet | 10.0 | Deserialization RCE | Apr 2025 |
| 7 | CVE-2025-3248 | Langflow | 9.8 | Code Injection RCE | Mar 2025 |
| 8 | CVE-2026-33017 | Langflow | 9.3 | Code Injection RCE | Mar 2026 |
| 9 | CVE-2025-34291 | Langflow | 9.4 | CORS/CSRF Chain | Mid 2025 |
| 10 | CVE-2025-68613 | n8n | 9.9 | Expression Injection RCE | 2025 |
| 11 | CVE-2025-54313 | eslint-config-prettier | High | Supply Chain Malware | Jul 2025 |
| 12 | CVE-2025-27407 | graphql-ruby | 9.1 | Code Injection RCE | Mar 2025 |
| 13 | CVE-2025-25291/25292 | ruby-saml | 8.8 | SAML Auth Bypass | Mar 2025 |
| 14 | CVE-2025-27520 | BentoML | 9.8 | Deserialization RCE | Apr 2025 |
| 15 | CVE-2025-27607 | python-json-logger | Critical | Dependency Hijack | Mar 2025 |
| 16 | CVE-2025-68664 | langchain-core | 9.3 | Serialization Injection | Dec 2025 |
| 17 | CVE-2025-64439 | langgraph-checkpoint | Critical | Deserialization RCE | 2025 |
| 18 | CVE-2025-31125 | Vite | 5.3 | File Read / Path Traversal | Mar 2025 |
| 19 | CVE-2025-62518 | async-tar/tokio-tar | 8.1 | Path Traversal / RCE | Oct 2025 |
| 20 | CVE-2026-34841+ | npm / Axios / Shai-Hulud | Critical | Supply Chain Worm + RAT | Sep 2025 - Mar 2026 |

---

## Key Trends Observed

1. **AI/ML tooling is a major new attack surface.** Langflow (3 CVEs), LangChain, LangGraph, n8n, and BentoML all suffered critical vulnerabilities -- most involving unsandboxed code execution or deserialization.

2. **Supply chain attacks are accelerating.** Shai-Hulud demonstrated the first self-replicating npm worm, and the Axios attack was attributed to a nation-state actor (North Korea/Sapphire Sleet).

3. **Time-to-exploit is collapsing.** CVE-2026-33017 was exploited within 20 hours. React2Shell PoCs appeared within 30 hours. The Axios attack window was just 3 hours.

4. **Deserialization remains the #1 vulnerability class.** CWE-502 appears in React2Shell, Apache Parquet, BentoML, LangChain, and LangGraph.

5. **CI/CD infrastructure is a prime target.** The tj-actions and reviewdog compromises affected 23,000+ repositories and demonstrated cascading supply chain attacks.

6. **Maintainer credential theft is the primary supply chain vector.** Phishing attacks targeting npm maintainers were behind eslint-config-prettier, Shai-Hulud, and the broader September 2025 npm compromise.

---

## Sources

- [React Critical Security Advisory](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)
- [Wiz Blog: React2Shell](https://www.wiz.io/blog/critical-vulnerability-in-react-cve-2025-55182)
- [Google Cloud: Threat Actors Exploit React2Shell](https://cloud.google.com/blog/topics/threat-intelligence/threat-actors-exploit-react2shell-cve-2025-55182)
- [Datadog: Next.js Middleware Auth Bypass](https://securitylabs.datadoghq.com/articles/nextjs-middleware-auth-bypass/)
- [Wiz Blog: IngressNightmare](https://www.wiz.io/blog/ingress-nginx-kubernetes-vulnerabilities)
- [Kubernetes Blog: CVE-2025-1974](https://kubernetes.io/blog/2025/03/24/ingress-nginx-cve-2025-1974/)
- [Wiz Blog: tj-actions Supply Chain Attack](https://www.wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066)
- [Unit 42: GitHub Actions Supply Chain Attack](https://unit42.paloaltonetworks.com/github-actions-supply-chain-attack/)
- [CISA: tj-actions and reviewdog Advisory](https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction)
- [The Hacker News: Apache Parquet RCE](https://thehackernews.com/2025/04/critical-flaw-in-apache-parquet-allows.html)
- [Zscaler: Langflow CVE-2025-3248](https://www.zscaler.com/blogs/security-research/cve-2025-3248-rce-vulnerability-langflow)
- [The Hacker News: Langflow CVE-2026-33017](https://thehackernews.com/2026/03/critical-langflow-flaw-cve-2026-33017.html)
- [Obsidian Security: Langflow CVE-2025-34291](https://www.obsidiansecurity.com/blog/cve-2025-34291-critical-account-takeover-and-rce-vulnerability-in-the-langflow-ai-agent-workflow-platform)
- [Orca Security: n8n CVE-2025-68613](https://orca.security/resources/blog/cve-2025-68613-n8n-rce-vulnerability/)
- [ZeroPath: eslint-config-prettier CVE-2025-54313](https://zeropath.com/blog/cve-2025-54313-eslint-config-prettier-supply-chain-malware)
- [SecurityOnline: graphql-ruby CVE-2025-27407](https://securityonline.info/cve-2025-27407-cvss-9-1-critical-graphql-ruby-flaw-exposes-millions-to-rce/)
- [The Hacker News: ruby-saml Vulnerabilities](https://thehackernews.com/2025/03/github-uncovers-new-ruby-saml.html)
- [Checkmarx: BentoML CVE-2025-27520](https://checkmarx.com/zero-post/bentoml-rce-fewer-affected-versions-cve-2025-27520/)
- [Upwind: python-json-logger CVE-2025-27607](https://www.upwind.io/feed/supply-chain-remote-code-execution-in-python-json-logger-cve-2025-27607)
- [Cyata: LangGrinch CVE-2025-68664](https://cyata.ai/blog/langgrinch-langchain-core-cve-2025-68664/)
- [GitHub: LangGraph GHSA-wwqv-p2pp-99h5](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-wwqv-p2pp-99h5)
- [Invicti: Vite Arbitrary File Read](https://www.invicti.com/web-application-vulnerabilities/vite-arbitrary-file-read-cve-2025-30208-cve-2025-31125)
- [Edera: TARmageddon](https://edera.dev/stories/tarmageddon)
- [The Hacker News: TARmageddon](https://thehackernews.com/2025/10/tarmageddon-flaw-in-async-tar-rust.html)
- [CISA: npm Ecosystem Compromise](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem)
- [Sysdig: Shai-Hulud Worm](https://www.sysdig.com/blog/shai-hulud-the-novel-self-replicating-worm-infecting-hundreds-of-npm-packages)
- [Wiz Blog: Shai-Hulud 2.0](https://www.wiz.io/blog/shai-hulud-2-0-ongoing-supply-chain-attack)
- [Socket: Axios Compromise](https://socket.dev/blog/axios-npm-package-compromised)
- [Microsoft: Axios Supply Chain Compromise](https://www.microsoft.com/en-us/security/blog/2026/04/01/mitigating-the-axios-npm-supply-chain-compromise/)
- [Google Cloud: North Korea Axios Attack](https://cloud.google.com/blog/topics/threat-intelligence/north-korea-threat-actor-targets-axios-npm-package)
- [NVD: CVE-2025-55182](https://nvd.nist.gov/vuln/detail/CVE-2025-55182)
- [NVD: CVE-2025-29927](https://nvd.nist.gov/vuln/detail/CVE-2025-29927)
- [NVD: CVE-2025-3248](https://nvd.nist.gov/vuln/detail/CVE-2025-3248)
- [NVD: CVE-2025-27520](https://nvd.nist.gov/vuln/detail/CVE-2025-27520)
- [NVD: CVE-2025-68613](https://nvd.nist.gov/vuln/detail/CVE-2025-68613)
