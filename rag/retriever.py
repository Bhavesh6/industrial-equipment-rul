"""
RAG (Retrieval-Augmented Generation) Knowledge Base Retriever
=============================================================
Indexes and retrieves maintenance manuals, standard operating procedures (SOPs),
fault catalogs, and industrial safety guidelines for RS-380 equipment diagnostics.
Operates completely offline without requiring cloud vector databases.
"""

import os
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"


class DocumentChunk:
    def __init__(self, doc_id: str, title: str, category: str, content: str, source_file: str):
        self.doc_id = doc_id
        self.title = title
        self.category = category
        self.content = content.strip()
        self.source_file = source_file
        self.tokens = self._tokenize(self.content + " " + self.title)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        # Filter common stopwords
        stops = {"the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "been"}
        return [w for w in words if w not in stops]


class MaintenanceKnowledgeRetriever:
    """
    In-memory BM25 / TF-IDF semantic retriever for industrial maintenance manuals.
    Enriched with hardware telemetry awareness.
    """

    def __init__(self, kb_path: Path = KB_DIR):
        self.kb_path = kb_path
        self.chunks: List[DocumentChunk] = []
        self.doc_freq: Dict[str, int] = {}
        self.total_docs = 0
        self.avg_doc_len = 0.0
        self._load_and_index()

    def _load_and_index(self):
        """Recursively parses all markdown files in the knowledge base."""
        if not self.kb_path.exists():
            return

        chunk_list = []
        for file_path in self.kb_path.rglob("*.md"):
            category = file_path.parent.name
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                
                # Split by Markdown H2 headers (## )
                sections = re.split(r"\n(?=##\s+)", text)
                doc_title = sections[0].split("\n")[0].replace("#", "").strip() if sections else file_path.stem

                for idx, sec in enumerate(sections):
                    lines = sec.strip().split("\n")
                    sec_title = lines[0].replace("#", "").strip() if lines else f"Section {idx+1}"
                    chunk_id = f"{file_path.stem}_{idx}"
                    chunk_list.append(DocumentChunk(
                        doc_id=chunk_id,
                        title=f"{doc_title} — {sec_title}",
                        category=category,
                        content=sec,
                        source_file=file_path.name
                    ))
            except Exception as e:
                print(f"[RAG] Warning: error reading {file_path}: {e}")

        self.chunks = chunk_list
        self.total_docs = len(self.chunks)
        if self.total_docs > 0:
            total_len = sum(len(c.tokens) for c in self.chunks)
            self.avg_doc_len = total_len / float(self.total_docs)

            # Build document frequency table
            df_counts: Dict[str, int] = {}
            for c in self.chunks:
                unique_tokens = set(c.tokens)
                for t in unique_tokens:
                    df_counts[t] = df_counts.get(t, 0) + 1
            self.doc_freq = df_counts
            print(f"[RAG] Knowledge Base Indexed: {self.total_docs} chunks loaded across {len(self.doc_freq)} terms.")

    def search(self, query: str, top_k: int = 3, telemetry: Optional[Dict[str, Any]] = None,
               prediction: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most relevant knowledge chunks using BM25 scoring
        boosted by active sensor conditions and fault states.
        """
        if not self.chunks:
            return []

        q_tokens = DocumentChunk._tokenize(query)

        # Context-aware query expansion based on live hardware anomalies
        if telemetry:
            vib = telemetry.get("vibration", 0.0)
            cur = telemetry.get("motor_current", 0.0)
            tmp = telemetry.get("temperature", 0.0)
            volt_delta = telemetry.get("cell_delta", 0.0)

            if vib > 0.40:
                q_tokens.extend(["vibration", "unbalance", "misalignment", "sop-m03", "bearing"])
            if cur > 2.50:
                q_tokens.extend(["overcurrent", "current", "brush", "armature", "stall", "short"])
            if tmp > 50.0:
                q_tokens.extend(["temperature", "overheating", "thermal", "cooling", "lubrication"])
            if volt_delta > 0.05:
                q_tokens.extend(["battery", "cell", "balance", "voltage", "saf-04"])

        if prediction:
            top_sensor = prediction.get("top_contributor", "")
            if top_sensor:
                q_tokens.append(top_sensor.replace("_", " "))

        # BM25 parameters
        k1 = 1.5
        b = 0.75

        scores = []
        for chunk in self.chunks:
            score = 0.0
            doc_len = len(chunk.tokens)
            if doc_len == 0:
                continue

            # Term frequency map for chunk
            tf_map: Dict[str, int] = {}
            for t in chunk.tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            for qt in q_tokens:
                if qt in tf_map:
                    tf = tf_map[qt]
                    df = self.doc_freq.get(qt, 1)
                    # IDF formula
                    idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))
                    # BM25 term weight
                    term_score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / self.avg_doc_len)))
                    score += term_score

            # Category boost for maintenance and troubleshooting queries
            lower_q = query.lower()
            if any(w in lower_q for w in ["how to", "procedure", "step", "fix", "repair", "replace", "maintain"]):
                if chunk.category == "maintenance_procedures":
                    score *= 1.3
            elif any(w in lower_q for w in ["fault", "why", "cause", "issue", "problem", "wear", "noise"]):
                if chunk.category == "fault_descriptions":
                    score *= 1.3
            elif any(w in lower_q for w in ["safe", "danger", "trip", "stop", "hazard", "loto"]):
                if chunk.category == "safety_guidelines":
                    score *= 1.3
            elif any(w in lower_q for w in ["spec", "rating", "limit", "rpm", "amp", "volt", "manual"]):
                if chunk.category == "equipment_manuals":
                    score *= 1.3

            scores.append((chunk, score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)
        top_results = scores[:top_k]

        formatted = []
        for chunk, s in top_results:
            formatted.append({
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "category": chunk.category,
                "source": chunk.source_file,
                "score": round(float(s), 3),
                "content": chunk.content
            })
        return formatted

    def format_context_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks into clean markdown context for the LLM."""
        if not chunks:
            return ""

        lines = ["\n### 📚 Retrieved Maintenance Knowledge Base (RAG Context):"]
        for idx, c in enumerate(chunks, 1):
            lines.append(f"#### [{idx}] {c['title']} (Source: {c['source']})")
            lines.append(c['content'])
            lines.append("")
        return "\n".join(lines)


# Singleton instance for quick imports
rag_retriever = MaintenanceKnowledgeRetriever()

if __name__ == "__main__":
    print("Testing RAG Retriever...")
    results = rag_retriever.search("How do I fix high vibration and bearing wear?")
    for r in results:
        print(f"-> Found [{r['category']}] {r['title']} (Score: {r['score']})")
