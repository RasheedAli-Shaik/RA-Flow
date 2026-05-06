import type { ViewerMode } from "@/types";

const MODES: ViewerMode[] = ["geometry", "pressure", "streamlines", "optimization"];

type Props = {
  mode: ViewerMode;
  onChange: (mode: ViewerMode) => void;
};

export function ModeToggle({ mode, onChange }: Props) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {MODES.map((candidate) => (
        <button
          key={candidate}
          type="button"
          onClick={() => onChange(candidate)}
          className={`rounded-2xl border px-3 py-2 text-left text-sm capitalize transition ${
            candidate === mode
              ? "border-neon bg-neon/15 text-neon shadow-glow"
              : "border-white/10 bg-white/5 text-paper/70 hover:border-frost/50 hover:text-paper"
          }`}
        >
          {candidate}
        </button>
      ))}
    </div>
  );
}

