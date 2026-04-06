"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPuzzle, votePuzzle } from "@/lib/api";
import type { Puzzle, PuzzleResult } from "@/lib/types";
import { RegistryBadge } from "@/components/analysis/registry-badge";
import { cn } from "@/lib/utils";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("ghost-session-id", id);
  }
  return id;
}

const CHALLENGE_LABELS: Record<string, string> = {
  reachability: "Reachability Challenge",
  exploitability: "Exploitability Challenge",
  impact: "Impact Challenge",
};

export default function PuzzleSolvePage() {
  const params = useParams();
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [result, setResult] = useState<PuzzleResult | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [confidence, setConfidence] = useState(0.7);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const startTime = useRef(Date.now());

  useEffect(() => {
    async function load() {
      try {
        const data = await getPuzzle(params.id as string);
        setPuzzle(data);
        startTime.current = Date.now();
      } catch (e) {
        console.error("Failed to load puzzle:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  const handleSubmit = async () => {
    if (selected === null || !puzzle) return;
    setSubmitting(true);
    try {
      const timeTaken = (Date.now() - startTime.current) / 1000;
      const res = await votePuzzle(puzzle.id, {
        selected_index: selected,
        confidence,
        time_taken_secs: timeTaken,
        session_id: getSessionId(),
      });
      setResult(res);
    } catch (e: any) {
      if (e.message?.includes("409")) {
        alert("You've already voted on this puzzle.");
      } else {
        console.error("Vote failed:", e);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !puzzle) {
    return <div className="text-muted-foreground/50 text-sm">Loading...</div>;
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in">
        <Link href="/puzzles" className="text-[12px] text-muted-foreground/60 hover:text-foreground/50 transition-colors">
          &larr; All Challenges
        </Link>
        <div className="flex items-center gap-2 mt-3 mb-2 flex-wrap">
          <span className={cn(
            "text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full border",
            puzzle.challenge_type === "reachability" ? "text-sky-400 bg-sky-500/10 border-sky-500/20" :
            puzzle.challenge_type === "exploitability" ? "text-orange-400 bg-orange-500/10 border-orange-500/20" :
            "text-violet-400 bg-violet-500/10 border-violet-500/20"
          )}>
            {CHALLENGE_LABELS[puzzle.challenge_type] || puzzle.challenge_type}
          </span>
          {puzzle.package_registry && <RegistryBadge registry={puzzle.package_registry} />}
          <span className="text-[11px] text-muted-foreground/50">{puzzle.package_name}</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-semibold tracking-tight gradient-text">
          {puzzle.title}
        </h1>
      </div>

      {/* Scenario */}
      <div className="rounded-2xl glass p-6 animate-fade-in animate-fade-in-delay-1">
        <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">Evidence</p>
        <div className="text-[13px] text-foreground/60 leading-relaxed whitespace-pre-wrap">
          {puzzle.scenario}
        </div>
      </div>

      {/* Options */}
      {!result ? (
        <div className="space-y-4 animate-fade-in animate-fade-in-delay-2">
          <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium">Your Assessment</p>
          <div className="space-y-2">
            {puzzle.options.map((opt, i) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className={cn(
                  "w-full text-left rounded-xl glass p-4 transition-all duration-200",
                  selected === i
                    ? "ring-2 ring-emerald-500/40 bg-emerald-500/[0.06]"
                    : "hover:bg-foreground/[0.03]"
                )}
              >
                <div className="flex items-start gap-3">
                  <span className={cn(
                    "shrink-0 h-6 w-6 rounded-full flex items-center justify-center text-[11px] font-medium border transition-all",
                    selected === i
                      ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                      : "bg-foreground/[0.04] border-foreground/10 text-muted-foreground/50"
                  )}>
                    {String.fromCharCode(65 + i)}
                  </span>
                  <span className="text-[13px] text-foreground/70">{opt.text}</span>
                </div>
              </button>
            ))}
          </div>

          {/* Confidence */}
          <div className="rounded-xl glass p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium">Confidence</span>
              <span className="text-[13px] text-foreground/60 font-mono">{(confidence * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={confidence * 100}
              onChange={(e) => setConfidence(Number(e.target.value) / 100)}
              className="w-full accent-emerald-500"
            />
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={selected === null || submitting}
            className={cn(
              "w-full rounded-xl px-5 py-3 text-[14px] font-medium transition-all duration-300",
              "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
              "hover:bg-emerald-500/20 hover:border-emerald-500/30",
              "disabled:opacity-30 disabled:cursor-not-allowed"
            )}
          >
            {submitting ? "Submitting..." : "Submit Answer"}
          </button>
        </div>
      ) : (
        /* Results */
        <div className="space-y-4 animate-fade-in">
          {/* Result banner */}
          <div className={cn(
            "rounded-2xl p-6 text-center",
            result.user_was_correct
              ? "bg-emerald-500/10 border border-emerald-500/20"
              : "bg-red-500/10 border border-red-500/20"
          )}>
            <p className={cn(
              "text-2xl font-bold",
              result.user_was_correct ? "text-emerald-400" : "text-red-400"
            )}>
              {result.user_was_correct ? "Correct!" : "Incorrect"}
            </p>
            <p className="text-[13px] text-foreground/50 mt-1">
              {result.total_votes} total vote{result.total_votes !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Options with results */}
          <div className="space-y-2">
            {result.options.map((opt, i) => {
              const voteCount = result.consensus[i] || 0;
              const pct = result.total_votes > 0 ? (voteCount / result.total_votes) * 100 : 0;
              return (
                <div
                  key={i}
                  className={cn(
                    "relative rounded-xl glass p-4 overflow-hidden",
                    opt.is_correct && "ring-2 ring-emerald-500/40",
                    selected === i && !opt.is_correct && "ring-2 ring-red-500/40"
                  )}
                >
                  {/* Vote bar */}
                  <div
                    className={cn(
                      "absolute inset-y-0 left-0 opacity-10",
                      opt.is_correct ? "bg-emerald-500" : "bg-foreground"
                    )}
                    style={{ width: `${pct}%` }}
                  />
                  <div className="relative flex items-start gap-3">
                    <span className={cn(
                      "shrink-0 h-6 w-6 rounded-full flex items-center justify-center text-[11px] font-medium border",
                      opt.is_correct
                        ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                        : "bg-foreground/[0.04] border-foreground/10 text-muted-foreground/50"
                    )}>
                      {opt.is_correct ? "✓" : String.fromCharCode(65 + i)}
                    </span>
                    <span className="text-[13px] text-foreground/70 flex-1">{opt.text}</span>
                    <span className="text-[12px] text-muted-foreground/50 tabular-nums shrink-0">
                      {pct.toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Explanation */}
          <div className="rounded-2xl glass p-6">
            <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-3">Explanation</p>
            <p className="text-[13px] text-foreground/60 leading-relaxed">{result.explanation}</p>
          </div>

          {/* Link to vulnerability */}
          <Link
            href={`/vulnerabilities/${puzzle.vulnerability_id}`}
            className="block text-center text-[13px] text-emerald-400/70 hover:text-emerald-400 transition-colors"
          >
            View full vulnerability details &rarr;
          </Link>
        </div>
      )}
    </div>
  );
}
