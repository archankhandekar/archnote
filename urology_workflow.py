"""End-to-end script for EPIC EHR data extraction, anonymization, and HELM
benchmark evaluation.

The script demonstrates how one might securely connect to the EPIC FHIR API,
collect urology clinic data from the last three months, anonymize the results,
and evaluate custom scenarios using Stanford's HELM framework. Actual network
access to EPIC is not implemented here; the functions serve as a template and
should be adapted for real deployments with proper authentication, secure
storage of credentials, and HIPAA-compliant processes.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
import pandas as pd
import re

try:
    from helm.benchmark.run import run_benchmark
    from helm.benchmark.scenarios.scenario import Scenario, Instance, Reference
except ImportError:
    run_benchmark = None  # helm library not installed

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_epic_auth_token() -> str:
    """Retrieve OAuth token from EPIC FHIR API. Credentials are read from environment variables."""
    client_id = os.getenv("EPIC_CLIENT_ID")
    client_secret = os.getenv("EPIC_CLIENT_SECRET")
    token_url = os.getenv("EPIC_TOKEN_URL")
    if not all([client_id, client_secret, token_url]):
        logging.error("Missing EPIC API credentials or token URL.")
        raise EnvironmentError("EPIC credentials not configured")
    response = requests.post(
        token_url,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError("No access token returned from EPIC API")
    logging.info("Successfully retrieved EPIC auth token")
    return token


def fetch_urology_encounters(token: str) -> List[Dict[str, Any]]:
    """Fetch urology clinic encounters in the last 3 months from EPIC FHIR API."""
    base_url = os.getenv("EPIC_FHIR_BASE_URL")
    if not base_url:
        raise EnvironmentError("EPIC FHIR base URL is not set")

    three_months_ago = datetime.utcnow() - timedelta(days=90)
    date_filter = three_months_ago.strftime("%Y-%m-%d")
    headers = {"Authorization": f"Bearer {token}"}

    # The query parameters may vary depending on EPIC implementation
    params = {
        "date": f"ge{date_filter}",  # on or after date_filter
        "department": "UROLOGY",
        "organization": "UM",
    }
    encounters = []
    url = f"{base_url}/Encounter"
    while url:
        logging.info("Fetching encounters from %s", url)
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        encounters.extend(data.get("entry", []))
        # Pagination using 'next' link if present
        url = next((link.get("url") for link in data.get("link", []) if link.get("relation") == "next"), None)
        params = None  # parameters only for first call
    logging.info("Fetched %d encounters", len(encounters))
    return encounters


def extract_patient_data(encounters: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
    """Retrieve notes, diagnoses, procedures, labs, and imaging reports for each encounter."""
    base_url = os.getenv("EPIC_FHIR_BASE_URL")
    headers = {"Authorization": f"Bearer {token}"}
    patient_data = []

    for enc in encounters:
        encounter_id = enc["resource"].get("id")
        if not encounter_id:
            continue
        logging.info("Processing encounter %s", encounter_id)
        patient_entry = {"encounter_id": encounter_id, "resources": {}}
        # Retrieve clinical notes
        note_url = f"{base_url}/DocumentReference"
        note_params = {"encounter": encounter_id}
        notes_resp = requests.get(note_url, headers=headers, params=note_params, timeout=10)
        notes_resp.raise_for_status()
        patient_entry["resources"]["notes"] = notes_resp.json().get("entry", [])

        # Diagnoses (conditions)
        cond_url = f"{base_url}/Condition"
        cond_params = {"encounter": encounter_id}
        cond_resp = requests.get(cond_url, headers=headers, params=cond_params, timeout=10)
        cond_resp.raise_for_status()
        patient_entry["resources"]["diagnoses"] = cond_resp.json().get("entry", [])

        # Procedures
        proc_url = f"{base_url}/Procedure"
        proc_params = {"encounter": encounter_id}
        proc_resp = requests.get(proc_url, headers=headers, params=proc_params, timeout=10)
        proc_resp.raise_for_status()
        patient_entry["resources"]["procedures"] = proc_resp.json().get("entry", [])

        # Labs (observations)
        lab_url = f"{base_url}/Observation"
        lab_params = {"encounter": encounter_id, "category": "laboratory"}
        lab_resp = requests.get(lab_url, headers=headers, params=lab_params, timeout=10)
        lab_resp.raise_for_status()
        patient_entry["resources"]["labs"] = lab_resp.json().get("entry", [])

        # Imaging reports (DiagnosticReport)
        img_url = f"{base_url}/DiagnosticReport"
        img_params = {"encounter": encounter_id}
        img_resp = requests.get(img_url, headers=headers, params=img_params, timeout=10)
        img_resp.raise_for_status()
        patient_entry["resources"]["imaging"] = img_resp.json().get("entry", [])

        patient_data.append(patient_entry)

    logging.info("Extracted data for %d encounters", len(patient_data))
    return patient_data


def anonymize_text(text: str) -> str:
    """Basic anonymization removing obvious identifiers."""
    patterns = [
        r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # Names
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format
        r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b",  # Phone numbers
        r"\b\d{1,3} [A-Za-z0-9 .]+, [A-Za-z ]+, [A-Z]{2} \d{5}\b",  # Addresses
    ]
    anonymized = text
    for pat in patterns:
        anonymized = re.sub(pat, "[REDACTED]", anonymized)
    return anonymized


def anonymize_data(patient_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Anonymize patient data using simple text replacement."""
    for entry in patient_data:
        for category, items in entry.get("resources", {}).items():
            for item in items:
                resource = item.get("resource", {})
                for key, value in resource.items():
                    if isinstance(value, str):
                        resource[key] = anonymize_text(value)
                    elif isinstance(value, list):
                        resource[key] = [anonymize_text(str(v)) for v in value]
    logging.info("Anonymization complete")
    return patient_data


