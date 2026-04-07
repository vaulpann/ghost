import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="max-w-2xl space-y-10 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground/90">
          Why Ghost Resolver exists
        </h1>
        <p className="text-[13px] sm:text-[14px] text-muted-foreground/50 mt-2 leading-relaxed">
          The case for human-in-the-loop supply chain security
        </p>
      </div>

      {/* The Problem */}
      <section className="space-y-4">
        <h2 className="text-[17px] font-semibold text-foreground/80">AI detection is creating a new problem</h2>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          AI-powered vulnerability detection is one of the most exciting developments in security. Automated scanners can now analyze millions of package releases, flag suspicious code patterns, and detect supply chain attacks in near-real time. The throughput is incredible.
        </p>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          But there's a problem: <strong className="text-foreground/80">the signal-to-noise ratio is terrible.</strong> AI scanners generate mountains of findings — most of them false positives, edge cases, or technically-true-but-practically-irrelevant flags. Security teams are drowning in slop. A minified file triggers "obfuscation detected." A CI helper reads environment variables and gets flagged as "data exfiltration." A version bump with a new dependency becomes a "critical supply chain risk."
        </p>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          The result: alert fatigue. When everything is flagged, nothing is. The real attacks — the ones where a maintainer's npm token gets stolen and a postinstall script starts exfiltrating SSH keys — get buried under a pile of noise.
        </p>
      </section>

      {/* Our Approach */}
      <section className="space-y-4">
        <h2 className="text-[17px] font-semibold text-foreground/80">Humans are still the best validators</h2>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          Ghost runs an AI-powered supply chain monitor that watches 500+ packages across npm, PyPI, and GitHub. Every new release gets analyzed within 60 seconds. The AI is good at catching things that look wrong — but it still needs humans to confirm what <em>actually is</em> wrong.
        </p>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          We built Resolver because we think <strong className="text-foreground/80">the best way to validate security findings is to give real people real evidence and let them decide.</strong> Not multiple-choice quizzes. Not sanitized educational examples. Real packages, real version diffs, real maintainer histories, real behavioral signals — presented clearly so you can form your own judgment.
        </p>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          Think of it like <a href="https://fold.it" target="_blank" rel="noopener noreferrer" className="text-[#1e3a5f] hover:underline font-medium">Foldit</a> for supply chain security. Foldit proved that gamified citizen science could solve protein folding problems that computers alone couldn't crack. We believe the same principle applies here: a network of sharp-eyed developers reviewing package updates can catch what automated scanners miss — and filter out the noise they generate.
        </p>
      </section>

      {/* How It Works */}
      <section className="space-y-4">
        <h2 className="text-[17px] font-semibold text-foreground/80">How Resolver works</h2>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          Each challenge presents a real package update with 6 dimensions of evidence:
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[
            { name: "Identity", desc: "Who published it" },
            { name: "Timeline", desc: "When and how often" },
            { name: "Structure", desc: "What files changed" },
            { name: "Behavior", desc: "What the code does" },
            { name: "Data Flow", desc: "Where data goes" },
            { name: "Context", desc: "Does it make sense" },
          ].map((e) => (
            <div key={e.name} className="rounded-xl glass p-3">
              <p className="text-[13px] font-semibold text-foreground/80">{e.name}</p>
              <p className="text-[11px] text-muted-foreground/50 mt-0.5">{e.desc}</p>
            </div>
          ))}
        </div>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          You review the evidence. You make the call: safe, suspicious, or malicious. You submit your verdict with a confidence level. After submitting, you see whether you were right and what actually happened with the package.
        </p>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          Every challenge uses data pulled from real registries — real version histories, real maintainer info, real dependency trees. Some of these packages were actually compromised. Some were legitimate. Can you tell the difference?
        </p>
      </section>

      {/* The Vision */}
      <section className="space-y-4">
        <h2 className="text-[17px] font-semibold text-foreground/80">Where this is going</h2>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          Today, Resolver is a daily challenge. But the long-term goal is a real-time validation network. When Ghost's AI scanner flags a new release as suspicious, it should be able to surface that finding to a community of trained reviewers who can confirm or reject it within minutes — not hours or days.
        </p>
        <p className="text-[14px] text-muted-foreground/70 leading-[1.85]">
          Human consensus on top of AI detection. The scanner handles throughput, the community handles precision. Together, they catch more attacks with fewer false alarms. That's the system we're building.
        </p>
      </section>

      {/* CTA */}
      <section className="rounded-2xl glass p-6 sm:p-8">
        <h2 className="text-[17px] font-semibold text-foreground/80 mb-2">Ready to try it?</h2>
        <p className="text-[14px] text-muted-foreground/60 leading-relaxed mb-5">
          New challenges drop daily. No account required. Just evidence and your judgment.
        </p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-[#1e3a5f] px-6 py-3 text-[14px] font-semibold text-white hover:bg-[#2a4f7a] transition-colors"
        >
          Play Resolver
        </Link>
      </section>

      {/* Footer note */}
      <p className="text-[12px] text-muted-foreground/30 leading-relaxed pb-4">
        Ghost is built by <a href="https://x.com/pjvann" target="_blank" rel="noopener noreferrer" className="hover:text-muted-foreground/50">Paul Vann</a>.
        If you're working on supply chain security and want to collaborate, <a href="mailto:paul@validia.ai" className="hover:text-muted-foreground/50">get in touch</a>.
      </p>
    </div>
  );
}
