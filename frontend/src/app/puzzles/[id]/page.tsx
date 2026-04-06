"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPuzzle, submitPuzzleAttempt } from "@/lib/api";
import type { Puzzle } from "@/lib/types";
import { cn } from "@/lib/utils";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  let id = localStorage.getItem("ghost-session-id");
  if (!id) { id = crypto.randomUUID(); localStorage.setItem("ghost-session-id", id); }
  return id;
}

const GAME_LABELS: Record<string, { label: string; color: string }> = {
  maze: { label: "Maze Escape", color: "text-emerald-400" },
  parser: { label: "Code Cracker", color: "text-amber-400" },
  timing: { label: "Timing Heist", color: "text-rose-400" },
  routing: { label: "Route Runner", color: "text-sky-400" },
  gatekeeper: { label: "Gatekeeper", color: "text-violet-400" },
  factory: { label: "Factory Hack", color: "text-orange-400" },
  blueprint: { label: "Blueprint", color: "text-cyan-400" },
};

export default function PuzzlePlayPage() {
  const params = useParams();
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [loading, setLoading] = useState(true);
  const [solved, setSolved] = useState(false);
  const [resultData, setResultData] = useState<any>(null);
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

  const handleComplete = async (didSolve: boolean, moves?: number, solutionPath?: any) => {
    if (!puzzle) return;
    const timeTaken = (Date.now() - startTime.current) / 1000;
    try {
      const res = await submitPuzzleAttempt(puzzle.id, {
        session_id: getSessionId(),
        solved: didSolve,
        time_taken_secs: timeTaken,
        moves,
        solution_path: solutionPath,
      });
      setSolved(didSolve);
      setResultData(res);
    } catch (e) {
      console.error("Failed to submit attempt:", e);
    }
  };

  if (loading || !puzzle) {
    return <div className="text-muted-foreground/50 text-sm">Loading puzzle...</div>;
  }

  const gl = GAME_LABELS[puzzle.game_type] || { label: puzzle.game_type, color: "text-foreground/60" };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in">
        <Link href="/puzzles" className="text-[12px] text-muted-foreground/60 hover:text-foreground/50 transition-colors">
          &larr; All Puzzles
        </Link>
        <div className="flex items-center gap-2 mt-3 mb-1">
          <span className={cn("text-[11px] font-medium uppercase tracking-wider", gl.color)}>{gl.label}</span>
          <div className="flex gap-0.5 ml-2">
            {Array.from({ length: 5 }).map((_, j) => (
              <div key={j} className={cn("h-1.5 w-1.5 rounded-full", j < puzzle.difficulty ? "bg-foreground/25" : "bg-foreground/[0.06]")} />
            ))}
          </div>
        </div>
        <h1 className="text-xl sm:text-2xl font-semibold tracking-tight gradient-text">{puzzle.title}</h1>
      </div>

      {/* Flavor text */}
      <div className="rounded-2xl glass p-6 animate-fade-in animate-fade-in-delay-1">
        <p className="text-[14px] text-foreground/60 leading-relaxed">{puzzle.flavor_text}</p>
      </div>

      {/* Game Area */}
      {!resultData ? (
        <div className="animate-fade-in animate-fade-in-delay-2">
          <GameRenderer
            gameType={puzzle.game_type}
            levelData={puzzle.level_data}
            onComplete={handleComplete}
          />
        </div>
      ) : (
        /* Results */
        <div className="space-y-4 animate-fade-in">
          <div className={cn(
            "rounded-2xl p-8 text-center",
            solved ? "bg-emerald-500/10 border border-emerald-500/20" : "bg-foreground/[0.03] border border-foreground/10"
          )}>
            <p className={cn("text-3xl font-bold", solved ? "text-emerald-400" : "text-foreground/50")}>
              {solved ? "Solved!" : "Not this time"}
            </p>
            {resultData.time_taken_secs && (
              <p className="text-[13px] text-muted-foreground/50 mt-2 font-mono">
                {resultData.time_taken_secs.toFixed(1)}s
                {resultData.your_rank && ` — #${resultData.your_rank} fastest`}
              </p>
            )}
            <p className="text-[12px] text-muted-foreground/40 mt-1">
              {resultData.total_attempts} total attempts · {(resultData.solve_rate * 100).toFixed(0)}% solve rate
            </p>
          </div>

          {/* Solve rate bar */}
          <div className="rounded-xl glass p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium">Community Solve Rate</span>
              <span className={cn("text-[13px] font-mono font-medium",
                resultData.solve_rate > 0.6 ? "text-emerald-400" :
                resultData.solve_rate > 0.3 ? "text-amber-400" : "text-rose-400"
              )}>
                {(resultData.solve_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-foreground/[0.05] overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all duration-1000",
                  resultData.solve_rate > 0.6 ? "bg-emerald-500/50" :
                  resultData.solve_rate > 0.3 ? "bg-amber-500/50" : "bg-rose-500/50"
                )}
                style={{ width: `${resultData.solve_rate * 100}%` }}
              />
            </div>
            <p className="text-[10px] text-muted-foreground/30 mt-2">
              Higher solve rate = vulnerability is more easily exploitable
            </p>
          </div>

          <div className="flex gap-3">
            <Link
              href="/puzzles"
              className="flex-1 rounded-xl glass px-4 py-3 text-center text-[13px] text-foreground/60 hover:bg-foreground/[0.03] transition-all"
            >
              More Puzzles
            </Link>
            <button
              onClick={() => { setResultData(null); startTime.current = Date.now(); }}
              className="flex-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-4 py-3 text-[13px] font-medium hover:bg-emerald-500/20 transition-all"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="flex gap-4 text-[11px] text-muted-foreground/30 animate-fade-in">
        <span>{puzzle.total_attempts} total plays</span>
        {puzzle.par_time_secs && <span>Par: {puzzle.par_time_secs}s</span>}
        {puzzle.avg_solve_time && <span>Avg solve: {puzzle.avg_solve_time.toFixed(0)}s</span>}
      </div>
    </div>
  );
}

/**
 * GameRenderer — renders the appropriate interactive game based on game_type.
 * Each game type gets its own component. The level_data drives the game configuration.
 */
function GameRenderer({
  gameType,
  levelData,
  onComplete,
}: {
  gameType: string;
  levelData: Record<string, unknown>;
  onComplete: (solved: boolean, moves?: number, path?: any) => void;
}) {
  // For V1, render a universal interactive game based on level_data
  // Future: each game_type gets a dedicated React component with Canvas/WebGL
  return (
    <div className="rounded-2xl glass p-8 space-y-6">
      <div className="text-center">
        <p className="text-[11px] text-muted-foreground/60 uppercase tracking-wider font-medium mb-4">
          Interactive Game — {gameType.toUpperCase()}
        </p>

        {/* Level data visualization */}
        <div className="rounded-xl bg-foreground/[0.02] border border-foreground/[0.04] p-6 text-left max-h-96 overflow-y-auto">
          <LevelVisualizer gameType={gameType} data={levelData} />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => onComplete(true, undefined, { method: "manual" })}
          className="flex-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-4 py-3 text-[14px] font-medium hover:bg-emerald-500/20 transition-all"
        >
          I found the solution
        </button>
        <button
          onClick={() => onComplete(false)}
          className="flex-1 rounded-xl glass px-4 py-3 text-[14px] text-foreground/50 hover:bg-foreground/[0.03] transition-all"
        >
          Can't solve it
        </button>
      </div>
    </div>
  );
}

