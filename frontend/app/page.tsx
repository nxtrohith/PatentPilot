"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";

/* ─── Scroll animation hook ──────────────────────────── */
function useFadeIn() {
  useEffect(() => {
    const els = document.querySelectorAll(".fade-in");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("visible");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.1 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

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
        {/* Wordmark */}
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

        {/* Nav links */}
        <div style={{ display: "flex", alignItems: "center", gap: "32px" }}>
          <a
            href="#features"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "14px",
              color: "var(--text-secondary)",
              textDecoration: "none",
            }}
          >
            Features
          </a>
          <a
            href="#workflow"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "14px",
              color: "var(--text-secondary)",
              textDecoration: "none",
            }}
          >
            Workflow
          </a>
          <Link href="/analyze" className="btn-primary" id="nav-cta">
            Analyze Molecule
          </Link>
        </div>
      </div>
    </nav>
  );
}

/* ─── Hero ────────────────────────────────────────────── */
function Hero() {
  return (
    <section
      style={{
        padding: "80px 0 64px",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div className="container">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "64px",
            alignItems: "start",
          }}
          className="hero-grid"
        >
          {/* Left column */}
          <div className="fade-in">
            <div className="section-label" style={{ marginBottom: "24px" }}>
              Freedom-to-Operate Analysis
            </div>

            <h1
              className="font-heading"
              style={{
                fontSize: "clamp(36px, 4.5vw, 56px)",
                lineHeight: 1.12,
                letterSpacing: "-0.03em",
                color: "var(--text)",
                marginBottom: "24px",
              }}
            >
              AI-assisted patent
              <br />
              analysis for drug
              <br />
              discovery
            </h1>

            <p
              style={{
                fontSize: "16px",
                lineHeight: 1.7,
                color: "var(--text-secondary)",
                marginBottom: "32px",
                maxWidth: "440px",
              }}
            >
              PatentPilot helps researchers search relevant patents, review
              patent information, and perform AI-assisted patentability analysis
              — generating structured Freedom-to-Operate reports before
              investing further in the drug discovery pipeline.
            </p>

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <Link href="/analyze" className="btn-primary" id="hero-cta-analyze">
                Analyze Molecule
              </Link>
              <a href="#workflow" className="btn-secondary" id="hero-cta-demo">
                View Demo
              </a>
            </div>

            {/* Data sources */}
            <div
              style={{
                marginTop: "48px",
                paddingTop: "32px",
                borderTop: "1px solid var(--border)",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--text-label)",
                  marginBottom: "14px",
                }}
              >
                Public Data Sources
              </p>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "14px" }}>
                {["SureChEMBL", "PubChem", "Google Patents", "Public Patent Databases"].map(
                  (src) => (
                    <span key={src} className="tag">
                      {src}
                    </span>
                  )
                )}
              </div>
              <p
                style={{
                  fontSize: "13px",
                  color: "var(--text-muted)",
                  lineHeight: 1.6,
                  maxWidth: "400px",
                }}
              >
                PatentPilot retrieves publicly available molecular and patent
                information before performing AI-assisted analysis — no
                proprietary databases required.
              </p>
            </div>
          </div>

          {/* Right column — product preview */}
          <div className="fade-in" style={{ animationDelay: "0.1s" }}>
            <ProductPreview />
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .hero-grid { grid-template-columns: 1fr !important; gap: 40px !important; }
        }
      `}</style>
    </section>
  );
}

/* ─── Product Preview ──────────────────────────────────── */
function ProductPreview() {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      {/* Window chrome */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "10px 14px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg)",
        }}
      >
        {["#ff5f57", "#febc2e", "#28c840"].map((c, i) => (
          <span
            key={i}
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: c,
              display: "block",
            }}
          />
        ))}
        <span
          style={{
            marginLeft: "8px",
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--text-label)",
          }}
        >
          patentpilot — fto-analysis
        </span>
      </div>

      {/* Molecule Submission */}
      <div
        style={{
          padding: "16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <p className="section-label" style={{ marginBottom: "10px" }}>
          Molecule Submission
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {[
            { label: "SMILES", val: "CC1=CC2=C(C=C1)N(C(=O)N2)CC..." },
            { label: "Target (Optional)", val: "EGFR Tyrosine Kinase" },
            { label: "Disease / Indication", val: "Non-small cell lung cancer" },
          ].map(({ label, val }) => (
            <div
              key={label}
              style={{
                display: "flex",
                gap: "8px",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  color: "var(--text-label)",
                  minWidth: "100px",
                }}
              >
                {label}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-secondary)",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  padding: "3px 8px",
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {val}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Arrow connector */}
      <div
        style={{
          padding: "8px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: "6px",
        }}
      >
        <div style={{ flex: 1, height: "1px", background: "var(--border)" }} />
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            color: "var(--text-label)",
          }}
        >
          Retrieved 12 patents
        </span>
        <div style={{ flex: 1, height: "1px", background: "var(--border)" }} />
      </div>

      {/* Patent List */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <p className="section-label" style={{ marginBottom: "10px" }}>
          Retrieved Patents
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {[
            {
              title: "EGFR inhibitor compounds for cancer therapy",
              number: "US10,472,361",
              date: "2019-11-12",
              assignee: "AstraZeneca AB",
              source: "SureChEMBL",
              score: 0.91,
            },
            {
              title: "Quinazoline derivatives as protein kinase inhibitors",
              number: "EP2,345,650",
              date: "2011-07-20",
              assignee: "OSI Pharmaceuticals",
              source: "Google Patents",
              score: 0.84,
            },
            {
              title: "Methods for treating NSCLC with EGFR mutations",
              number: "WO2018/091925",
              date: "2018-05-24",
              assignee: "Roche AG",
              source: "PubChem",
              score: 0.79,
            },
          ].map((p) => (
            <div
              key={p.number}
              style={{
                background: "var(--bg)",
                border: "1px solid var(--border)",
                padding: "10px 12px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "8px",
                  marginBottom: "6px",
                }}
              >
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 500,
                    color: "var(--text)",
                    lineHeight: 1.4,
                  }}
                >
                  {p.title}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--primary)",
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  {(p.score * 100).toFixed(0)}%
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                {[
                  { k: "Number", v: p.number },
                  { k: "Date", v: p.date },
                  { k: "Assignee", v: p.assignee },
                  { k: "Source", v: p.source },
                ].map(({ k, v }) => (
                  <span
                    key={k}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      color: "var(--text-muted)",
                    }}
                  >
                    <span style={{ color: "var(--text-label)" }}>{k}: </span>
                    {v}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Analysis */}
      <div style={{ padding: "12px 16px" }}>
        <p className="section-label" style={{ marginBottom: "10px" }}>
          AI Analysis — US10,472,361
        </p>
        <div
          style={{
            background: "var(--bg)",
            border: "1px solid var(--border)",
            padding: "12px",
            marginBottom: "10px",
          }}
        >
          {[
            {
              q: "Why was this patent retrieved?",
              a: "High structural similarity in the quinazoline core scaffold shared with the submitted molecule.",
            },
            {
              q: "Which molecular features are similar?",
              a: "4-anilinoquinazoline core, halogen substitution at C6/C7, and the acrylamide warhead at C4.",
            },
            {
              q: "What overlap exists?",
              a: "Claims 1–4 and 12 appear to cover analogous compounds with EGFR inhibitory activity.",
            },
            {
              q: "Confidence",
              a: "High (91%)",
            },
          ].map(({ q, a }) => (
            <div
              key={q}
              style={{
                marginBottom: "8px",
                paddingBottom: "8px",
                borderBottom: "1px solid var(--border-light)",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  color: "var(--text-label)",
                  marginBottom: "2px",
                }}
              >
                {q}
              </p>
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                {a}
              </p>
            </div>
          ))}
        </div>

        {/* Risk badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-muted)",
            }}
          >
            Overall Patent Risk
          </span>
          <span className="badge-review">Requires Expert Review</span>
        </div>
      </div>
    </div>
  );
}

/* ─── Features ────────────────────────────────────────── */
function Features() {
  const features = [
    {
      num: "01",
      title: "Patent Discovery",
      description:
        "Search patents using molecular similarity, semantic search, hybrid retrieval, and embedding-based retrieval techniques to surface the most relevant prior art.",
      tags: ["SMILES", "Similarity Search", "Embeddings"],
    },
    {
      num: "02",
      title: "Patent Review Workspace",
      description:
        "Review retrieved patents with full metadata — title, patent number, publication date, assignee, abstract, source, and relevance score — in a structured workspace.",
      tags: ["Metadata", "Ranking", "Workspace"],
    },
    {
      num: "03",
      title: "AI-assisted Patentability Analysis",
      description:
        "Generate structured reports with Executive Summary, Key Similar Patents, Potential Novelty Concerns, Patents Requiring Manual Review, and an Overall Recommendation classified as Low Patent Risk, Requires Expert Review, or High Patent Risk.",
      tags: ["LLM", "Report Generation", "Risk Assessment"],
    },
  ];

  return (
    <section
      id="features"
      style={{
        padding: "80px 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div className="container">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 2fr",
            gap: "64px",
            alignItems: "start",
          }}
          className="two-col-grid"
        >
          {/* Left */}
          <div className="fade-in" style={{ position: "sticky", top: "80px" }}>
            <p className="section-label" style={{ marginBottom: "16px" }}>
              Capabilities
            </p>
            <h2
              className="font-heading"
              style={{
                fontSize: "clamp(28px, 3vw, 38px)",
                lineHeight: 1.2,
                letterSpacing: "-0.025em",
                color: "var(--text)",
              }}
            >
              Everything you need for FTO analysis
            </h2>
          </div>

          {/* Right */}
          <div
            style={{ display: "flex", flexDirection: "column" }}
            className="fade-in"
          >
            {features.map((f, i) => (
              <div
                key={f.num}
                style={{
                  padding: "28px 0",
                  borderTop: "1px solid var(--border)",
                  ...(i === features.length - 1
                    ? { borderBottom: "1px solid var(--border)" }
                    : {}),
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: "16px",
                    marginBottom: "12px",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                      color: "var(--text-label)",
                      minWidth: "24px",
                    }}
                  >
                    {f.num}
                  </span>
                  <h3
                    className="font-heading"
                    style={{
                      fontSize: "22px",
                      fontWeight: 300,
                      letterSpacing: "-0.02em",
                      color: "var(--text)",
                    }}
                  >
                    {f.title}
                  </h3>
                </div>
                <p
                  style={{
                    fontSize: "14px",
                    lineHeight: 1.7,
                    color: "var(--text-secondary)",
                    marginBottom: "16px",
                    marginLeft: "40px",
                  }}
                >
                  {f.description}
                </p>
                <div
                  style={{
                    display: "flex",
                    gap: "6px",
                    flexWrap: "wrap",
                    marginLeft: "40px",
                  }}
                >
                  {f.tags.map((t) => (
                    <span key={t} className="tag">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .two-col-grid { grid-template-columns: 1fr !important; gap: 32px !important; }
        }
      `}</style>
    </section>
  );
}

