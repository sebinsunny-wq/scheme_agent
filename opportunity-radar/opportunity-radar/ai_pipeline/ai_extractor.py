"""
ai_extractor.py
Enriches scraped opportunities using HuggingFace Inference API (free tier).

- Summarization  → facebook/bart-large-cnn
- Zero-shot classification → facebook/bart-large-mnli
- NER / date/amount extraction → regex + lightweight rules

No GPU, no paid API, no local model download required.
"""

import os
import re
import json
import time
import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HF_API_KEY  = os.environ.get("HF_API_KEY", "")           # set in GitHub Secrets
HF_BASE_URL = "https://api-inference.huggingface.co/models"

SUMMARIZE_MODEL  = "facebook/bart-large-cnn"
CLASSIFY_MODEL   = "facebook/bart-large-mnli"

CATEGORIES = [
    "Grant", "Fellowship", "Accelerator", "Incubation",
    "Innovation Challenge", "CSR Opportunity", "Competition",
    "Government Scheme", "Research Funding",
]

SECTORS = [
    "Agriculture", "Biotech", "CleanTech", "EdTech", "FinTech",
    "HealthTech", "Manufacturing", "Social Impact", "AI/DeepTech",
    "General / Mixed",
]


# ──────────────────────────────────────────────
# HuggingFace API helpers
# ──────────────────────────────────────────────
def hf_request(model: str, payload: dict, retries: int = 3) -> Optional[dict]:
    url     = f"{HF_BASE_URL}/{model}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 503:
                log.warning(f"Model loading ({model}), waiting 20s…")
                time.sleep(20)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning(f"HF request error (attempt {attempt+1}): {e}")
            time.sleep(5)
    return None


def summarize(text: str, max_length: int = 130) -> str:
    if not text or len(text) < 100:
        return text
    text = text[:1024]     # BART input limit
    result = hf_request(SUMMARIZE_MODEL, {
        "inputs": text,
        "parameters": {"max_length": max_length, "min_length": 40, "do_sample": False},
    })
    if result and isinstance(result, list) and "summary_text" in result[0]:
        return result[0]["summary_text"]
    return text[:300] + "…"


def classify(text: str, labels: list[str]) -> str:
    if not text:
        return labels[-1]
    result = hf_request(CLASSIFY_MODEL, {
        "inputs": text[:512],
        "parameters": {"candidate_labels": labels, "multi_label": False},
    })
    if result and "labels" in result:
        return result["labels"][0]
    return labels[-1]


# ──────────────────────────────────────────────
# Rule-based extractors (fast, no API cost)
# ──────────────────────────────────────────────
DATE_PATTERNS = [
    r"\b(\d{1,2}[\s\-/]\w+[\s\-/]20\d{2})\b",
    r"\b(\w+ \d{1,2},?\s+20\d{2})\b",
    r"\b(20\d{2}-\d{2}-\d{2})\b",
    r"\b(deadline[:\s]+[^\n.]{5,40})\b",
    r"\b(last date[:\s]+[^\n.]{5,40})\b",
    r"\b(apply by[:\s]+[^\n.]{5,40})\b",
    r"\b(closes on[:\s]+[^\n.]{5,40})\b",
]

AMOUNT_PATTERNS = [
    r"(?:INR|₹|Rs\.?)\s*[\d,]+(?:\s*(?:lakh|crore|lakhs|crores|L|Cr))?",
    r"[\d,]+\s*(?:lakh|crore|lakhs|crores)\s*(?:rupees)?",
    r"\$[\d,]+(?:K|M|B)?",
    r"USD\s*[\d,]+",
    r"up to\s+(?:INR|₹|Rs\.?|USD|\$)?\s*[\d,]+[^\s]*",
    r"grant of\s+(?:INR|₹|Rs\.?|USD|\$)?\s*[\d,]+[^\s]*",
    r"funding of\s+(?:INR|₹|Rs\.?|USD|\$)?\s*[\d,]+[^\s]*",
]

