"""Build only from a fresh public probe, never the owner's repository."""
import json
from pathlib import Path
from app.models import CandidateProfile, Job


def main():
    evidence = json.loads(Path("data/release-probe.json").read_text())
    jobs = []
    for value in evidence["jobs"]:
        job = Job.model_validate(value)
        job.notes = job.contact = ""
        job.favorite = job.hidden = False
        job.application_status = "not_applied"
        job.applied_at = job.interview_at = job.reminder_at = None
        job.corrections = {}
        # Keep source evidence intact: truncation can erase eligibility restrictions.
        job.provenance = {"public_snapshot": True, "snapshot_at": evidence["verified_at"], "listing_kind": value.get("provenance", {}).get("listing_kind", "internship"), "source_values": value.get("provenance", {}).get("source_values", {})}
        jobs.append(job.model_dump(mode="json"))
    profile = CandidateProfile(name="Demo candidate", education="Computer Science undergraduate", country="India", preferred_locations=["India"], skills=["JavaScript", "TypeScript", "React", "Next.js", "Python", "FastAPI", "Git"], preferred_roles=["software engineering", "frontend", "full-stack"], remote_preference=True, paid_only=True)
    snapshot = {"snapshot_at": evidence["verified_at"], "profile": profile.model_dump(mode="json"), "jobs": jobs, "runs": [{"id":"public-snapshot", "status":"completed", "query":"", "started_at":evidence["verified_at"], "completed_at":evidence["verified_at"], "provider_results":evidence["combined_reports"], "details":evidence["metrics"]}], "probe_metrics":evidence["metrics"]}
    path = Path("demo/snapshot.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2))
    print("Public snapshot:", len(jobs), "records;", evidence["unique_active"], "active-looking;", evidence["verified_at"])


if __name__ == "__main__":
    main()
