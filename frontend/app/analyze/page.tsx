"use client";

import { useState, useRef, useCallback } from "react";
import Link from "next/link";

/* ─── Types ───────────────────────────────────────────── */
type AnalysisState = "input" | "loading" | "results" | "error";

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type Recommendation =
  | "proceed"
  | "proceed_with_caution"
  | "consult_ip_counsel"
  | "do_not_proceed";

export interface Patent {
  title: string;
  publication_number: string | null;
  assignee: string | null;
  publication_date: string | null;
  abstract: string | null;
  source: string | null;
  similarity_score: number | null;
  why_retrieved: string;
  similarities: string[];
  potential_overlap: string;
  confidence: number;
  risk_level: RiskLevel;
}

export interface AnalysisResult {
  smiles: string;
  target: string | null;
  disease: string | null;
  patents: Patent[];
  executive_summary: string;
  key_similar_patents: string[];
  novelty_concerns: string[];
  patents_requiring_review: string[];
  overall_recommendation: Recommendation;
  recommendation_explanation: string;
  errors: string[];
}

interface ProgressEvent {
  step: string;
  index: number;
  total: number;
}

/* ─── Helpers ─────────────────────────────────────────── */
export const RISK_CONFIG: Record<
  RiskLevel,
  { label: string; cls: string; color: string; bg: string; border: string }
> = {
  low: {
    label: "Low Risk",
    cls: "badge-low",
    color: "var(--risk-low)",
    bg: "var(--risk-low-bg)",
    border: "#bbf7d0",
  },
  medium: {
    label: "Manual Review",
    cls: "badge-review",
    color: "var(--risk-review)",
    bg: "var(--risk-review-bg)",
    border: "#fde68a",
  },
  high: {
    label: "High Risk",
    cls: "badge-high",
    color: "var(--risk-high)",
    bg: "var(--risk-high-bg)",
    border: "#fecaca",
  },
  critical: {
    label: "High Risk",
    cls: "badge-high",
    color: "var(--risk-high)",
    bg: "var(--risk-high-bg)",
    border: "#fecaca",
  },
};

export const REC_CONFIG: Record<
  Recommendation,
  { label: string; cls: string; color: string; bg: string; border: string }
> = {
  proceed: {
    label: "Proceed",
    cls: "badge-low",
    color: "var(--risk-low)",
    bg: "var(--risk-low-bg)",
    border: "#bbf7d0",
  },
  proceed_with_caution: {
    label: "Proceed with Caution",
    cls: "badge-review",
    color: "var(--risk-review)",
    bg: "var(--risk-review-bg)",
    border: "#fde68a",
  },
  consult_ip_counsel: {
    label: "Consult IP Counsel",
    cls: "badge-review",
    color: "var(--risk-review)",
    bg: "var(--risk-review-bg)",
    border: "#fde68a",
  },
  do_not_proceed: {
    label: "Do Not Proceed",
    cls: "badge-high",
    color: "var(--risk-high)",
    bg: "var(--risk-high-bg)",
    border: "#fecaca",
  },
};

const API_URL = "http://localhost:8000";

/* ─── Nav ─────────────────────────────────────────────── */
function Nav() {
  return (
    <nav>
      <div
        className="container"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "56px",
        }}
      >
        <Link href="/" style={{ textDecoration: "none" }}>
          <span
            style={{
              fontFamily: "var(--font-heading)",
              fontWeight: 300,
              fontSize: "18px",
              color: "var(--primary)",
              letterSpacing: "-0.02em",
            }}
          >
            PatentPilot
          </span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-label)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            FTO Analysis Workspace
          </span>
          <Link
            href="/history"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "13px",
              color: "var(--text-secondary)",
              textDecoration: "none",
            }}
          >
            History
          </Link>
          <Link
            href="/"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "13px",
              color: "var(--text-secondary)",
              textDecoration: "none",
            }}
          >
            ← Back to Home
          </Link>
        </div>
      </div>
    </nav>
  );
}

