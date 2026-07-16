"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { ResultsPanel, AnalysisResult } from "../analyze/page";

const API_URL = "http://localhost:8000";

type HistoryItem = {
  id: string;
  smiles: string;
  target?: string;
  disease?: string;
  createdAt: string;
  patentRisk: string;
  retrievedPatentCount: number;
  analyzedPatentCount: number;
};

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  
  // Detail view state
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailResult, setDetailResult] = useState<AnalysisResult | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState("");

  // Filters & Search
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<string[]>([]);
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest");

  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await fetch(`${API_URL}/api/history?limit=100`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleOpenAnalysis = async (id: string) => {
    setSelectedId(id);
    setLoadingDetail(true);
    setDetailError("");
    try {
      const res = await fetch(`${API_URL}/api/history/${id}`);
      if (!res.ok) throw new Error("Failed to load analysis");
      const data = await res.json();
      
      const result: AnalysisResult = {
        smiles: data.smiles,
        target: data.target || null,
        disease: data.disease || null,
        patents: data.patents.map((p: any) => ({
          title: p.title,
          publication_number: p.patentNumber,
          assignee: p.assignee,
          publication_date: p.publicationDate,
          abstract: p.abstract,
          source: p.source,
          similarity_score: p.similarityScore,
          why_retrieved: p.aiExplanation || "",
          similarities: [], // Since aiExplanation is already assembled
          potential_overlap: "",
          confidence: p.confidence,
          risk_level: p.confidence >= 0.8 ? "low" : p.confidence >= 0.6 ? "medium" : "high" 
          // Wait, original risk_level was stored. We might need to store it or map it.
          // Since it wasn't saved explicitly in patent, we'll infer or just use medium for UI rendering
        })),
        executive_summary: data.report.executiveSummary,
        key_similar_patents: data.report.keySimilarPatents,
        novelty_concerns: data.report.noveltyConcerns,
        patents_requiring_review: data.report.manualReview,
        overall_recommendation: data.report.recommendation,
        recommendation_explanation: "",
        errors: []
      };
      
      // Let's patch the risk_level based on confidence for patents since we didn't save it directly in patent doc
      result.patents.forEach(p => {
          if (p.confidence >= 0.8) p.risk_level = "low";
          else if (p.confidence >= 0.6) p.risk_level = "medium";
          else p.risk_level = "high";
      });

      setDetailResult(result);
    } catch (err: any) {
      setDetailError(err.message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this analysis?")) return;
    try {
      const res = await fetch(`${API_URL}/api/history/${id}`, { method: "DELETE" });
      if (res.ok) {
        setHistory(prev => prev.filter(item => item.id !== id));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Are you sure you want to delete ALL analysis history? This cannot be undone.")) {
      setConfirmDeleteAll(false);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/history?confirm=true`, { method: "DELETE" });
      if (res.ok) {
        setHistory([]);
      }
    } catch (err) {
      console.error(err);
    }
    setConfirmDeleteAll(false);
  };

  const filteredHistory = useMemo(() => {
    let result = history;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(h => 
        h.smiles.toLowerCase().includes(q) || 
        (h.target && h.target.toLowerCase().includes(q)) || 
        (h.disease && h.disease.toLowerCase().includes(q))
      );
    }
    if (riskFilter.length > 0) {
      result = result.filter(h => riskFilter.includes(h.patentRisk));
    }
    result.sort((a, b) => {
      const da = new Date(a.createdAt).getTime();
      const db = new Date(b.createdAt).getTime();
      return sortOrder === "newest" ? db - da : da - db;
    });
    return result;
  }, [history, search, riskFilter, sortOrder]);

  const toggleRiskFilter = (risk: string) => {
    setRiskFilter(prev => prev.includes(risk) ? prev.filter(r => r !== risk) : [...prev, risk]);
  };

  const getRiskBadgeClasses = (risk: string) => {
    if (risk === "Low Patent Risk") return "badge-low";
    if (risk === "Requires Expert Review") return "badge-review";
    if (risk === "High Patent Risk") return "badge-high";
    return "badge-review";
  };

  // Detail View Rendering
  if (selectedId) {
    return (
      <>
        <nav>
          <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: "56px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
              <button 
                onClick={() => { setSelectedId(null); setDetailResult(null); }}
                style={{ background: "none", border: "none", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-secondary)" }}
              >
                ← Back to History
              </button>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-label)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Saved Analysis
            </span>
          </div>
        </nav>
        <main style={{ minHeight: "calc(100vh - 56px)", display: "flex", flexDirection: "column" }}>
          {loadingDetail ? (
            <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
              <div style={{ width: "40px", height: "40px", borderRadius: "50%", border: "2px solid var(--border)", borderTopColor: "var(--primary)", animation: "spin 1s linear infinite" }} />
            </div>
          ) : detailError ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--risk-high)" }}>{detailError}</div>
          ) : detailResult ? (
            <ResultsPanel result={detailResult} onReset={() => { setSelectedId(null); setDetailResult(null); }} />
          ) : null}
        </main>
      </>
    );
  }

  return (
    <>
      <nav>
        <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: "56px" }}>
          <Link href="/" style={{ textDecoration: "none" }}>
            <span style={{ fontFamily: "var(--font-heading)", fontWeight: 300, fontSize: "18px", color: "var(--primary)", letterSpacing: "-0.02em" }}>
              PatentPilot
            </span>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
            <Link href="/analyze" style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-secondary)", textDecoration: "none" }}>
              + New Analysis
            </Link>
            <Link href="/" style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-secondary)", textDecoration: "none" }}>
              ← Back to Home
            </Link>
          </div>
        </div>
      </nav>

      <main style={{ minHeight: "calc(100vh - 56px)", padding: "40px 0" }}>
        <div className="container">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px" }}>
            <div>
              <h1 className="font-heading" style={{ fontSize: "32px", color: "var(--heading)", marginBottom: "8px" }}>Analysis History</h1>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Browse and reopen previously saved FTO analyses.</p>
            </div>
            {history.length > 0 && (
              <button onClick={handleDeleteAll} className="btn-secondary" style={{ color: "var(--risk-high)", borderColor: "#fecaca" }}>
                Delete All
              </button>
            )}
          </div>

          {/* Toolbar */}
          <div style={{ display: "flex", gap: "16px", marginBottom: "32px", flexWrap: "wrap" }}>
            <input 
              type="text"
              placeholder="Search SMILES, Target, Disease..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field"
              style={{ maxWidth: "320px", flex: 1 }}
            />
            
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              {["Low Patent Risk", "Requires Expert Review", "High Patent Risk"].map(risk => (
                <button
                  key={risk}
                  onClick={() => toggleRiskFilter(risk)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "20px",
                    border: `1px solid ${riskFilter.includes(risk) ? "var(--primary)" : "var(--border)"}`,
                    background: riskFilter.includes(risk) ? "rgba(28,52,97,0.06)" : "var(--surface)",
                    fontSize: "12px",
                    cursor: "pointer",
                    color: riskFilter.includes(risk) ? "var(--primary)" : "var(--text-secondary)",
                    transition: "all 0.2s"
                  }}
                >
                  {risk}
                </button>
              ))}
            </div>

            <select 
              value={sortOrder} 
              onChange={(e) => setSortOrder(e.target.value as any)}
              className="input-field"
              style={{ width: "auto" }}
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
            </select>
          </div>

          {/* List */}
          {loadingList ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "20px" }}>
              {[1, 2, 3].map(i => (
                <div key={i} className="card skeleton" style={{ height: "200px" }} />
              ))}
            </div>
          ) : filteredHistory.length === 0 ? (
            <div className="card" style={{ padding: "60px 20px", textAlign: "center" }}>
              <div style={{ fontSize: "40px", marginBottom: "16px", opacity: 0.5 }}>📁</div>
              <h3 style={{ fontSize: "18px", color: "var(--heading)", marginBottom: "8px" }}>No history found</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "24px" }}>
                {search || riskFilter.length > 0 ? "Try adjusting your filters or search query." : "Analyses you run will automatically be saved here."}
              </p>
              {!search && riskFilter.length === 0 && (
                <Link href="/analyze" className="btn-primary">Run your first analysis</Link>
              )}
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "20px" }}>
              {filteredHistory.map(item => (
                <div 
                  key={item.id} 
                  className="card patent-card"
                  onClick={() => handleOpenAnalysis(item.id)}
                  style={{ cursor: "pointer", display: "flex", flexDirection: "column", padding: "20px" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                    <span className={getRiskBadgeClasses(item.patentRisk)}>{item.patentRisk}</span>
                    <button 
                      onClick={(e) => handleDelete(e, item.id)}
                      style={{ background: "none", border: "none", color: "var(--text-label)", cursor: "pointer", padding: "4px" }}
                      title="Delete"
                    >
                      ✕
                    </button>
                  </div>
                  
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--heading)", wordBreak: "break-all", marginBottom: "16px", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                    {item.smiles}
                  </div>

                  {(item.target || item.disease) && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginBottom: "16px" }}>
                      {item.target && <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}><b>Target:</b> {item.target}</span>}
                      {item.disease && <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}><b>Disease:</b> {item.disease}</span>}
                    </div>
                  )}

                  <div style={{ marginTop: "auto", borderTop: "1px solid var(--border-light)", paddingTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                        {new Date(item.createdAt).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}
                      </span>
                      <span style={{ fontSize: "10px", color: "var(--text-label)", fontFamily: "var(--font-mono)" }}>
                        {new Date(item.createdAt).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
                      </span>
                    </div>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--primary)", fontWeight: 500, background: "rgba(28,52,97,0.06)", padding: "4px 8px", borderRadius: "4px" }}>
                      {item.analyzedPatentCount} Patents
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