def save_to_json(data: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logging.info("Data written to %s", path)


def create_helm_dataset(data: List[Dict[str, Any]], path: str) -> None:
    """Create a HELM-compatible dataset JSON."""
    instances = []
    for entry in data:
        notes = entry["resources"].get("notes", [])
        note_texts = [n.get("resource", {}).get("text", {}).get("div", "") for n in notes]
        instance_text = "\n".join(note_texts)
        instances.append({"input": instance_text, "references": [{"output": ""}]})
    dataset = {"instances": instances}
    with open(path, "w") as f:
        json.dump(dataset, f, indent=2)
    logging.info("HELM dataset saved to %s", path)


def define_custom_scenarios(path: str) -> None:
    """Save custom HELM scenario configuration."""
    scenarios = {
        "name": "urology_custom",
        "tasks": [
            {
                "task_name": "extract_hpi",
                "description": "Extract structured HPI from notes",
            },
            {
                "task_name": "list_procedures",
                "description": "Identify procedures and diagnostics chronologically",
            },
            {
                "task_name": "summarize_diagnoses",
                "description": "Summarize diagnoses",
            },
        ],
    }
    with open(path, "w") as f:
        json.dump(scenarios, f, indent=2)
    logging.info("Scenario definitions saved to %s", path)


def run_helm(dataset_path: str, scenario_path: str, model: str = "openai/gpt-4o") -> Dict[str, Any]:
    if not run_benchmark:
        logging.error("crfm-helm library is not installed")
        raise RuntimeError("crfm-helm not available")
    config = {
        "suite": "urology_suite",
        "scenarios": scenario_path,
        "model": model,
        "dataset": dataset_path,
    }
    results = run_benchmark(config)
    logging.info("HELM benchmark completed")
    return results


def summarize_metrics(results: Dict[str, Any]) -> Dict[str, float]:
    """Calculate key performance metrics from HELM results."""
    # Placeholder summary; actual metrics depend on result structure
    metrics = {
        "accuracy": results.get("accuracy", 0.0),
        "precision": results.get("precision", 0.0),
        "recall": results.get("recall", 0.0),
        "f1": results.get("f1", 0.0),
    }
    logging.info("Metrics: %s", metrics)
    return metrics


def main():
    try:
        token = get_epic_auth_token()
        encounters = fetch_urology_encounters(token)
        data = extract_patient_data(encounters, token)
        data = anonymize_data(data)

        os.makedirs("output", exist_ok=True)
        raw_json = "output/urology_anonymized.json"
        helm_dataset = "output/helm_dataset.json"
        scenarios_file = "output/scenarios.json"

        save_to_json(data, raw_json)
        create_helm_dataset(data, helm_dataset)
        define_custom_scenarios(scenarios_file)

        results = run_helm(helm_dataset, scenarios_file)
        metrics = summarize_metrics(results)

        with open("output/metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        logging.info("Workflow complete")
    except Exception as e:
        logging.exception("Workflow failed: %s", e)


if __name__ == "__main__":
    main()