ELIGIBILITY_PATTERNS = [
    r"(?:eligible|eligibility)[:\s]+([^.!\n]{20,200})",
    r"(?:who can apply)[:\s]+([^.!\n]{20,200})",
    r"(?:open to)[:\s]+([^.!\n]{20,200})",
    r"(?:for (?:startups?|companies|entrepreneurs|students|researchers))[^\n.]{10,150}",
]

TAG_KEYWORDS = [
    "grant", "fellowship", "accelerator", "incubation", "challenge",
    "hackathon", "funding", "startup", "deeptech", "ai", "biotech",
    "cleantech", "edtech", "fintech", "csr", "government", "india",
    "innovation", "research", "seed", "competition",
]


def extract_deadline(text: str) -> str:
    for pat in DATE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:80]
    return ""


def extract_amount(text: str) -> str:
    for pat in AMOUNT_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:80]
    return ""


def extract_eligibility(text: str) -> str:
    for pat in ELIGIBILITY_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return ""


def extract_tags(text: str) -> str:
    t = text.lower()
    return ",".join(kw for kw in TAG_KEYWORDS if kw in t)


# ──────────────────────────────────────────────
# MAIN ENRICHMENT PIPELINE
# ──────────────────────────────────────────────
def enrich_opportunity(opp: dict, use_hf: bool = True) -> dict:
    full_text = f"{opp.get('title', '')} {opp.get('description', '')}"

    # Rule-based (always run — free)
    if not opp.get("deadline"):
        opp["deadline"] = extract_deadline(full_text)
    if not opp.get("funding_amount"):
        opp["funding_amount"] = extract_amount(full_text)
    if not opp.get("eligibility"):
        opp["eligibility"] = extract_eligibility(full_text)
    if not opp.get("tags"):
        opp["tags"] = extract_tags(full_text)

    # HuggingFace (runs if key available)
    if use_hf and HF_API_KEY:
        if not opp.get("ai_summary"):
            opp["ai_summary"] = summarize(full_text)
            time.sleep(1)                       # avoid rate limit

        if not opp.get("category"):
            opp["category"] = classify(full_text, CATEGORIES)
            time.sleep(1)

        if opp.get("sector") in ("", "Mixed", None):
            opp["sector"] = classify(full_text, SECTORS)
            time.sleep(1)
    else:
        # Fallback: simple rule-based classification
        if not opp.get("category"):
            t = full_text.lower()
            if "fellowship"  in t: opp["category"] = "Fellowship"
            elif "accelerat" in t: opp["category"] = "Accelerator"
            elif "incubat"   in t: opp["category"] = "Incubation"
            elif "challenge" in t: opp["category"] = "Innovation Challenge"
            elif "csr"       in t: opp["category"] = "CSR Opportunity"
            elif "grant"     in t: opp["category"] = "Grant"
            else:                  opp["category"] = "Government Scheme"

        if not opp.get("ai_summary"):
            opp["ai_summary"] = opp.get("description", "")[:200]

    return opp


def run_pipeline(input_file: str = "scraped_opportunities.json",
                 output_file: str = "enriched_opportunities.json"):
    with open(input_file) as f:
        opps = json.load(f)

    log.info(f"Enriching {len(opps)} opportunities…")
    use_hf = bool(HF_API_KEY)
    if not use_hf:
        log.warning("HF_API_KEY not set — using rule-based extraction only")

    enriched = []
    for i, opp in enumerate(opps):
        log.info(f"[{i+1}/{len(opps)}] {opp.get('title', '')[:60]}")
        enriched.append(enrich_opportunity(opp, use_hf=use_hf))

    with open(output_file, "w") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    log.info(f"Saved {len(enriched)} enriched records to {output_file}")
    return enriched


if __name__ == "__main__":
    run_pipeline()