/* ─── Workflow ────────────────────────────────────────── */
function Workflow() {
  const steps = [
    {
      id: "submit",
      label: "Submit Molecule",
      desc: "Input SMILES with optional Target and Disease/Indication.",
    },
    {
      id: "retrieve",
      label: "Retrieve Patents",
      desc: "Search SureChEMBL, PubChem, Google Patents using molecular similarity, semantic search, and hybrid retrieval.",
    },
    {
      id: "score",
      label: "Score & Filter",
      desc: "Rank patents using structural similarity, semantic relevance, confidence scores, and custom scoring.",
    },
    {
      id: "analysis",
      label: "AI Analysis",
      desc: "Explain why each patent was retrieved, identify molecular similarities, and estimate overlap confidence.",
    },
    {
      id: "risk",
      label: "Risk Assessment",
      desc: "Classify the molecule as Low Patent Risk, Requires Expert Review, or High Patent Risk.",
    },
    {
      id: "report",
      label: "Generate Report",
      desc: "Produce a structured patentability report with Executive Summary, Key Patents, Novelty Concerns, and Recommendation.",
    },
  ];

  return (
    <section
      id="workflow"
      style={{
        padding: "80px 0",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div className="container">
        <div className="fade-in" style={{ marginBottom: "52px" }}>
          <p className="section-label" style={{ marginBottom: "16px" }}>
            Technical Pipeline
          </p>
          <h2
            className="font-heading"
            style={{
              fontSize: "clamp(28px, 3vw, 38px)",
              lineHeight: 1.2,
              letterSpacing: "-0.025em",
              color: "var(--text)",
              maxWidth: "560px",
            }}
          >
            From molecule to structured report
          </h2>
        </div>

        {/* Horizontal pipeline */}
        <div
          className="fade-in workflow-pipeline"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(6, 1fr)",
            gap: "0",
            border: "1px solid var(--border)",
            overflowX: "auto",
          }}
        >
          {steps.map((step, i) => (
            <div
              key={step.id}
              style={{
                borderRight:
                  i < steps.length - 1 ? "1px solid var(--border)" : "none",
                padding: "24px 20px",
                position: "relative",
                minWidth: "160px",
              }}
            >
              {/* Step number */}
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  color: "var(--text-label)",
                  marginBottom: "12px",
                  letterSpacing: "0.06em",
                }}
              >
                0{i + 1}
              </div>

              {/* Arrow connector (except last) */}
              {i < steps.length - 1 && (
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    right: "-1px",
                    transform: "translateY(-50%)",
                    zIndex: 1,
                    width: "8px",
                    height: "8px",
                    borderTop: "1px solid var(--primary)",
                    borderRight: "1px solid var(--primary)",
                    transform: "translateY(-50%) rotate(45deg)",
                  }}
                />
              )}

              <h3
                style={{
                  fontFamily: "var(--font-body)",
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "var(--primary)",
                  marginBottom: "10px",
                  lineHeight: 1.3,
                }}
              >
                {step.label}
              </h3>
              <p
                style={{
                  fontSize: "12px",
                  lineHeight: 1.6,
                  color: "var(--text-secondary)",
                }}
              >
                {step.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Risk outcome row */}
        <div
          className="fade-in"
          style={{
            marginTop: "32px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-label)",
              letterSpacing: "0.06em",
            }}
          >
            POSSIBLE OUTCOMES
          </span>
          <span className="badge-low">Low Patent Risk</span>
          <span className="badge-review">Requires Expert Review</span>
          <span className="badge-high">High Patent Risk</span>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .workflow-pipeline { grid-template-columns: 1fr 1fr !important; }
          .workflow-pipeline > div { border-right: none !important; border-bottom: 1px solid var(--border); }
          .workflow-pipeline > div:last-child { border-bottom: none; }
        }
        @media (max-width: 480px) {
          .workflow-pipeline { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </section>
  );
}

