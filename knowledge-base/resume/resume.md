---
source_id: resume-abhishek-palle-current
source_type: RESUME
source_name: Resume
section: Full Resume
project_id: null
experience_type: GENERAL
visibility: PUBLIC
approved: true
source_url: /resume.pdf
document_version: "2026-10"
updated_at: "2026-10-16"
section_experience_types:
  WORK EXPERIENCE: PROFESSIONAL
  SELECTED PROJECTS: PORTFOLIO
  EDUCATION: EDUCATION
---

# ABHISHEK PALLE

## SUMMARY

Senior ML/AI Engineer with 8+ years building production ML and Generative AI systems end-to-end on Google Cloud - agentic LLM applications, RAG pipelines, prompt engineering and evaluation, and CI/CD-driven deployment and monitoring.

## TECHNICAL SKILLS

- Languages & Frameworks: Python, TypeScript, SQL, PySpark, FastAPI, React, Git
- GCP&MLOps: Vertex AI, Cloud Run, AlloyDB, BigQuery, Cloud Composer (Airflow), Docker, CI/CD, monitoring
- ML & Evaluation: PyTorch, TensorFlow, Hugging Face, XGBoost, scikit-learn, BERT, eval harness, regression testing, release gating
- RAG & Retrieval: pgvector, Vertex AI Search, embeddings, hybrid retrieval, reranking, chunking, citation validation
- GenAI & Agents: Google ADK, LangGraph, LangChain, Gemini / OpenAI / Anthropic APIs, prompt engineering, AI guardrails

## WORK EXPERIENCE

### CNA Insurance, Senior Machine Learning Engineer | March 2021 - Present

#### Agentic LLM Platform for Underwriting Intelligence

- Architected and shipped an agentic LLM system processing ~3K business applications weekly to automate SIC/NAICS classification and evaluate 400+ underwriting risk questions.
- Engineered an inference pipeline executing 7 grounded LLM calls per application and processing ~100K calls/month at ~$0.30 per application, with structured outputs, versioned prompts/models, and evidence logs of search queries and grounding URLs.
- Built an eval harness with a 500-application golden dataset for regression testing, a human-in-the-loop app where underwriters accept/reject predictions, achieving ~95% acceptance rate in production

#### LLM Multi-Label Text Classification with Evidence Attribution - Fire Loss Claims

- Productionized a Composer-orchestrated LLM inference pipeline classifying claim narratives across 12 binary fire-cause labels, with structured-output validation, conditional retries for missing predictions, and verbatim claim-text evidence for every label.
- Evaluated the pipeline on 1,000 human-labeled large-loss claims, achieving 92.6% recall across 12 fire-cause labels; built pre-release regression tests to protect model quality for portfolio-level analytics.

#### Fine-Tuned BERT Multi-Label Classification - Water Damage Claims

- Led five data scientists to deliver the first structured view of water-loss causes for portfolio-level analytics - taxonomy design, gold-standard annotation, and fine-tuned BERT classifiers mapping claim narratives to 23 cause-of-loss categories at 0.97 weighted F1
- Productionized monthly batch inference for ~2.5K newly closed claims, orchestrating Vertex AI Custom Jobs on Cloud Composer from digest-pinned CI images; volume and prediction-rate drift monitoring fails the run and alerts before anomalous output reaches review.

#### Explainable Fraud Detection & Ranking Platform

- Built a monthly batch-scoring platform (Cloud Composer + Vertex AI Custom Jobs) ranking 45K open claims into a fixed-capacity investigator queue, pairing XGBoost probabilities with per-claim SHAP drivers in a Looker view.
- Built for reproducibility and audit: immutable feature snapshots, scoring pinned to an explicitly promoted model version so retrains never auto-deploy, and 6 data-quality + 7 reconciliation assertions gating publication.
- Improved precision 23% -> 40% and F1 0.34 -> 0.52; Top-200 hit rate rose 36% -> 49% (71 -> 99 actionable cases), outperforming 5 of 7 existing referral sources.

#### ML Pricing System - Vehicle Service Contracts

- Built a two-stage GLM (Poisson frequency x Gamma severity) on 3.7M contracts and 1.4M claims, delivered as the rating workbook the pricing team validates and dealerships quote from, release-gated on model-vs-workbook parity.
- Lifted Gini 0.4 -> 0.65 and cut decile loss-ratio spread 96% (1.42 -> 0.06) on a 448K-contract holdout.

### Stanley Black & Decker, Machine Learning Intern | May 2019 - Dec 2019

#### Time-Series Forecasting and Industrial Anomaly Detection

- Built an ensemble time-series forecasting pipeline to predict sales across tool product lines, reducing forecast MAPE by 63% and supporting inventory planning.
- Developed an unsupervised anomaly-detection pipeline for machine-sensor data to identify early indicators of equipment failure and support preventive maintenance.

### Eternal Robotics, Machine Learning Engineer | July 2017 - June 2018

#### Edge Computer Vision for Autonomous Painting

- Engineered and deployed an end-to-end computer vision inference system on edge hardware, transforming captured images into spatial guidance for the MYRO robot's autonomous painting.
- Built the ML training pipeline across image collection, annotation, augmentation, and transfer learning, fine-tuning Faster R-CNN in PyTorch and achieving 0.78 mAP@0.5 on held-out test data.
- Integrated model outputs with the robotic workflow, providing paintable regions and exclusion zones for downstream painting operations.

### Production Modeling Corporation, Senior Data Scientist | July 2016 - June 2017

- Developed a Python-based simulation model to identify automotive assembly-line bottlenecks, recommending process changes projected to increase throughput by 12 vehicles per hour.
- Built a Python-based linear programming model to optimize product allocation from distribution centers to customers, enabling more efficient supply chain planning.

## SELECTED PROJECTS

### Policy-Grounded Workers' Compensation Claims Assistant

- Built a full-stack RAG app (React/TypeScript, FastAPI, Cloud Run) over a pre-indexed corpus of policy forms, endorsements, and jurisdictional regulations, with policy-scoped hybrid retrieval on AlloyDB pgvector, reranking, and citation-grounded generation.
- Architected the evaluation framework, scoring a 100-case golden dataset on Recall@10, citation precision/recall, and abstention accuracy, with release gates that block quality regressions.

### Agentic Commercial Auto Underwriting

- Architected a Google ADK supervisor-agent workflow that coordinates specialized agents for exposure review, loss analysis, and broker clarification over LLM-extracted ACORD applications, vehicle schedules, loss runs, and broker submissions.
- Built deterministic validation and referral controls with typed agent handoffs and source-grounded findings; evaluated the workflow on 100 synthetic submissions with release gates for extraction, agent dispatch, issue resolution, and routing regressions.

## EDUCATION

- Texas A&M University, College Station, TX - M.S. Industrial Engineering (Data Science) | GPA: 3.6 | Dec 2020
- Birla Institute of Technology and Science, Pilani, India - B.Tech, Mechanical Engineering | GPA: 3.6 | May 2016