/**
 * LevelVisualizer — renders a visual representation of the game level data.
 * This is the foundation that will be replaced with interactive game engines.
 */
function LevelVisualizer({ gameType, data }: { gameType: string; data: Record<string, unknown> }) {
  if (gameType === "maze" && data.grid) {
    const grid = data.grid as number[][];
    const start = data.start as number[] | undefined;
    const goal = data.goal as number[] | undefined;
    return (
      <div className="space-y-1">
        {grid.map((row, y) => (
          <div key={y} className="flex gap-0.5">
            {row.map((cell, x) => {
              const isStart = start && start[0] === x && start[1] === y;
              const isGoal = goal && goal[0] === x && goal[1] === y;
              return (
                <div
                  key={x}
                  className={cn(
                    "w-6 h-6 rounded-sm text-[8px] flex items-center justify-center font-bold",
                    cell === 1 ? "bg-foreground/20" :
                    isStart ? "bg-emerald-500/40 text-emerald-300" :
                    isGoal ? "bg-amber-500/40 text-amber-300" :
                    "bg-foreground/[0.03]"
                  )}
                >
                  {isStart ? "S" : isGoal ? "G" : cell === 1 ? "" : ""}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    );
  }

  if (gameType === "parser" && data.parser_rules) {
    return (
      <div className="space-y-3">
        <p className="text-[12px] text-foreground/50">Type input below. Watch how the machine interprets it:</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Your Input</p>
            <div className="bg-foreground/[0.03] rounded-lg p-3 h-20 text-[13px] text-foreground/60 font-mono">
              {(data.input_field as string) || "..."}
            </div>
          </div>
          <div>
            <p className="text-[10px] text-muted-foreground/40 uppercase mb-1">Machine Sees</p>
            <div className="bg-foreground/[0.03] rounded-lg p-3 h-20 text-[13px] font-mono">
              <span className="text-sky-400">data</span>
            </div>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground/40">Goal: make <span className="text-rose-400">red (instruction)</span> text appear in the machine view</p>
      </div>
    );
  }

  if (gameType === "timing") {
    const window = (data.window_ms as number) || 100;
    return (
      <div className="space-y-3 text-center">
        <p className="text-[12px] text-foreground/50">Two conveyor belts. Swap the item during the inspection gap.</p>
        <div className="flex justify-center gap-4">
          <div className="w-32 h-8 rounded bg-foreground/[0.05] relative overflow-hidden">
            <div className="absolute inset-y-0 left-0 w-1/3 bg-emerald-500/20 animate-pulse" />
          </div>
          <div className="w-32 h-8 rounded bg-foreground/[0.05] relative overflow-hidden">
            <div className="absolute inset-y-0 right-0 w-1/3 bg-rose-500/20 animate-pulse" />
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground/40">Timing window: {window}ms</p>
      </div>
    );
  }

  // Default: show the level data as structured info
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <span className="text-[10px] text-muted-foreground/40 uppercase">{key.replace(/_/g, " ")}</span>
          <pre className="text-[11px] text-foreground/50 font-mono mt-0.5 overflow-x-auto">
            {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
}