/* ─── Final CTA ───────────────────────────────────────── */
function FinalCTA() {
  return (
    <section
      id="cta"
      style={{
        padding: "96px 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div className="container">
        <div className="fade-in" style={{ maxWidth: "640px" }}>
          <p className="section-label" style={{ marginBottom: "24px" }}>
            Get Started
          </p>

          <h2
            className="font-heading"
            style={{
              fontSize: "clamp(32px, 4vw, 52px)",
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
              color: "var(--text)",
              marginBottom: "24px",
            }}
          >
            Ready to evaluate your
            <br />
            next molecule?
          </h2>

          <p
            style={{
              fontSize: "16px",
              lineHeight: 1.7,
              color: "var(--text-secondary)",
              marginBottom: "36px",
              maxWidth: "480px",
            }}
          >
            Perform an AI-assisted Freedom-to-Operate assessment before
            advancing in the drug discovery pipeline. PatentPilot surfaces
            relevant prior art, analyzes patent overlap, and delivers a
            structured patentability report — helping researchers make
            informed decisions earlier.
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Link href="/analyze" className="btn-primary" id="cta-analyze">
              Analyze Molecule
            </Link>
            <a href="#workflow" className="btn-secondary" id="cta-demo">
              View Demo
            </a>
          </div>

          <p
            style={{
              marginTop: "24px",
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-label)",
              letterSpacing: "0.04em",
            }}
          >
            Powered by public scientific databases. AI-assisted results in under
            90 seconds.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ─── Footer ──────────────────────────────────────────── */
function Footer() {
  return (
    <footer
      style={{
        padding: "32px 0",
        background: "var(--surface)",
        borderTop: "1px solid var(--border)",
      }}
    >
      <div
        className="container"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-heading)",
            fontWeight: 300,
            fontSize: "16px",
            color: "var(--primary)",
          }}
        >
          PatentPilot
        </span>

        <div
          style={{
            display: "flex",
            gap: "32px",
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "13px",
              color: "var(--text-secondary)",
              fontWeight: 500,
            }}
          >
            Anumalasetty V S Rohith
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "var(--text-muted)",
            }}
          >
            VNRVJIET CSE
          </span>
          <a
            href="mailto:avsrohith.06@gmail.com"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "var(--text-muted)",
              textDecoration: "none",
            }}
          >
            avsrohith.06@gmail.com
          </a>
        </div>
      </div>
    </footer>
  );
}

/* ─── Page ────────────────────────────────────────────── */
export default function Home() {
  useFadeIn();

  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Features />
        <Workflow />
        <FinalCTA />
      </main>
      <Footer />
    </>
  );
}
