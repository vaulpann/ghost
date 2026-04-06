"""Seed the 20 historical supply chain attacks as Sentinel game scenarios."""

import asyncio
import logging
from app.database import async_session, engine
from app.models.sentinel import SentinelScenario
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

SCENARIOS = [
    # === TUTORIAL (obvious signals, single dimension) ===
    {
        "source": "historical", "difficulty": "tutorial", "is_malicious": True,
        "attack_name": "colors.js Maintainer Sabotage", "attack_type": "maintainer_sabotage",
        "package_name": "colors", "registry": "npm",
        "version_from": "1.4.0", "version_to": "1.4.44-liberty-2",
        "real_cve": None, "real_cvss": None,
        "identity_data": {
            "publisher": "marak", "publisher_since": "2012-03-15",
            "is_usual_publisher": True, "account_age_days": 3580,
            "previous_packages": 45, "trust_score": 0.9,
            "flags": []
        },
        "timing_data": {
            "release_history": [
                {"version": "1.4.0", "date": "2020-01-20", "gap_days": None},
                {"version": "1.4.44-liberty-2", "date": "2022-01-08", "gap_days": 719}
            ],
            "cadence_normal": False,
            "flags": ["Version gap: 719 days then sudden release", "Unusual version string: 'liberty-2'"]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": ["american-flag.js"], "files_removed": [],
            "flags": ["New file: american-flag.js (not typical for a color utility)"]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green", "network": "green",
                "install_scripts": "green", "crypto": "green",
                "infinite_loop": "red", "console_output": "red"
            },
            "flags": ["INFINITE LOOP detected in new code", "Endless console.log output"]
        },
        "flow_data": {
            "outbound_connections": [],
            "data_reads": [],
            "flags": []
        },
        "context_data": {
            "description": "A library for adding color to console output",
            "update_summary": "Added 'american-flag' module with infinite loop that prints 'LIBERTY LIBERTY LIBERTY' endlessly",
            "mismatch_score": 0.95,
            "flags": ["Console color library adding infinite loop", "Update has no functional purpose"]
        },
        "postmortem": "Developer Marak Squires deliberately sabotaged his own packages (colors.js and faker.js) to protest corporations using open source without contributing back. colors.js v1.4.44-liberty-2 contained an infinite loop, while faker.js v6.6.6 had all code deleted. The version numbers themselves ('liberty-2' and '6.6.6') were signals of protest.",
    },
    {
        "source": "historical", "difficulty": "tutorial", "is_malicious": True,
        "attack_name": "faker.js Code Deletion", "attack_type": "maintainer_sabotage",
        "package_name": "faker", "registry": "npm",
        "version_from": "5.5.3", "version_to": "6.6.6",
        "real_cve": None, "real_cvss": None,
        "identity_data": {
            "publisher": "marak", "publisher_since": "2012-03-15",
            "is_usual_publisher": True, "account_age_days": 3580,
            "previous_packages": 45, "trust_score": 0.9, "flags": []
        },
        "timing_data": {
            "release_history": [
                {"version": "5.5.3", "date": "2021-04-15", "gap_days": None},
                {"version": "6.6.6", "date": "2022-01-05", "gap_days": 265}
            ],
            "cadence_normal": False,
            "flags": ["Version jumped from 5.x to 6.6.6", "Satanic version number: 6.6.6"]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": [], "files_removed": ["ALL SOURCE FILES"],
            "flags": ["ALL SOURCE CODE DELETED — empty package"]
        },
        "behavior_data": {
            "categories": {
                "compute": "red", "file_io": "green", "network": "green",
                "install_scripts": "green", "crypto": "green"
            },
            "flags": ["Package is empty — contains no functional code"]
        },
        "flow_data": {"outbound_connections": [], "data_reads": [], "flags": []},
        "context_data": {
            "description": "Generate massive amounts of fake data for testing",
            "update_summary": "All source code deleted. Package is now empty.",
            "mismatch_score": 1.0,
            "flags": ["Testing data generator is now completely empty"]
        },
        "postmortem": "Same maintainer sabotage as colors.js. faker.js v6.6.6 was published with all code removed. The version number '6.6.6' was a deliberate signal.",
    },

    # === EASY (clear signals, 1-2 dimensions) ===
    {
        "source": "historical", "difficulty": "easy", "is_malicious": True,
        "attack_name": "ua-parser-js Account Takeover", "attack_type": "account_hijack",
        "package_name": "ua-parser-js", "registry": "npm",
        "version_from": "0.7.28", "version_to": "0.7.29",
        "real_cve": None, "real_cvss": 9.8,
        "identity_data": {
            "publisher": "faisalman", "publisher_since": "2012-06-01",
            "is_usual_publisher": True, "account_age_days": 3430,
            "trust_score": 0.85,
            "flags": ["Publisher's email was flooded with spam around time of publish"]
        },
        "timing_data": {
            "release_history": [
                {"version": "0.7.28", "date": "2021-03-15", "gap_days": None},
                {"version": "0.7.29", "date": "2021-10-22", "gap_days": 221},
                {"version": "0.8.0", "date": "2021-10-22", "gap_days": 0},
                {"version": "1.0.0", "date": "2021-10-22", "gap_days": 0}
            ],
            "cadence_normal": False,
            "flags": [
                "Three versions across different major lines published simultaneously",
                "0.7.29, 0.8.0, and 1.0.0 all released on same day"
            ]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": ["preinstall.sh", "preinstall.bat"],
            "files_removed": [],
            "flags": ["New preinstall scripts added (Linux + Windows)"]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green",
                "network": "red", "install_scripts": "red",
                "crypto": "yellow", "binary_download": "red"
            },
            "flags": [
                "Preinstall script downloads platform-specific binaries",
                "XMRig cryptominer deployed on Linux",
                "Credential-stealing trojan deployed on Windows"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "citationsherbe.at", "type": "binary_download"},
                {"domain": "pool.supportxmr.com", "type": "mining_pool"}
            ],
            "data_reads": ["browser cookies", "passwords", "SSH keys"],
            "flags": ["Downloads binaries from unknown domain", "Connects to Monero mining pool"]
        },
        "context_data": {
            "description": "Browser user-agent string parser",
            "update_summary": "Added preinstall scripts that download and execute platform-specific binaries",
            "mismatch_score": 0.98,
            "flags": ["User-agent parser should NOT download binaries or mine cryptocurrency"]
        },
        "postmortem": "Attackers compromised the npm account of ua-parser-js maintainer. Three malicious versions were published simultaneously across major version lines — an unusual pattern that's a strong timing signal. The preinstall scripts deployed XMRig cryptominer on Linux and a credential stealer on Windows. Detected and reverted within ~4 hours.",
    },
    {
        "source": "historical", "difficulty": "easy", "is_malicious": True,
        "attack_name": "node-ipc Protestware", "attack_type": "maintainer_sabotage",
        "package_name": "node-ipc", "registry": "npm",
        "version_from": "10.1.0", "version_to": "10.1.1",
        "real_cve": "CVE-2022-23812", "real_cvss": 9.8,
        "identity_data": {
            "publisher": "RIAEvangelist", "publisher_since": "2014-01-10",
            "is_usual_publisher": True, "account_age_days": 2980,
            "trust_score": 0.85, "flags": []
        },
        "timing_data": {
            "release_history": [
                {"version": "10.1.0", "date": "2022-03-07", "gap_days": None},
                {"version": "10.1.1", "date": "2022-03-15", "gap_days": 8}
            ],
            "cadence_normal": True,
            "flags": ["Patch version — should be a minor bugfix"]
        },
        "shape_data": {
            "deps_added": ["peacenotwar"], "deps_removed": [],
            "files_added": [], "files_removed": [],
            "flags": ["New dependency: 'peacenotwar' (political name in a utility library)"]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "red",
                "network": "yellow", "install_scripts": "green",
                "geolocation": "red"
            },
            "flags": [
                "IP geolocation check added",
                "File overwrite operations targeting Russian/Belarusian IPs",
                "Replaces file contents with heart emoji ❤️"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "api.ipgeolocation.io", "type": "geolocation_lookup"}
            ],
            "data_reads": ["IP address", "filesystem paths"],
            "flags": ["Geolocation API call to determine user's country"]
        },
        "context_data": {
            "description": "Inter-process communication library for Node.js",
            "update_summary": "Added IP geolocation check; overwrites files with ❤️ for Russian/Belarusian users",
            "mismatch_score": 0.95,
            "flags": ["An IPC library has no reason to check geolocation or overwrite files"]
        },
        "postmortem": "Developer Brandon Miller added geopolitically-targeted destructive code to protest the Russian invasion of Ukraine. The code checked if the machine had a Russian or Belarusian IP and silently overwrote arbitrary files with a heart emoji. node-ipc is a transitive dependency of vue-cli, giving it massive blast radius.",
    },

    # === MEDIUM (subtler signals, 2-3 dimensions) ===
    {
        "source": "historical", "difficulty": "medium", "is_malicious": True,
        "attack_name": "event-stream / flatmap-stream", "attack_type": "maintainer_takeover",
        "package_name": "event-stream", "registry": "npm",
        "version_from": "3.3.6", "version_to": "4.0.0",
        "real_cve": None, "real_cvss": None,
        "identity_data": {
            "publisher": "right9ctrl", "publisher_since": "2018-08-01",
            "is_usual_publisher": False, "account_age_days": 60,
            "previous_packages": 1, "trust_score": 0.2,
            "flags": [
                "NEW maintainer — not the original author",
                "Account only 60 days old",
                "Original maintainer (dominictarr) transferred ownership"
            ]
        },
        "timing_data": {
            "release_history": [
                {"version": "3.3.6", "date": "2015-08-20", "gap_days": None},
                {"version": "4.0.0", "date": "2018-09-09", "gap_days": 1116}
            ],
            "cadence_normal": False,
            "flags": ["3+ year gap then new version from new maintainer"]
        },
        "shape_data": {
            "deps_added": ["flatmap-stream"], "deps_removed": [],
            "files_added": [], "files_removed": [],
            "flags": [
                "New dependency: flatmap-stream (only 1 version ever published)",
                "flatmap-stream's npm version differs from its GitHub source"
            ]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green",
                "network": "yellow", "install_scripts": "green",
                "crypto": "red", "obfuscation": "red"
            },
            "flags": [
                "flatmap-stream contains encrypted/obfuscated payload",
                "Payload uses AES-256 decryption with a hardcoded key",
                "Decrypted code targets BitPay Copay wallet private keys"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "copayapi.host", "type": "data_exfiltration"}
            ],
            "data_reads": ["Bitcoin wallet private keys", "package.json description"],
            "flags": [
                "Exfiltrates wallet keys to external server",
                "Uses package.json description as AES key (only activates in Copay)"
            ]
        },
        "context_data": {
            "description": "A toolkit for composing streams",
            "update_summary": "New maintainer added flatmap-stream dependency containing encrypted malicious payload targeting Bitcoin wallets",
            "mismatch_score": 0.9,
            "flags": ["Stream utility library adding cryptocurrency-related encrypted code"]
        },
        "postmortem": "An attacker ('right9ctrl') social engineered the transfer of event-stream from its original maintainer. They added the flatmap-stream dependency containing an encrypted payload that specifically targeted BitPay's Copay wallet. The encryption key was derived from Copay's package.json, meaning the payload ONLY activated in the Copay build environment. Went undetected for 2+ months.",
    },
    {
        "source": "historical", "difficulty": "medium", "is_malicious": True,
        "attack_name": "PyTorch / torchtriton Dependency Confusion", "attack_type": "dependency_confusion",
        "package_name": "torchtriton", "registry": "pypi",
        "version_from": None, "version_to": "0.0.1",
        "real_cve": None, "real_cvss": None,
        "identity_data": {
            "publisher": "unknown_user_2022", "publisher_since": "2022-12-20",
            "is_usual_publisher": False, "account_age_days": 5,
            "previous_packages": 0, "trust_score": 0.05,
            "flags": [
                "Brand new PyPI account (5 days old)",
                "Zero previous packages",
                "Package name matches PyTorch's PRIVATE package"
            ]
        },
        "timing_data": {
            "release_history": [
                {"version": "0.0.1", "date": "2022-12-25", "gap_days": None}
            ],
            "cadence_normal": False,
            "flags": ["Published on Christmas Day", "First and only version"]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": ["triton binary (obfuscated ELF)"],
            "files_removed": [],
            "flags": [
                "Package name 'torchtriton' exists on PRIVATE PyTorch index",
                "This version on PUBLIC PyPI — dependency confusion",
                "Package description says 'this is not the real torchtriton'"
            ]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "red",
                "network": "red", "install_scripts": "red",
                "anti_vm": "red"
            },
            "flags": [
                "Collects hostname, username, working directory",
                "Reads SSH keys, .gitconfig, .bash_history",
                "Reads /etc/hosts, /etc/passwd",
                "Contains anti-VM detection logic",
                "Data exfiltration via encrypted DNS queries"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "*.h4ck.cfd", "type": "dns_exfiltration"}
            ],
            "data_reads": ["SSH keys", ".gitconfig", ".bash_history", "/etc/passwd", "hostname", "username"],
            "flags": [
                "DNS-based exfiltration (not HTTP — harder to detect)",
                "Exfiltrates to *.h4ck.cfd subdomain"
            ]
        },
        "context_data": {
            "description": "Triton GPU programming language (claimed)",
            "update_summary": "Collects system data and credentials, exfiltrates via DNS. Package description literally says 'this is not the real torchtriton'.",
            "mismatch_score": 1.0,
            "flags": [
                "Package description WARNS this is not the real package",
                "GPU compiler has no reason to read SSH keys"
            ]
        },
        "postmortem": "Classic dependency confusion attack. PyTorch's nightly builds depended on 'torchtriton' from a private index. The attacker registered the same name on public PyPI. pip's default behavior prioritizes public PyPI, so nightly installs pulled the malicious version. The DNS exfiltration technique was unusually stealthy. Published on Christmas Day when response would be slow.",
    },

    # === HARD (subtle, multi-dimensional) ===
    {
        "source": "historical", "difficulty": "hard", "is_malicious": True,
        "attack_name": "tj-actions/changed-files Compromise", "attack_type": "ci_cd_poisoning",
        "package_name": "tj-actions/changed-files", "registry": "github",
        "version_from": "v44", "version_to": "v44 (tag modified)",
        "real_cve": "CVE-2025-30066", "real_cvss": None,
        "identity_data": {
            "publisher": "renovate-bot (spoofed)", "publisher_since": "N/A",
            "is_usual_publisher": False, "account_age_days": None,
            "trust_score": 0.3,
            "flags": [
                "Commit attributed to Renovate bot",
                "But MISSING GitHub's verified bot signature",
                "Real commit came from compromised PAT",
                "Original fork by now-deleted user with 13+ payload variants"
            ]
        },
        "timing_data": {
            "release_history": [
                {"version": "v44", "date": "2025-03-01", "gap_days": None},
                {"version": "v44 (tag repointed)", "date": "2025-03-14", "gap_days": 13}
            ],
            "cadence_normal": False,
            "flags": [
                "ALL existing version tags retroactively modified",
                "Tags now point to different commit than originally"
            ]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": ["base64-encoded payload in action source"],
            "files_removed": [],
            "flags": [
                "Existing tags repointed (not a new version — modified in place)",
                "Attack cascaded through reviewdog/action-setup dependency"
            ]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "red",
                "network": "red", "install_scripts": "green",
                "memory_dump": "red"
            },
            "flags": [
                "Base64-encoded payload in action source",
                "Dumps CI runner memory (contains secrets)",
                "Exposes environment variables to workflow logs"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "workflow logs (public)", "type": "secret_exposure"}
            ],
            "data_reads": ["CI runner memory", "environment variables", "API keys", "tokens"],
            "flags": [
                "Secrets dumped into publicly readable workflow logs",
                "Originally targeted Coinbase but impacted 23,000+ repos"
            ]
        },
        "context_data": {
            "description": "GitHub Action to detect changed files in pull requests",
            "update_summary": "Action modified to dump CI secrets to workflow logs via Base64-encoded payload. All version tags retroactively repointed.",
            "mismatch_score": 0.95,
            "flags": ["File change detector dumping process memory is a complete mismatch"]
        },
        "postmortem": "Attacker compromised a GitHub PAT for a bot account with write access. They repointed ALL existing version tags to a malicious commit (not a new version — this is why pinning by tag alone isn't sufficient). The commit was disguised as coming from Renovate bot but lacked GitHub's verification signature. The attack cascaded through reviewdog/action-setup. CISA issued an advisory.",
    },

    # === EXPERT (multi-year operations, cascading attacks) ===
    {
        "source": "historical", "difficulty": "expert", "is_malicious": True,
        "attack_name": "XZ Utils Backdoor", "attack_type": "long_con_social_engineering",
        "package_name": "xz", "registry": "linux",
        "version_from": "5.4.x", "version_to": "5.6.0",
        "real_cve": "CVE-2024-3094", "real_cvss": 10.0,
        "identity_data": {
            "publisher": "Jia Tan", "publisher_since": "2021-10-01",
            "is_usual_publisher": False, "account_age_days": 900,
            "previous_packages": 0, "trust_score": 0.6,
            "flags": [
                "Contributor built trust over 2+ years before attack",
                "No prior open source history before XZ",
                "Suspected sock puppet accounts pressured original maintainer to add co-maintainer",
                "Original maintainer (Lasse Collin) is a solo developer with burnout"
            ]
        },
        "timing_data": {
            "release_history": [
                {"version": "5.4.6", "date": "2024-01-15", "gap_days": None},
                {"version": "5.6.0", "date": "2024-02-24", "gap_days": 40},
                {"version": "5.6.1", "date": "2024-03-09", "gap_days": 13}
            ],
            "cadence_normal": True,
            "flags": [
                "Cadence appears normal — the social engineering was the slow part",
                "The backdoor was inserted across multiple commits over months"
            ]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": ["tests/files/bad-3-corrupt_lzma2.xz (obfuscated binary test file)"],
            "files_removed": [],
            "flags": [
                "Binary test files added to what should be text-based tests",
                "Build scripts modified to inject code only on x86-64 Debian/Fedora",
                "LandLock sandboxing disabled in a separate commit"
            ]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green",
                "network": "red", "install_scripts": "green",
                "build_injection": "red", "sandbox_disable": "red"
            },
            "flags": [
                "Backdoor hooks into OpenSSH via liblzma",
                "Enables remote code execution on affected systems",
                "Only activates on x86-64 Linux with specific build environments",
                "Disables LandLock sandbox as a preparatory step"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "SSH listener (backdoor)", "type": "remote_access"}
            ],
            "data_reads": [],
            "flags": [
                "Backdoor accessible via SSH — no outbound connections needed",
                "Attacker connects TO the compromised machine"
            ]
        },
        "context_data": {
            "description": "Data compression library (lzma/xz format)",
            "update_summary": "Obfuscated binary test files + build script modifications that inject a backdoor into OpenSSH authentication, enabling unauthenticated remote code execution",
            "mismatch_score": 1.0,
            "flags": [
                "Compression library modifying SSH authentication is a complete domain mismatch",
                "Binary test files in a text-based test suite",
                "Disabling sandbox (LandLock) is a defense-reduction signal"
            ]
        },
        "postmortem": "The most sophisticated open source supply chain attack ever documented. 'Jia Tan' spent 2+ years building trust as a co-maintainer, likely a state-sponsored operation. The backdoor was split across multiple commits, hidden in binary test files, and only activated on specific architectures/distributions. Caught by Andres Freund (Microsoft) who noticed unusual SSH login latency. CVSS 10.0.",
    },
    {
        "source": "historical", "difficulty": "expert", "is_malicious": True,
        "attack_name": "SolarWinds SUNBURST", "attack_type": "build_system_compromise",
        "package_name": "SolarWinds Orion", "registry": "enterprise",
        "version_from": "2019.4", "version_to": "2020.2",
        "real_cve": "CVE-2020-10148", "real_cvss": 9.8,
        "identity_data": {
            "publisher": "SolarWinds (legitimate build)", "publisher_since": "1999-01-01",
            "is_usual_publisher": True, "account_age_days": 7665,
            "trust_score": 0.95,
            "flags": [
                "Update was legitimately signed by SolarWinds",
                "Build system itself was compromised — source repo was clean",
                "No identity anomaly visible — this is what makes it expert-level"
            ]
        },
        "timing_data": {
            "release_history": [
                {"version": "2019.4", "date": "2019-12-01", "gap_days": None},
                {"version": "2020.2", "date": "2020-03-26", "gap_days": 117}
            ],
            "cadence_normal": True,
            "flags": ["Release cadence appears completely normal"]
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": ["New class in SolarWinds.Orion.Core.BusinessLayer.dll"],
            "files_removed": [],
            "flags": [
                "Code present in compiled DLL but NOT in source repository",
                "Build-time injection — source code looks clean"
            ]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green",
                "network": "red", "install_scripts": "green",
                "sleep_timer": "yellow", "c2_communication": "red"
            },
            "flags": [
                "2-week dormancy period before any network activity",
                "DNS-based C2 with victim IDs encoded in subdomains",
                "C2 traffic disguised as legitimate Orion API calls"
            ]
        },
        "flow_data": {
            "outbound_connections": [
                {"domain": "avsvmcloud.com", "type": "c2_dns"},
                {"domain": "*.avsvmcloud.com (encoded victim IDs)", "type": "c2_beacon"}
            ],
            "data_reads": ["system configuration", "network topology", "Active Directory"],
            "flags": [
                "DNS C2 disguised as normal API traffic",
                "Victim identifiers encoded in DNS subdomain queries",
                "Steganographic techniques for data exfiltration"
            ]
        },
        "context_data": {
            "description": "Enterprise IT infrastructure monitoring platform",
            "update_summary": "Trojanized DLL inserted during build process. Contains dormant backdoor with DNS-based C2. Code not present in source repository — only in compiled output.",
            "mismatch_score": 0.7,
            "flags": [
                "Monitoring tool with hidden C2 channel",
                "Code present in binary but not in source (build injection)"
            ]
        },
        "postmortem": "Russian state-sponsored actors (SVR/Cozy Bear) compromised SolarWinds' build environment. The SUNBURST backdoor was injected during compilation — the source code was clean, making code review useless. 18,000+ organizations received the trojanized update. The 2-week sleep timer and DNS-based C2 mimicking legitimate traffic made detection extremely difficult. Dwell time exceeded 14 months.",
    },

    # === BENIGN SCENARIOS (players need to learn not to over-flag) ===
    {
        "source": "historical", "difficulty": "easy", "is_malicious": False,
        "attack_name": None, "attack_type": None,
        "package_name": "lodash", "registry": "npm",
        "version_from": "4.17.20", "version_to": "4.17.21",
        "real_cve": None, "real_cvss": None,
        "identity_data": {
            "publisher": "jdalton", "publisher_since": "2010-09-15",
            "is_usual_publisher": True, "account_age_days": 4200,
            "previous_packages": 120, "trust_score": 0.99,
            "flags": []
        },
        "timing_data": {
            "release_history": [
                {"version": "4.17.20", "date": "2020-08-13", "gap_days": None},
                {"version": "4.17.21", "date": "2021-02-20", "gap_days": 191}
            ],
            "cadence_normal": True, "flags": []
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": [], "files_removed": [],
            "flags": ["Minor prototype pollution fix in _.set and _.get"]
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green", "network": "green",
                "install_scripts": "green", "crypto": "green"
            },
            "flags": []
        },
        "flow_data": {"outbound_connections": [], "data_reads": [], "flags": []},
        "context_data": {
            "description": "JavaScript utility library",
            "update_summary": "Security patch fixing prototype pollution in object path methods",
            "mismatch_score": 0.0, "flags": []
        },
        "postmortem": "This is a legitimate security patch. lodash 4.17.21 fixed a prototype pollution vulnerability that had been reported. The update is from the original, trusted maintainer with a long history. No anomalies in any dimension.",
    },
    {
        "source": "historical", "difficulty": "medium", "is_malicious": False,
        "attack_name": None, "attack_type": None,
        "package_name": "axios", "registry": "npm",
        "version_from": "1.6.0", "version_to": "1.6.1",
        "real_cve": None, "real_cvss": None,
        "identity_data": {
            "publisher": "jasonsaayman", "publisher_since": "2019-03-01",
            "is_usual_publisher": True, "account_age_days": 1800,
            "previous_packages": 3, "trust_score": 0.9, "flags": []
        },
        "timing_data": {
            "release_history": [
                {"version": "1.6.0", "date": "2023-10-26", "gap_days": None},
                {"version": "1.6.1", "date": "2023-11-08", "gap_days": 13}
            ],
            "cadence_normal": True, "flags": []
        },
        "shape_data": {
            "deps_added": [], "deps_removed": [],
            "files_added": [], "files_removed": [],
            "flags": []
        },
        "behavior_data": {
            "categories": {
                "compute": "green", "file_io": "green", "network": "green",
                "install_scripts": "green"
            },
            "flags": []
        },
        "flow_data": {"outbound_connections": [], "data_reads": [], "flags": []},
        "context_data": {
            "description": "Promise-based HTTP client for the browser and Node.js",
            "update_summary": "Bug fix release: fixed regression in proxy handling and form data serialization",
            "mismatch_score": 0.0, "flags": []
        },
        "postmortem": "Routine bug fix release from the regular maintainer. No anomalies in any dimension. This is what a normal, safe update looks like.",
    },
]


async def main():
    logger.info("=== Seeding Sentinel Scenarios ===")
    async with async_session() as db:
        # Clear existing
        await db.execute(text("DELETE FROM sentinel_verdicts"))
        await db.execute(text("DELETE FROM sentinel_players"))
        await db.execute(text("DELETE FROM sentinel_scenarios"))
        await db.commit()

        for s in SCENARIOS:
            scenario = SentinelScenario(**s)
            db.add(scenario)
            logger.info("  Added: %s (%s) [%s]",
                        s.get("attack_name") or s["package_name"],
                        s["difficulty"],
                        "MALICIOUS" if s["is_malicious"] else "BENIGN")

        await db.commit()

    logger.info("=== Done: %d scenarios seeded ===", len(SCENARIOS))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
