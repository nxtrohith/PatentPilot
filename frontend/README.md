# PatentPilot Frontend 🧬💻
> Interactive Next.js React Dashboard for Freedom-to-Operate Analysis

This directory contains the user interface for PatentPilot, a clean, responsive single-page dashboard designed for researchers to analyze chemical compounds and explore intellectual property overlaps.

## ✨ Features

- **Molecular Input Form**: Simple submission form accepting SMILES strings, biological target labels, and disease indications.
- **Server-Sent Events (SSE) Progress Panel**: Displays real-time, animated progress steps directly linked to the backend LangGraph execution workflow.
- **Dynamic FTO Report View**: Interactive display of retrieved patents, Tanimoto similarity percentages, executive summary, novelty concerns, and overall patent risk classification.
- **Details Sidebar**: Drill down into individual patents to understand *why* they were flagged, what molecular groups overlap, and overall confidence scores.
- **Analysis History Management**: A comprehensive database page to browse previous reports, search by keywords, filter by risk level, reopen saved details, and delete entries.

## 🛠️ Tech Stack & Design

- **Framework**: Next.js 15 (App Router, React 19)
- **Language**: TypeScript
- **Styling**: Vanilla CSS (TailwindCSS not used, custom styled for a premium dark mode, glassmorphism, responsive grids, and subtle fade-in micro-animations).

## 🚀 Running the Frontend

### 1. Prerequisites
Ensure you have [Node.js](https://nodejs.org/) (v18+) and `npm` installed.

### 2. Configure Backend Connection
The application is pre-configured to communicate with the FastAPI backend running at `http://localhost:8000`. Ensure your backend server is up and running before submitting analyses.

### 3. Run Development Server
Install dependencies and run the local development server:
```bash
# Install packages
npm install

# Start development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### 4. Build for Production
To create an optimized production build of the frontend:
```bash
npm run build
npm start
```
