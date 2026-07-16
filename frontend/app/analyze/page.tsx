"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

/* ─── Types ───────────────────────────────────────────── */
type AnalysisState = "input" | "loading" | "results";
type RiskLevel = "low" | "review" | "high";

interface MoleculeData {
  smiles: string;
  target: string;
  disease: string;
}

/* ─── Mock Data for Demo ──────────────────────────────── */
const MOCK_PATENTS = [
  {
    number: "US10,472,361",
    title: "EGFR inhibitor compounds for cancer therapy",
    date: "2019-11-12",
    assignee: "AstraZeneca AB",
    source: "SureChEMBL",
    score: 0.91,
    risk: "review" as RiskLevel,
    abstract: "The present invention relates to novel 4-anilinoquinazoline derivatives, pharmaceutical compositions containing them, and their use in the treatment of proliferative disorders such as cancer, particularly non-small cell lung cancer characterized by EGFR mutations.",
    analysis: {
      why: "High structural similarity in the quinazoline core scaffold shared with the submitted molecule.",
      features: "4-anilinoquinazoline core, halogen substitution at C6/C7, and the acrylamide warhead at C4.",
      overlap: "Claims 1–4 and 12 appear to cover analogous compounds with EGFR inhibitory activity.",
      confidence: 0.91
    }
  },
  {
    number: "EP2,345,650",
    title: "Quinazoline derivatives as protein kinase inhibitors",
    date: "2011-07-20",
    assignee: "OSI Pharmaceuticals",
    source: "Google Patents",
    score: 0.84,
    risk: "low" as RiskLevel,
    abstract: "Compounds represented by Formula I, and pharmaceutically acceptable salts thereof, are useful in the treatment of hyperproliferative diseases and angiogenesis mediated diseases. The compounds are inhibitors of protein kinases, particularly the epidermal growth factor receptor (EGFR).",
    analysis: {
      why: "Shares the general quinazoline skeleton but lacks the specific substituted acrylamide group.",
      features: "Basic quinazoline ring system; different substituent pattern at the aniline ring.",
      overlap: "Minimal overlap expected as the claims focus on a different substitution profile for reversable binding.",
      confidence: 0.88
    }
  },
  {
    number: "WO2018/091925",
    title: "Methods for treating NSCLC with EGFR mutations",
    date: "2018-05-24",
    assignee: "Roche AG",
    source: "PubChem",
    score: 0.79,
    risk: "low" as RiskLevel,
    abstract: "The disclosure provides methods of treating non-small cell lung cancer (NSCLC) harboring specific EGFR mutations by administering a combination of a third-generation EGFR inhibitor and a MEK inhibitor.",
    analysis: {
      why: "Method of treatment patent targeting the same disease indication and biological mechanism.",
      features: "Pharmacological overlap in therapeutic application, though structural compounds claimed are distinct.",
      overlap: "No composition of matter overlap. Method claims could be relevant if combination therapy is pursued.",
      confidence: 0.95
    }
  }
];

/* ─── Nav ─────────────────────────────────────────────── */
function Nav() {
  return (
    <nav>
      <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: "56px" }}>
        <Link href="/" style={{ textDecoration: "none" }}>
          <span style={{ fontFamily: "var(--font-heading)", fontWeight: 300, fontSize: "18px", color: "var(--primary)", letterSpacing: "-0.02em" }}>
            PatentPilot
          </span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "32px" }}>
          <Link href="/" style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-secondary)", textDecoration: "none" }}>
            Exit Workspace
          </Link>
        </div>
      </div>
    </nav>
  );
}