/* ─── Workflow Progress ───────────────────────────────── */
function WorkflowProgress({ currentState }: { currentState: AnalysisState }) {
  const steps = [
    { id: "search", label: "Search" },
    { id: "ranking", label: "Ranking" },
    { id: "ai", label: "AI Analysis" },
    { id: "report", label: "Report" },
  ];

  const getStepStatus = (stepId: string) => {
    if (currentState === "input") return "pending";
    if (currentState === "loading") {
      if (stepId === "search") return "done";
      if (stepId === "ranking") return "done";
      if (stepId === "ai") return "active";
      return "pending";
    }
    if (currentState === "results") return "done";
    return "pending";
  };

  return (
    <div className="workflow-progress">
      <div className="workflow-inner">
        {steps.map((step, i) => {
          const status = getStepStatus(step.id);
          return (
            <div key={step.id} className="workflow-step-wrapper">
              <div className={`workflow-step workflow-step--${status}`}>
                <span className="workflow-dot">
                  {status === "done" ? "✓" : status === "active" ? "◉" : "○"}
                </span>
                <span className="workflow-label">{step.label}</span>
              </div>
              {i < steps.length - 1 && (
                <div
                  className={`workflow-connector ${status === "done" ? "workflow-connector--done" : ""}`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Input Form ──────────────────────────────────────── */
function InputForm({
  onSubmit,
}: {
  onSubmit: (smiles: string, target: string, disease: string) => void;
}) {
  const [smiles, setSmiles] = useState("");
  const [target, setTarget] = useState("");
  const [disease, setDisease] = useState("");
  const [touched, setTouched] = useState(false);

  const isValid = smiles.trim().length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!isValid) return;
    onSubmit(smiles.trim(), target.trim(), disease.trim());
  };

  return (
    <section
      className="fade-in visible"
      style={{
        flex: 1,
        padding: "64px 0 80px",
        display: "flex",
        alignItems: "center",
      }}
    >
      <div className="container" style={{ maxWidth: "640px", width: "100%" }}>
        {/* Header */}
        <div style={{ marginBottom: "40px" }}>
          <p
            className="section-label"
            style={{ marginBottom: "12px" }}
          >
            New Analysis
          </p>
          <h1
            className="font-heading"
            style={{
              fontSize: "clamp(28px, 4vw, 42px)",
              lineHeight: 1.12,
              letterSpacing: "-0.025em",
              color: "var(--heading)",
              marginBottom: "12px",
            }}
          >
            Submit your molecule
          </h1>
          <p
            style={{
              fontSize: "15px",
              color: "var(--body-text)",
              lineHeight: 1.65,
              maxWidth: "480px",
            }}
          >
            Enter a SMILES string to begin an AI-assisted Freedom-to-Operate
            analysis. Patent retrieval and LLM reasoning typically take{" "}
            <span style={{ color: "var(--heading)", fontWeight: 500 }}>
              60–120 seconds
            </span>
            .
          </p>
        </div>

        {/* Form Card */}
        <div className="card" style={{ padding: "32px" }}>
          <form
            onSubmit={handleSubmit}
            style={{ display: "flex", flexDirection: "column", gap: "24px" }}
          >
            {/* SMILES */}
            <div>
              <label className="input-label" htmlFor="smiles-input">
                SMILES String{" "}
                <span style={{ color: "var(--risk-high)" }}>*</span>
              </label>
              <textarea
                id="smiles-input"
                className="input-field"
                placeholder="e.g. Cn1cnc2n(C)c(=O)n(C)c(=O)c12"
                value={smiles}
                onChange={(e) => setSmiles(e.target.value)}
                rows={3}
                style={{
                  resize: "vertical",
                  fontFamily: "var(--font-mono)",
                  fontSize: "13px",
                  ...(touched && !isValid
                    ? { borderColor: "var(--risk-high)" }
                    : {}),
                }}
                required
              />
              {touched && !isValid && (
                <p
                  style={{
                    fontSize: "12px",
                    color: "var(--risk-high)",
                    marginTop: "4px",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  A SMILES string is required.
                </p>
              )}
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--text-label)",
                  marginTop: "6px",
                  fontFamily: "var(--font-mono)",
                }}
              >
                Standard SMILES notation. Example: Caffeine is{" "}
                <code
                  style={{ color: "var(--text-muted)", fontSize: "11px" }}
                >
                  Cn1cnc2n(C)c(=O)n(C)c(=O)c12
                </code>
              </p>
            </div>

            {/* Optional Fields */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
              }}
              className="form-grid"
            >
              <div>
                <label className="input-label" htmlFor="target-input">
                  Biological Target{" "}
                  <span style={{ color: "var(--text-label)" }}>(optional)</span>
                </label>
                <input
                  id="target-input"
                  type="text"
                  className="input-field"
                  placeholder="e.g. EGFR Tyrosine Kinase"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                />
              </div>
              <div>
                <label className="input-label" htmlFor="disease-input">
                  Disease / Indication{" "}
                  <span style={{ color: "var(--text-label)" }}>(optional)</span>
                </label>
                <input
                  id="disease-input"
                  type="text"
                  className="input-field"
                  placeholder="e.g. Non-small cell lung cancer"
                  value={disease}
                  onChange={(e) => setDisease(e.target.value)}
                />
              </div>
            </div>

            {/* Info note */}
            <div
              style={{
                padding: "12px 14px",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderLeft: "3px solid var(--primary)",
                display: "flex",
                gap: "10px",
                alignItems: "flex-start",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--primary)",
                  fontWeight: 600,
                  marginTop: "1px",
                  whiteSpace: "nowrap",
                }}
              >
                NOTE
              </span>
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--body-text)",
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                PatentPilot searches SureChEMBL, enriches results via Google
                Patents, and runs AI analysis. Providing a Target and Disease
                improves report quality.
              </p>
            </div>

            {/* Submit */}
            <button
              type="submit"
              id="submit-analyze"
              className="btn-primary"
              style={{
                width: "100%",
                justifyContent: "center",
                padding: "14px",
                fontSize: "15px",
                opacity: isValid ? 1 : 0.5,
                cursor: isValid ? "pointer" : "not-allowed",
              }}
            >
              Run FTO Analysis →
            </button>
          </form>
        </div>

        {/* Pipeline overview */}
        <div style={{ marginTop: "28px" }}>
          <p
            className="section-label"
            style={{ marginBottom: "14px" }}
          >
            What happens next
          </p>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "0" }}
          >
            {[
              "Patent retrieval via molecular similarity (SureChEMBL)",
              "Abstract enrichment from Google Patents",
              "Similarity ranking & filtering (top-5)",
              "Per-patent AI analysis (risk, overlap, confidence)",
              "Structured FTO report generation",
            ].map((step, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: "12px",
                  alignItems: "flex-start",
                  padding: "10px 0",
                  borderBottom:
                    i < 4 ? "1px solid var(--border-light)" : "none",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    color: "var(--text-label)",
                    minWidth: "20px",
                    paddingTop: "1px",
                  }}
                >
                  0{i + 1}
                </span>
                <span
                  style={{
                    fontSize: "13px",
                    color: "var(--body-text)",
                    lineHeight: 1.5,
                  }}
                >
                  {step}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 600px) {
          .form-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}

/* ─── Loading State ───────────────────────────────────── */
function LoadingPanel({
  progress,
  smiles,
}: {
  progress: ProgressEvent | null;
  smiles: string;
}) {
  const steps = [
    "Searching molecular databases",
    "Retrieving relevant patents",
    "Enriching patent metadata",
    "Ranking patents by similarity",
    "Running AI analysis per patent",
    "Generating patentability report",
  ];

  const currentIndex = progress?.index ?? 0;

  return (
    <section
      className="fade-in visible"
      style={{
        flex: 1,
        padding: "80px 0",
        display: "flex",
        alignItems: "center",
      }}
    >
      <div className="container" style={{ maxWidth: "540px", width: "100%" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              margin: "0 auto 20px",
              borderRadius: "50%",
              border: "2px solid var(--border)",
              borderTopColor: "var(--primary)",
              animation: "spin 1s linear infinite",
            }}
          />
          <h2
            className="font-heading"
            style={{
              fontSize: "28px",
              color: "var(--heading)",
              marginBottom: "8px",
            }}
          >
            AI Analysis in Progress
          </h2>
          <p
            style={{
              fontSize: "13px",
              color: "var(--text-label)",
              fontFamily: "var(--font-mono)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: "400px",
              margin: "0 auto",
            }}
          >
            {smiles.length > 50 ? smiles.slice(0, 50) + "…" : smiles}
          </p>
        </div>

        <div className="card" style={{ padding: "24px" }}>
          {/* Progress bar */}
          <div
            style={{
              height: "3px",
              background: "var(--border)",
              marginBottom: "24px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                background: "var(--primary)",
                width: `${((currentIndex + 1) / steps.length) * 100}%`,
                transition: "width 0.5s ease",
              }}
            />
          </div>

          {steps.map((label, idx) => {
            const isDone = idx < currentIndex;
            const isActive = idx === currentIndex;
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "14px",
                  padding: "10px 0",
                  borderBottom:
                    idx < steps.length - 1
                      ? "1px solid var(--border-light)"
                      : "none",
                  opacity: isDone ? 0.6 : isActive ? 1 : 0.3,
                  transition: "opacity 0.3s ease",
                }}
              >
                {/* Icon */}
                <div
                  style={{
                    width: "26px",
                    height: "26px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    fontSize: "11px",
                    fontWeight: 600,
                    background: isDone
                      ? "var(--risk-low)"
                      : isActive
                      ? "var(--primary)"
                      : "var(--border-light)",
                    color: isDone || isActive ? "white" : "var(--text-label)",
                    border: `1px solid ${
                      isDone
                        ? "#bbf7d0"
                        : isActive
                        ? "var(--primary)"
                        : "var(--border)"
                    }`,
                    transition: "all 0.3s ease",
                  }}
                >
                  {isDone ? (
                    "✓"
                  ) : isActive ? (
                    <div
                      style={{
                        width: "12px",
                        height: "12px",
                        border: "2px solid rgba(255,255,255,0.3)",
                        borderTopColor: "white",
                        borderRadius: "50%",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                  ) : (
                    idx + 1
                  )}
                </div>

                {/* Label */}
                <span
                  style={{
                    fontSize: "13px",
                    fontWeight: isActive ? 500 : 400,
                    color: isActive ? "var(--heading)" : "var(--body-text)",
                  }}
                >
                  {label}
                </span>

                {/* Active pulse */}
                {isActive && (
                  <span
                    style={{
                      marginLeft: "auto",
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      color: "var(--primary)",
                      letterSpacing: "0.06em",
                    }}
                  >
                    RUNNING
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <p
          style={{
            textAlign: "center",
            marginTop: "20px",
            fontSize: "12px",
            color: "var(--text-label)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Typical runtime: 60–120 seconds. Please do not close this tab.
        </p>
      </div>
    </section>
  );
}

/* ─── Risk Summary Bar ────────────────────────────────── */
function RiskBar({ patents }: { patents: Patent[] }) {
  const counts = patents.reduce(
    (acc, p) => {
      acc[p.risk_level] = (acc[p.risk_level] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const items: { label: string; count: number; cls: string }[] = [
    { label: "Low", count: counts.low || 0, cls: "badge-low" },
    { label: "Review", count: counts.medium || 0, cls: "badge-review" },
    { label: "High", count: counts.high || 0, cls: "badge-high" },
    { label: "Critical", count: counts.critical || 0, cls: "badge-high" },
  ].filter((x) => x.count > 0);

  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
      {items.map((item) => (
        <span
          key={item.label}
          className={item.cls}
          style={{ fontSize: "11px" }}
        >
          {item.count} {item.label}
        </span>
      ))}
    </div>
  );
}

/* ─── Confidence Bar ──────────────────────────────────── */
function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const filled = Math.round(pct / 10);
  const label = pct >= 80 ? "High Confidence" : pct >= 60 ? "Moderate Confidence" : "Low Confidence";
  const barColor = pct >= 80 ? "var(--risk-low)" : pct >= 60 ? "var(--risk-review)" : "var(--risk-high)";

  return (
    <div>
      <div style={{ display: "flex", gap: "2px", marginBottom: "4px", alignItems: "center" }}>
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            style={{
              width: "14px",
              height: "8px",
              borderRadius: "2px",
              background: i < filled ? barColor : "var(--border)",
              transition: "background 0.3s ease",
            }}
          />
        ))}
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            fontWeight: 700,
            color: "var(--heading)",
            marginLeft: "6px",
          }}
        >
          {pct}%
        </span>
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "10px",
          color: barColor,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
    </div>
  );
}

/* ─── Patent Carousel ─────────────────────────────────── */
function PatentCarousel({
  patents,
  onSelect,
  selectedIndex,
}: {
  patents: Patent[];
  onSelect: (i: number) => void;
  selectedIndex: number;
}) {
  const [page, setPage] = useState(0);
  const cardsPerPage = 3;
  const totalPages = Math.ceil(patents.length / cardsPerPage);

  const prev = () => setPage((p) => Math.max(0, p - 1));
  const next = () => setPage((p) => Math.min(totalPages - 1, p + 1));

  const visible = patents.slice(page * cardsPerPage, (page + 1) * cardsPerPage);

  return (
    <div className="carousel-wrapper">
      <div className="carousel-header">
        <p className="section-label">Analysed Patents</p>
        <div className="carousel-nav">
          <button
            className="carousel-arrow"
            onClick={prev}
            disabled={page === 0}
            aria-label="Previous patents"
          >
            ←
          </button>
          <button
            className="carousel-arrow"
            onClick={next}
            disabled={page >= totalPages - 1}
            aria-label="Next patents"
          >
            →
          </button>
        </div>
      </div>

      <div className="carousel-track">
        {visible.map((patent, idx) => {
          const absoluteIdx = page * cardsPerPage + idx;
          const risk = RISK_CONFIG[patent.risk_level];
          const isSelected = selectedIndex === absoluteIdx;
          const year = patent.publication_date
            ? patent.publication_date.slice(0, 4)
            : "N/A";

          return (
            <div
              key={absoluteIdx}
              className={`carousel-card ${isSelected ? "carousel-card--active" : ""}`}
              onClick={() => onSelect(absoluteIdx)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onSelect(absoluteIdx)}
            >
              <div
                style={{ height: "3px", background: risk.color, opacity: 0.8, marginBottom: "14px", borderRadius: "1px" }}
              />
              <p className="carousel-title">{patent.title}</p>
              <div className="carousel-meta-row">
                {patent.similarity_score !== null && (
                  <span className="carousel-match">
                    {(patent.similarity_score * 100).toFixed(0)}% match
                  </span>
                )}
                <span className={risk.cls} style={{ fontSize: "10px" }}>
                  {risk.label}
                </span>
              </div>
              <div className="carousel-details">
                <div className="carousel-detail-item">
                  <span className="carousel-detail-label">Confidence</span>
                  <span className="carousel-detail-val">
                    {(patent.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="carousel-detail-item">
                  <span className="carousel-detail-label">Year</span>
                  <span className="carousel-detail-val">{year}</span>
                </div>
                <div className="carousel-detail-item" style={{ gridColumn: "1/-1" }}>
                  <span className="carousel-detail-label">Assignee</span>
                  <span
                    className="carousel-detail-val"
                    style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  >
                    {patent.assignee ?? "N/A"}
                  </span>
                </div>
              </div>
              <button
                className="carousel-view-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(absoluteIdx);
                }}
              >
                {isSelected ? "Viewing ↓" : "View Analysis →"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Pagination dots */}
      {totalPages > 1 && (
        <div className="carousel-dots">
          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i}
              className={`carousel-dot ${i === page ? "carousel-dot--active" : ""}`}
              onClick={() => setPage(i)}
              aria-label={`Page ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Patent Card ─────────────────────────────────────── */
function PatentCard({
  patent,
  highlighted,
  onRef,
}: {
  patent: Patent;
  highlighted: boolean;
  onRef?: (el: HTMLDivElement | null) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const risk = RISK_CONFIG[patent.risk_level];

  return (
    <div
      ref={onRef}
      className={`card patent-card ${highlighted ? "patent-card--highlighted" : ""}`}
      style={{ padding: 0, overflow: "hidden" }}
    >
      {/* Risk accent line */}
      <div
        style={{
          height: "3px",
          background: risk.color,
          opacity: 0.7,
        }}
      />

      {/* Header */}
      <div
        style={{
          padding: "24px 28px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "16px",
            marginBottom: "14px",
          }}
        >
          <h3
            style={{
              fontSize: "16px",
              fontWeight: 500,
              color: "var(--heading)",
              lineHeight: 1.45,
              margin: 0,
            }}
          >
            {patent.title}
          </h3>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              flexShrink: 0,
            }}
          >
            {patent.similarity_score !== null && (
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "14px",
                  color: "var(--primary)",
                  fontWeight: 700,
                }}
              >
                {(patent.similarity_score * 100).toFixed(0)}% match
              </span>
            )}
            <span
              className={risk.cls}
              style={{ fontSize: "10px", whiteSpace: "nowrap" }}
            >
              {risk.label}
            </span>
          </div>
        </div>

        {/* Metadata row */}
        <div
          style={{ display: "flex", gap: "20px", flexWrap: "wrap" }}
        >
          {[
            {
              k: "Number",
              v: patent.publication_number ?? "N/A",
            },
            { k: "Date", v: patent.publication_date ?? "N/A" },
            { k: "Assignee", v: patent.assignee ?? "N/A" },
            { k: "Source", v: patent.source ?? "N/A" },
          ].map(({ k, v }) => (
            <span
              key={k}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--text-muted)",
              }}
            >
              <span style={{ color: "var(--text-label)" }}>{k}: </span>
              {v}
            </span>
          ))}
        </div>
      </div>

      {/* AI Analysis Grid */}
      <div
        style={{ padding: "24px 28px", background: "var(--bg)" }}
      >
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}
          className="analysis-grid"
        >
          {/* Why Retrieved */}
          <div className="analysis-section">
            <p className="analysis-section-label">Why Retrieved</p>
            <p className="analysis-section-text">
              {patent.why_retrieved}
            </p>
          </div>

          {/* Similar Features */}
          <div className="analysis-section">
            <p className="analysis-section-label">Similar Features</p>
            {patent.similarities.length > 0 ? (
              <ul className="analysis-list">
                {patent.similarities.slice(0, 3).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            ) : (
              <p
                style={{
                  fontSize: "14px",
                  color: "var(--text-muted)",
                  lineHeight: 1.6,
                }}
              >
                No specific similarities noted.
              </p>
            )}
          </div>

          {/* Potential Overlap + Confidence */}
          <div
            style={{
              gridColumn: "1 / -1",
              borderTop: "1px solid var(--border-light)",
              paddingTop: "20px",
              display: "grid",
              gridTemplateColumns: "1fr auto",
              gap: "24px",
              alignItems: "start",
            }}
            className="overlap-grid"
          >
            <div className="analysis-section">
              <p className="analysis-section-label">Potential Overlap</p>
              <p className="analysis-section-text">
                {patent.potential_overlap}
              </p>
            </div>
            <div style={{ minWidth: "140px" }}>
              <p className="analysis-section-label" style={{ marginBottom: "10px" }}>
                AI Confidence
              </p>
              <ConfidenceBar value={patent.confidence} />
            </div>
          </div>
        </div>

        {/* Abstract toggle */}
        {patent.abstract && (
          <div style={{ marginTop: "20px", borderTop: "1px solid var(--border-light)", paddingTop: "16px" }}>
            <button
              onClick={() => setExpanded(!expanded)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--text-label)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                padding: 0,
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "color 0.2s ease",
              }}
            >
              {expanded ? "▲" : "▼"} {expanded ? "Hide" : "Show"} Abstract
            </button>
            {expanded && (
              <p
                className="fade-in visible"
                style={{
                  marginTop: "12px",
                  fontSize: "13px",
                  color: "var(--body-text)",
                  lineHeight: 1.7,
                  fontStyle: "italic",
                  borderLeft: "2px solid var(--border)",
                  paddingLeft: "14px",
                }}
              >
                {patent.abstract}
              </p>
            )}
          </div>
        )}
      </div>

      <style>{`
        @media (max-width: 600px) {
          .analysis-grid { grid-template-columns: 1fr !important; }
          .overlap-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}

/* ─── Retrieval Summary Card ──────────────────────────── */
function RetrievalSummaryCard() {
  return (
    <div className="card retrieval-summary-card" style={{ padding: "20px" }}>
      <p className="section-label" style={{ marginBottom: "12px" }}>
        Retrieval Summary
      </p>
      <p style={{ fontSize: "13px", color: "var(--body-text)", lineHeight: 1.65, marginBottom: "12px" }}>
        <strong style={{ color: "var(--heading)", fontWeight: 600 }}>10 patents</strong> were initially
        retrieved from public patent databases.
      </p>
      <p style={{ fontSize: "12px", color: "var(--text-label)", lineHeight: 1.6, marginBottom: "10px", fontFamily: "var(--font-mono)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        Ranking criteria
      </p>
      <ul className="retrieval-list">
        <li>Molecular similarity</li>
        <li>Semantic relevance</li>
        <li>Keyword overlap</li>
        <li>AI confidence</li>
      </ul>
      <p style={{ fontSize: "12px", color: "var(--body-text)", lineHeight: 1.6, marginTop: "12px", padding: "10px 12px", background: "rgba(28,52,97,0.04)", borderRadius: "6px", border: "1px solid var(--border-light)" }}>
        Only the <strong style={{ color: "var(--primary)" }}>Top 5</strong> highest-scoring patents
        are selected for detailed AI analysis to reduce inference cost and latency.
      </p>
    </div>
  );
}

/* ─── Results ─────────────────────────────────────────── */
export function ResultsPanel({
  result,
  onReset,
}: {
  result: AnalysisResult;
  onReset: () => void;
}) {
  const rec = REC_CONFIG[result.overall_recommendation];
  const avgSimilarity =
    result.patents.length > 0
      ? result.patents.reduce((s, p) => s + (p.similarity_score ?? 0), 0) /
        result.patents.length
      : 0;
  const avgConfidence =
    result.patents.length > 0
      ? result.patents.reduce((s, p) => s + p.confidence, 0) /
        result.patents.length
      : 0;

  const [selectedPatent, setSelectedPatent] = useState<number | null>(null);
  const patentRefs = useRef<(HTMLDivElement | null)[]>([]);

  const handleCarouselSelect = (index: number) => {
    setSelectedPatent(index);
    setTimeout(() => {
      patentRefs.current[index]?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 50);
  };

  return (
    <section
      className="slide-up"
      style={{ padding: "0 0 80px", background: "var(--bg)" }}
    >
      <div className="container">
        {/* Workflow Progress Indicator */}
        <WorkflowProgress currentState="results" />

        {/* Header Row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            marginBottom: "40px",
            flexWrap: "wrap",
            gap: "16px",
          }}
        >
          <div>
            <p className="section-label" style={{ marginBottom: "8px" }}>
              Analysis Complete
            </p>
            <h1
              className="font-heading"
              style={{
                fontSize: "clamp(24px, 3vw, 36px)",
                color: "var(--heading)",
                marginBottom: "8px",
                letterSpacing: "-0.02em",
              }}
            >
              Freedom-to-Operate Report
            </h1>
            {result.smiles && (
              <p
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                  color: "var(--text-label)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  maxWidth: "420px",
                }}
              >
                {result.smiles.length > 60
                  ? result.smiles.slice(0, 60) + "…"
                  : result.smiles}
              </p>
            )}
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              id="new-analysis-btn"
              className="btn-secondary"
              onClick={onReset}
            >
              New Analysis
            </button>
          </div>
        </div>

        {/* Errors banner */}
        {result.errors && result.errors.length > 0 && (
          <div
            style={{
              padding: "12px 16px",
              background: "var(--risk-high-bg)",
              border: "1px solid #fecaca",
              marginBottom: "32px",
              borderLeft: "3px solid var(--risk-high)",
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--risk-high)",
                fontWeight: 600,
                marginBottom: "4px",
              }}
            >
              WARNINGS
            </p>
            {result.errors.map((e, i) => (
              <p key={i} style={{ fontSize: "13px", color: "var(--risk-high)", lineHeight: 1.6 }}>
                {e}
              </p>
            ))}
          </div>
        )}

        {/* Main 2-column grid */}
        <div
          style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "36px", alignItems: "start" }}
          className="results-grid"
        >
          {/* ── Left Sidebar ── */}
          <div className="sidebar-sticky">
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

              {/* Recommendation card */}
              <div
                className="card"
                style={{
                  padding: "22px",
                  borderTop: `3px solid ${rec.color}`,
                  boxShadow: "0 2px 12px rgba(0,0,0,0.05)",
                }}
              >
                <p className="section-label" style={{ marginBottom: "12px" }}>
                  Overall Recommendation
                </p>
                <span
                  className={rec.cls}
                  style={{ fontSize: "12px", display: "inline-block", marginBottom: "14px" }}
                >
                  {rec.label}
                </span>
                <p
                  style={{
                    fontSize: "14px",
                    color: "var(--body-text)",
                    lineHeight: 1.65,
                  }}
                >
                  {result.recommendation_explanation}
                </p>
              </div>

              {/* Metrics card */}
              <div
                className="card"
                style={{ padding: "22px", boxShadow: "0 2px 12px rgba(0,0,0,0.05)" }}
              >
                <p className="section-label" style={{ marginBottom: "16px" }}>
                  Analysis Metrics
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  {[
                    {
                      label: "Patents Analyzed",
                      val: String(result.patents.length),
                    },
                    {
                      label: "Avg Similarity",
                      val: `${(avgSimilarity * 100).toFixed(1)}%`,
                    },
                    {
                      label: "Avg AI Confidence",
                      val: `${(avgConfidence * 100).toFixed(1)}%`,
                    },
                  ].map(({ label, val }) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        paddingBottom: "12px",
                        borderBottom: "1px solid var(--border-light)",
                      }}
                    >
                      <span
                        style={{ fontSize: "13px", color: "var(--body-text)" }}
                      >
                        {label}
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "14px",
                          fontWeight: 700,
                          color: "var(--heading)",
                        }}
                      >
                        {val}
                      </span>
                    </div>
                  ))}

                  {/* Risk distribution */}
                  <div>
                    <span
                      style={{
                        fontSize: "13px",
                        color: "var(--body-text)",
                        display: "block",
                        marginBottom: "10px",
                      }}
                    >
                      Risk Distribution
                    </span>
                    <RiskBar patents={result.patents} />
                  </div>
                </div>
              </div>

              {/* Retrieval Summary */}
              <RetrievalSummaryCard />

              {/* Molecule Context */}
              {(result.target || result.disease) && (
                <div
                  className="card"
                  style={{ padding: "22px", boxShadow: "0 2px 12px rgba(0,0,0,0.05)" }}
                >
                  <p className="section-label" style={{ marginBottom: "12px" }}>
                    Molecule Context
                  </p>
                  {result.target && (
                    <div style={{ marginBottom: "10px" }}>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          color: "var(--text-label)",
                          display: "block",
                          marginBottom: "2px",
                          textTransform: "uppercase",
                        }}
                      >
                        Target
                      </span>
                      <span
                        style={{ fontSize: "14px", color: "var(--heading)", fontWeight: 500 }}
                      >
                        {result.target}
                      </span>
                    </div>
                  )}
                  {result.disease && (
                    <div>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          color: "var(--text-label)",
                          display: "block",
                          marginBottom: "2px",
                          textTransform: "uppercase",
                        }}
                      >
                        Disease
                      </span>
                      <span
                        style={{ fontSize: "14px", color: "var(--heading)", fontWeight: 500 }}
                      >
                        {result.disease}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Right Main Content ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: "40px" }}>

            {/* Executive Summary + Report */}
            <div className="card" style={{ padding: "32px", boxShadow: "0 2px 12px rgba(0,0,0,0.05)" }}>
              <h2
                className="font-heading"
                style={{
                  fontSize: "24px",
                  marginBottom: "28px",
                  color: "var(--heading)",
                  letterSpacing: "-0.015em",
                }}
              >
                AI Patentability Report
              </h2>

              <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
                {/* Executive Summary */}
                <div>
                  <h3 className="report-section-heading">
                    Executive Summary
                  </h3>
                  <p
                    style={{
                      fontSize: "15px",
                      color: "var(--body-text)",
                      lineHeight: 1.75,
                    }}
                  >
                    {result.executive_summary}
                  </p>
                </div>

                {/* Key Similar Patents */}
                {result.key_similar_patents.length > 0 && (
                  <div
                    style={{
                      borderTop: "1px solid var(--border)",
                      paddingTop: "24px",
                    }}
                  >
                    <h3 className="report-section-heading">
                      Key Similar Patents
                    </h3>
                    <ul className="report-list">
                      {result.key_similar_patents.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Novelty Concerns */}
                {result.novelty_concerns.length > 0 && (
                  <div
                    style={{
                      borderTop: "1px solid var(--border)",
                      paddingTop: "24px",
                    }}
                  >
                    <h3
                      className="report-section-heading"
                      style={{ color: "var(--risk-high)" }}
                    >
                      Potential Novelty Concerns
                    </h3>
                    <ul className="report-list" style={{ color: "var(--body-text)" }}>
                      {result.novelty_concerns.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Patents requiring review */}
                {result.patents_requiring_review.length > 0 && (
                  <div
                    style={{
                      borderTop: "1px solid var(--border)",
                      paddingTop: "24px",
                    }}
                  >
                    <div
                      style={{
                        background: "var(--risk-review-bg)",
                        border: "1px solid #fde68a",
                        borderRadius: "8px",
                        padding: "20px",
                      }}
                    >
                      <h3
                        className="report-section-heading"
                        style={{ color: "var(--risk-review)", marginBottom: "12px" }}
                      >
                        Patents Requiring Manual Review
                      </h3>
                      <ul className="report-list" style={{ color: "var(--risk-review)" }}>
                        {result.patents_requiring_review.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Patent Carousel */}
            {result.patents.length > 0 && (
              <PatentCarousel
                patents={result.patents}
                onSelect={handleCarouselSelect}
                selectedIndex={selectedPatent ?? -1}
              />
            )}

            {/* Patent Cards */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "20px",
                }}
              >
                <p className="section-label">
                  Detailed Patent Analysis ({result.patents.length})
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "32px",
                }}
              >
                {result.patents.length > 0 ? (
                  result.patents.map((patent, i) => (
                    <PatentCard
                      key={i}
                      patent={patent}
                      highlighted={selectedPatent === i}
                      onRef={(el) => { patentRefs.current[i] = el; }}
                    />
                  ))
                ) : (
                  <div
                    className="card"
                    style={{
                      padding: "40px",
                      textAlign: "center",
                      color: "var(--text-muted)",
                    }}
                  >
                    <p style={{ fontSize: "15px" }}>
                      No patents were successfully analyzed.
                    </p>
                    {result.errors.length > 0 && (
                      <p
                        style={{
                          fontSize: "13px",
                          color: "var(--risk-high)",
                          marginTop: "8px",
                        }}
                      >
                        See warnings above.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Disclaimer */}
            <div className="disclaimer-panel">
              <span className="disclaimer-icon">ℹ</span>
              <p className="disclaimer-text">
                This AI-assisted assessment is based on publicly available patent metadata and abstracts.
                Final Freedom-to-Operate decisions should always involve expert review of complete patent claims.
              </p>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .results-grid { grid-template-columns: 1fr !important; }
          .sidebar-sticky { position: static !important; top: auto !important; }
        }
        @media (max-width: 600px) {
          .analysis-grid { grid-template-columns: 1fr !important; }
          .overlap-grid { grid-template-columns: 1fr !important; }
          .carousel-track { grid-template-columns: 1fr !important; overflow-x: auto; }
        }
        @media (min-width: 601px) and (max-width: 900px) {
          .carousel-track { grid-template-columns: repeat(2, 1fr) !important; }
        }
      `}</style>
    </section>
  );
}

/* ─── Error Panel ─────────────────────────────────────── */
function ErrorPanel({
  message,
  onReset,
}: {
  message: string;
  onReset: () => void;
}) {
  return (
    <section
      className="fade-in visible"
      style={{
        flex: 1,
        padding: "80px 0",
        display: "flex",
        alignItems: "center",
      }}
    >
      <div className="container" style={{ maxWidth: "520px", width: "100%" }}>
        <div className="card" style={{ padding: "32px", textAlign: "center" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "var(--risk-high-bg)",
              border: "1px solid #fecaca",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
              fontSize: "20px",
            }}
          >
            ✕
          </div>
          <h2
            className="font-heading"
            style={{
              fontSize: "24px",
              color: "var(--heading)",
              marginBottom: "12px",
            }}
          >
            Analysis Failed
          </h2>
          <p
            style={{
              fontSize: "14px",
              color: "var(--body-text)",
              lineHeight: 1.65,
              marginBottom: "8px",
            }}
          >
            {message}
          </p>
          <p
            style={{
              fontSize: "12px",
              color: "var(--text-label)",
              marginBottom: "24px",
              fontFamily: "var(--font-mono)",
            }}
          >
            Ensure the PatentPilot API server is running on port 8000.
          </p>
          <button
            id="retry-btn"
            className="btn-primary"
            onClick={onReset}
            style={{ width: "100%", justifyContent: "center", padding: "12px" }}
          >
            Try Again
          </button>
        </div>
      </div>
    </section>
  );
}

/* ─── Main Page ───────────────────────────────────────── */
export default function AnalyzePage() {
  const [state, setState] = useState<AnalysisState>("input");
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [currentSmiles, setCurrentSmiles] = useState("");

  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (smiles: string, target: string, disease: string) => {
      setCurrentSmiles(smiles);
      setState("loading");
      setProgress(null);
      setResult(null);
      setErrorMsg("");

      abortRef.current = new AbortController();

      try {
        const response = await fetch(`${API_URL}/analyze/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ smiles, target: target || null, disease: disease || null, top_n: 5 }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: "Server error" }));
          throw new Error(err.detail || `Server error: ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            if (!part.trim()) continue;
            const lines = part.split("\n");
            let eventType = "";
            let dataLine = "";

            for (const line of lines) {
              if (line.startsWith("event: ")) eventType = line.slice(7).trim();
              if (line.startsWith("data: ")) dataLine = line.slice(6).trim();
            }

            if (!dataLine) continue;

            const payload = JSON.parse(dataLine);

            if (eventType === "progress") {
              setProgress(payload as ProgressEvent);
            } else if (eventType === "result") {
              setResult(payload as AnalysisResult);
              setState("results");
            } else if (eventType === "error") {
              throw new Error(payload.message || "Unknown error from server");
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        const msg =
          err instanceof Error ? err.message : "An unknown error occurred.";
        setErrorMsg(msg);
        setState("error");
      }
    },
    []
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState("input");
    setProgress(null);
    setResult(null);
    setErrorMsg("");
    setCurrentSmiles("");
  }, []);

  return (
    <>
      <Nav />
      <main
        style={{
          minHeight: "calc(100vh - 56px)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {state === "input" && <InputForm onSubmit={handleSubmit} />}
        {state === "loading" && (
          <LoadingPanel progress={progress} smiles={currentSmiles} />
        )}
        {state === "results" && result && (
          <ResultsPanel result={result} onReset={reset} />
        )}
        {state === "error" && (
          <ErrorPanel message={errorMsg} onReset={reset} />
        )}
      </main>
    </>
  );
}
