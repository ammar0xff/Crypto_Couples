import { NavLink, Link } from "react-router-dom";
import { Images, Link2, ListTree, Settings, ShieldCheck } from "lucide-react";

import { cn } from "../../lib/utils";

const NAV_ITEMS = [
  { to: "/split", label: "Split", icon: Images },
  { to: "/reveal", label: "Reveal", icon: Link2 },
  { to: "/operations", label: "Operations", icon: ListTree },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function TopBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/95 backdrop-blur supports-[backdrop-filter]:bg-bg/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link
          to="/split"
          className="flex shrink-0 items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded-md"
        >
          <span className="flex size-7 items-center justify-center rounded bg-primary/15">
            <ShieldCheck className="size-4 text-primary" aria-hidden />
          </span>
          <span className="font-mono text-sm tracking-tight text-text">
            crypto_couples
          </span>
        </Link>

        <nav className="flex items-center gap-1" aria-label="Primary">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
                  isActive
                    ? "bg-accent text-text"
                    : "text-text-muted hover:bg-accent/60 hover:text-text",
                )
              }
            >
              <Icon aria-hidden className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>
      <footer className="border-t border-border">
        <p className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 text-xs text-text-faint sm:px-6 lg:px-8">
          <span>demo-grade visual crypto, for demonstration not real secrets</span>
          <span className="font-mono text-[11px]">shake: single-machine, in-memory, metadata-only history</span>
        </p>
      </footer>
    </div>
  );
}