/* ─── Main Component ──────────────────────────────────── */
export default function AnalyzePage() {
  const [state, setState] = useState<AnalysisState>("input");
  const [formData, setFormData] = useState<MoleculeData>({ smiles: "", target: "", disease: "" });
  const [activeStep, setActiveStep] = useState(0);

  // Loading simulation
  useEffect(() => {
    if (state === "loading") {
      let currentStep = 0;
      const interval = setInterval(() => {
        currentStep++;
        if (currentStep > 4) {
          clearInterval(interval);
          setTimeout(() => setState("results"), 500); // Transition to results
        } else {
          setActiveStep(currentStep);
        }
      }, 1200); // 1.2s per step for effect
      return () => clearInterval(interval);
    }
  }, [state]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.smiles.trim()) return;
    setState("loading");
    setActiveStep(0);
  };

  const reset = () => {
    setState("input");
    setFormData({ smiles: "", target: "", disease: "" });
    setActiveStep(0);
  };

  return (
    <>
      <Nav />
      <main style={{ minHeight: "calc(100vh - 56px)", display: "flex", flexDirection: "column" }}>
        {state === "input" && (
          <section className="fade-in visible" style={{ flex: 1, padding: "64px 0", display: "flex", alignItems: "center" }}>
            <div className="container" style={{ maxWidth: "600px", width: "100%" }}>
              <div style={{ textAlign: "center", marginBottom: "40px" }}>
                <p className="section-label" style={{ marginBottom: "16px" }}>New Analysis</p>
                <h1 className="font-heading" style={{ fontSize: "36px", color: "var(--text)", marginBottom: "16px" }}>
                  Molecule Input
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
                  Enter a SMILES string to begin an AI-assisted Freedom-to-Operate analysis.
                </p>
              </div>

              <div className="card">
                <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div>
                    <label className="input-label">
                      SMILES <span className="required">*</span>
                    </label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="e.g. CC1=CC2=C(C=C1)N(C(=O)N2)CC..."
                      value={formData.smiles}
                      onChange={e => setFormData({ ...formData, smiles: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="input-label">Target (Optional)</label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="e.g. EGFR Tyrosine Kinase"
                      value={formData.target}
                      onChange={e => setFormData({ ...formData, target: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="input-label">Disease / Indication (Optional)</label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="e.g. Non-small cell lung cancer"
                      value={formData.disease}
                      onChange={e => setFormData({ ...formData, disease: e.target.value })}
                    />
                  </div>
                  <div style={{ marginTop: "12px" }}>
                    <button type="submit" className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px" }} disabled={!formData.smiles.trim()}>
                      Analyze Molecule
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </section>
        )}

        {state === "loading" && (
          <section className="fade-in visible" style={{ flex: 1, padding: "80px 0", display: "flex", alignItems: "center" }}>
            <div className="container" style={{ maxWidth: "480px", width: "100%" }}>
              <h2 className="font-heading" style={{ fontSize: "28px", textAlign: "center", marginBottom: "40px" }}>
                AI Analysis in Progress
              </h2>
              <div className="card">
                {[
                  "Searching molecular databases",
                  "Retrieving relevant patents",
                  "Ranking patent similarity",
                  "Running AI reasoning",
                  "Generating patentability report"
                ].map((stepLabel, idx) => (
                  <div
                    key={idx}
                    className={\`progress-step \${idx < activeStep ? 'completed' : idx === activeStep ? 'active' : ''}\`}
                  >
                    <div className="step-icon">
                      {idx < activeStep ? "✓" : idx === activeStep ? <div className="step-spinner" /> : idx + 1}
                    </div>
                    <span style={{ fontSize: "14px", fontWeight: idx === activeStep ? 500 : 400 }}>
                      {stepLabel}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {state === "results" && (
          <section className="slide-up" style={{ padding: "48px 0 80px", background: "var(--bg)" }}>
            <div className="container">
              
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "32px", flexWrap: "wrap", gap: "16px" }}>
                <div>
                  <p className="section-label" style={{ marginBottom: "8px" }}>Analysis Results</p>
                  <h1 className="font-heading" style={{ fontSize: "32px" }}>Freedom-to-Operate Report</h1>
                </div>
                <div style={{ display: "flex", gap: "12px" }}>
                  <button className="btn-secondary" onClick={reset}>New Analysis</button>
                  <button className="btn-primary">Export PDF</button>
                </div>
              </div>

              {/* Grid Layout */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "32px", '@media (min-width: 1024px)': { gridTemplateColumns: "300px 1fr" } } as any}>
                
                {/* Left Sidebar - Executive Summary & Metrics */}
                <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                  <div className="card" style={{ padding: "20px" }}>
                    <p className="section-label" style={{ marginBottom: "16px" }}>Executive Summary</p>
                    <div style={{ marginBottom: "20px" }}>
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>Overall Patent Risk</p>
                      <span className="badge-review" style={{ fontSize: "13px", padding: "6px 12px" }}>Requires Expert Review</span>
                    </div>
                    
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "20px", borderBottom: "1px solid var(--border)", paddingBottom: "20px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>AI Confidence</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 500 }}>88%</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Patents Analyzed</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 500 }}>{MOCK_PATENTS.length}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Avg Similarity</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 500 }}>84.6%</span>
                      </div>
                    </div>

                    <p style={{ fontSize: "13px", lineHeight: 1.6, color: "var(--text)" }}>
                      Analysis of {MOCK_PATENTS.length} relevant patents indicates a potential overlap with existing quinazoline-core claims. While novelty appears intact for the specific side-chain, the structural core overlaps significantly with US10,472,361. IP counsel consultation is recommended before proceeding.
                    </p>
                  </div>
                </div>

                {/* Main Content - Report & Patents */}
                <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
                  
                  {/* Patentability Report Card */}
                  <div className="card" style={{ padding: "32px" }}>
                    <h2 className="font-heading" style={{ fontSize: "24px", marginBottom: "24px" }}>AI Patentability Report</h2>
                    
                    <div style={{ display: "grid", gap: "24px" }}>
                      <div>
                        <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--primary)", marginBottom: "8px" }}>Key Similar Patents</h3>
                        <ul style={{ margin: 0, paddingLeft: "16px", color: "var(--text)", fontSize: "14px", lineHeight: 1.6 }}>
                          <li><span style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>US10,472,361</span> — High structural similarity in the quinazoline core scaffold.</li>
                          <li><span style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>EP2,345,650</span> — General quinazoline skeleton overlap.</li>
                        </ul>
                      </div>

                      <div>
                        <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--primary)", marginBottom: "8px" }}>Potential Novelty Concerns</h3>
                        <p style={{ fontSize: "14px", color: "var(--text)", lineHeight: 1.6 }}>
                          The primary concern lies in the 4-anilinoquinazoline core which is broadly claimed in several existing AstraZeneca and OSI patents. The specific acrylamide warhead at C4 may provide some differentiation, but falls within the Markush structures of US'361.
                        </p>
                      </div>

                      <div style={{ background: "var(--risk-review-bg)", padding: "16px", borderRadius: "6px", border: "1px solid #fde68a", marginTop: "8px" }}>
                        <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--risk-review)", marginBottom: "6px" }}>Overall Recommendation: Consult IP Counsel</h3>
                        <p style={{ fontSize: "13px", color: "var(--text)", lineHeight: 1.5, margin: 0 }}>
                          Material concerns exist regarding the core structure. Legal review of US10,472,361 claims is needed to determine if the proposed substituent modifications are sufficient for freedom-to-operate.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Filters */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
                    <p className="section-label">Analyzed Patents ({MOCK_PATENTS.length})</p>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <select className="input-field" style={{ padding: "6px 12px", width: "auto", fontSize: "13px" }}>
                        <option>Sort by: Similarity (High to Low)</option>
                        <option>Sort by: Confidence (High to Low)</option>
                        <option>Sort by: Date (Newest)</option>
                      </select>
                      <select className="input-field" style={{ padding: "6px 12px", width: "auto", fontSize: "13px" }}>
                        <option>Filter: All Risks</option>
                        <option>Filter: High & Review</option>
                      </select>
                    </div>
                  </div>

                  {/* Patent Cards */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {MOCK_PATENTS.map((patent, i) => (
                      <div key={patent.number} className="card card-hover" style={{ padding: 0, overflow: "hidden" }}>
                        {/* Header */}
                        <div style={{ padding: "20px", borderBottom: "1px solid var(--border)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", marginBottom: "12px" }}>
                            <h3 style={{ fontSize: "16px", fontWeight: 500, color: "var(--text)", lineHeight: 1.4, margin: 0 }}>
                              {patent.title}
                            </h3>
                            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                              <span style={{ fontFamily: "var(--font-mono)", fontSize: "14px", color: "var(--primary)", fontWeight: 500 }}>
                                {(patent.score * 100).toFixed(0)}% Match
                              </span>
                              <span className={\`badge-\${patent.risk}\`}>
                                {patent.risk === 'low' ? 'Low Risk' : patent.risk === 'review' ? 'Review Needed' : 'High Risk'}
                              </span>
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                            {[
                              { k: "Number", v: patent.number },
                              { k: "Date", v: patent.date },
                              { k: "Assignee", v: patent.assignee },
                              { k: "Source", v: patent.source }
                            ].map(({ k, v }) => (
                              <span key={k} style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                                <span style={{ color: "var(--text-label)" }}>{k}: </span>{v}
                              </span>
                            ))}
                          </div>
                        </div>
                        
                        {/* AI Analysis Grid */}
                        <div style={{ padding: "20px", background: "var(--bg)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                            <div>
                              <p style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-label)", marginBottom: "4px" }}>Why Retrieved</p>
                              <p style={{ fontSize: "13px", color: "var(--text)", lineHeight: 1.5 }}>{patent.analysis.why}</p>
                            </div>
                            <div>
                              <p style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-label)", marginBottom: "4px" }}>Similar Features</p>
                              <p style={{ fontSize: "13px", color: "var(--text)", lineHeight: 1.5 }}>{patent.analysis.features}</p>
                            </div>
                            <div style={{ gridColumn: "1 / -1", borderTop: "1px solid var(--border-light)", paddingTop: "16px", marginTop: "4px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                <div>
                                  <p style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-label)", marginBottom: "4px" }}>Potential Overlap</p>
                                  <p style={{ fontSize: "13px", color: "var(--text)", lineHeight: 1.5 }}>{patent.analysis.overlap}</p>
                                </div>
                                <div style={{ textAlign: "right", minWidth: "100px" }}>
                                  <p style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-label)", marginBottom: "4px" }}>AI Confidence</p>
                                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 500, color: "var(--text)" }}>
                                    {(patent.analysis.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", display: "flex", gap: "12px", background: "var(--surface)" }}>
                          <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }}>View Full Patent</button>
                          <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px", border: "none" }}>Copy Number</button>
                        </div>
                      </div>
                    ))}
                  </div>

                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </>
  );
}
