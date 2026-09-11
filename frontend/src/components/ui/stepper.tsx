import { cn } from "../../lib/utils";

export interface Step {
  key: string;
  label: string;
}

export function Stepper({
  steps,
  current,
  className,
}: {
  steps: Step[];
  current: number;
  className?: string;
}) {
  return (
    <ol
      className={cn("flex items-center gap-2 text-sm", className)}
      aria-label="Workflow steps"
    >
      {steps.map((step, i) => {
        const active = i === current;
        const done = i < current;
        return (
          <li key={step.key} className="flex items-center gap-2">
            <span
              aria-current={active ? "step" : undefined}
              className={
                done
                  ? "text-success"
                  : active
                    ? "text-text"
                    : "text-text-faint"
              }
            >
              <span aria-hidden className="mr-1 font-mono text-xs">
                {i + 1}
              </span>
              {step.label}
            </span>
            {i < steps.length - 1 && (
              <span className="text-text-faint" aria-hidden>
                /
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}