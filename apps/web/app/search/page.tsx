"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { EmptyState, Spinner } from "@/components/ui";

function SearchInner() {
  const params = useSearchParams();
  const q = params.get("q") || "";
  const [results, setResults] = useState<{ tender_id: string; title: string; score: number; matched_fields: string[] }[] | null>(null);

  useEffect(() => {
    if (!q) return;
    setResults(null);
    api.search(q).then((r) => setResults(r.results));
  }, [q]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 760 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700 }}>
        Search results for &ldquo;{q}&rdquo;
      </h1>
      {results === null && (
        <div style={{ display: "flex", gap: 8, color: "var(--muted)" }}>
          <Spinner size={14} /> Searching…
        </div>
      )}
      {results?.length === 0 && <EmptyState title="No matches found" sub="Try a different keyword, certification name, or product category." />}
      {results?.map((r) => (
        <Link key={r.tender_id} href={`/tenders/${r.tender_id}`} className="card" style={{ padding: 14, display: "block" }}>
          <div style={{ fontWeight: 700, fontSize: 13.5 }}>{r.title}</div>
          <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 4 }}>
            Matched in: {r.matched_fields.join(", ")} &nbsp;•&nbsp; relevance score {r.score}
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div style={{ color: "var(--muted)" }}>Loading…</div>}>
      <SearchInner />
    </Suspense>
  );
}
