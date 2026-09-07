"""Import the course tables from the curriculum PDF into Episteme's JSON catalog."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pdfplumber


PROJECT_ID = re.compile(r"^(P(?:0\.\d+|\d+(?:[\ufffd\u2013-]P?\d+)?))\b")
HEADER = "Project ID &"


def dewrap(value: str | None) -> str:
    if not value:
        return ""
    text = " ".join(part.strip() for part in value.splitlines() if part.strip())
    text = re.sub(r"\s+([,.;:!?\)])", r"\1", text)
    text = re.sub(r"([\(])\s+", r"\1", text)
    text = re.sub(r"(?<=\w)_\s+(?=\w)", "_", text)
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    replacements = {
        "Implementati on": "Implementation",
        "configurati on": "configuration",
        "denominator= 0": "denominator=0",
        "nume rator": "numerator",
        "AP I_PORT": "API_PORT",
        "python-dotenv .": "python-dotenv.",
        "calculate_ohm s_law": "calculate_ohms_law",
        "Multi-Conditio n": "Multi-Condition",
        "Documentatio n": "Documentation",
        "Command-Lin e": "Command-Line",
        "RFC-Complian t": "RFC-Compliant",
        "Comprehensiv e": "Comprehensive",
        "Heterogeneou s": "Heterogeneous",
        "ACID-Complia nt": "ACID-Compliant",
        "Database-Bac ked": "Database-Backed",
        "Form-to-Sprea dsheet": "Form-to-Spreadsheet",
        "Threshold-Driv en": "Threshold-Driven",
        "Database-Trig gered": "Database-Triggered",
        "Synchronizatio n": "Synchronization",
        "Webhook-to-C RM": "Webhook-to-CRM",
        "High-Throughp ut": "High-Throughput",
        "Multi-Workflo w": "Multi-Workflow",
        "Transformation s": "Transformations",
        "Auto-Respons e": "Auto-Response",
        "Schema-Enfor ced": "Schema-Enforced",
        "Human-in-the- Loop": "Human-in-the-Loop",
        "Semi-Structure d": "Semi-Structured",
        "Citation-Backe d": "Citation-Backed",
        "Action-Oriente d": "Action-Oriented",
        "Enterprise-Scal e": "Enterprise-Scale",
        "Multi-Containe r": "Multi-Container",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()


def split_id_title(value: str) -> tuple[str, str]:
    normalized = value.replace("\ufffd", "-").replace("\u2013", "-")
    match = PROJECT_ID.match(normalized)
    if not match:
        raise ValueError(f"Could not parse project identifier from {value!r}")
    project_id = match.group(1).replace("PP", "P")
    title = dewrap(normalized[match.end() :])
    return project_id, title


def split_example(value: str) -> tuple[str, str]:
    text = dewrap(value)
    parts = re.split(r"\bExpected\s+Output:\s*", text, maxsplit=1, flags=re.I)
    example_input = re.sub(r"^Input:\s*", "", parts[0], flags=re.I).strip()
    example_output = parts[1].strip() if len(parts) == 2 else ""
    return example_input, example_output


def import_pdf(source: Path) -> dict:
    records: list[dict] = []
    current: dict | None = None
    phase = None
    phase_titles: dict[int, str] = {}

    with pdfplumber.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            lines = (page.extract_text() or "").splitlines()
            headings = []
            for index, line in enumerate(lines):
                match = re.search(r"Phase\s+(\d+)\s*:\s*(.+)", line)
                if not match:
                    continue
                number = int(match.group(1))
                title = match.group(2).strip()
                if index + 1 < len(lines):
                    continuation = lines[index + 1].strip()
                    if continuation and len(continuation) < 55 and not continuation.startswith(f"Phase {number}"):
                        title += " " + continuation
                phase_titles[number] = title
            heading_hits = page.search(r"Phase\s+\d+\s*:", regex=True) or []
            heading_events = []
            for hit in heading_hits:
                number = int(re.search(r"\d+", hit["text"]).group())
                heading_events.append((hit["top"], "phase", number))
            table_events = [(table.bbox[1], "table", table) for table in page.find_tables()]

            for _, kind, payload in sorted(heading_events + table_events, key=lambda item: item[0]):
                if kind == "phase":
                    if current:
                        records.append(current)
                        current = None
                    phase = payload
                    continue
                for row in payload.extract():
                    if not row or len(row) < 5:
                        continue
                    if (row[0] or "").startswith(HEADER):
                        if current:
                            records.append(current)
                            current = None
                        continue
                    first = (row[0] or "").strip()
                    starts_project = bool(PROJECT_ID.match(first.replace("\ufffd", "-").replace("\u2013", "-")))
                    if starts_project:
                        if current:
                            records.append(current)
                        current = {"phase": phase, "page": page_number, "cells": [cell or "" for cell in row[:5]]}
                    elif current:
                        for index, cell in enumerate(row[:5]):
                            if cell:
                                current["cells"][index] += "\n" + cell
            if heading_events:
                phase = heading_events[-1][2]
    if current:
        records.append(current)

    projects = []
    for ordinal, record in enumerate(records, 1):
        project_id, title = split_id_title(record["cells"][0])
        example_input, example_output = split_example(record["cells"][4])
        projects.append(
            {
                "id": project_id,
                "ordinal": ordinal,
                "phase": record["phase"],
                "phase_title": phase_titles.get(record["phase"], f"Phase {record['phase']}"),
                "title": title,
                "prerequisites": dewrap(record["cells"][1]),
                "concept": dewrap(record["cells"][2]),
                "instructions": dewrap(record["cells"][3]),
                "example_input": example_input,
                "example_output": example_output,
                "source_page": record["page"],
            }
        )
    return {"schema_version": 1, "source_title": source.stem, "project_count": len(projects), "projects": projects}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    catalog = import_pdf(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Imported {catalog['project_count']} projects into {args.output}")


if __name__ == "__main__":
    main()
