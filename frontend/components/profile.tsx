"use client";
import { useEffect, useState } from "react";
import { api, Profile, roles } from "../lib/api";
import { Upload, Save } from "lucide-react";
export function ProfileEditor({ onSaved, readOnly = false }: { onSaved: () => void; readOnly?: boolean }) {
  const [profile, setProfile] = useState<Profile>();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [skillsText, setSkillsText] = useState("");
  const [extracted, setExtracted] = useState<{
    skills: string[];
    education: string[];
    suggested_role: string;
  }>();
  function loadProfile() {
    setMessage("");
    api<Profile>("profile")
      .then((p) => {
        setProfile(p);
        setSkillsText(p.skills.join(", "));
      })
      .catch((e) => setMessage(e.message));
  }
  useEffect(() => { loadProfile(); }, []);
  async function resume(file: File) {
    setBusy(true);
    setMessage("");
    try {
      if (file.size > 2_000_000)
        throw new Error("Resume must be smaller than 2 MB");
      const result = await api<{
        skills: string[];
        education: string[];
        suggested_role: string;
      }>("resume/analyze", {
        method: "POST",
        headers: { "Content-Type": file.type || "text/plain" },
        body: file,
      });
      setExtracted(result);
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("profile", {
        method: "PUT",
        body: JSON.stringify({
          ...profile,
          skills: skillsText
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      });
      setMessage("Profile saved. Recommendations have been recalculated.");
      onSaved();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!profile) return <div><p role="status">{message || "Loading profile..."}</p>{message && <button onClick={loadProfile}>Retry</button>}</div>;
  return (
    <form className="profile-form" onSubmit={save}>
      <fieldset disabled={readOnly} className="profile-fields">
      <div className="section-heading">
        <div>
          <h2>Your next role starts here</h2>
          <p className="muted">
            Your skills and preferences shape every recommendation.
          </p>
        </div>
        <button className="primary-button" disabled={busy}>
          <Save size={16} />
          Save profile
        </button>
      </div>
      <div className="form-grid">
        <label>
          Name
          <input
            value={profile.name}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })}
          />
        </label>
        <label>
          Education
          <input
            value={profile.education}
            onChange={(e) =>
              setProfile({ ...profile, education: e.target.value })
            }
          />
        </label>
        <label>
          Country
          <input
            value={profile.country}
            onChange={(e) =>
              setProfile({ ...profile, country: e.target.value })
            }
          />
        </label>
        <label>
          Graduation year
          <input
            type="number"
            min="2000"
            max="2100"
            value={profile.graduation_year || ""}
            onChange={(e) =>
              setProfile({
                ...profile,
                graduation_year: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </label>
        <label>
          Experience in months
          <input
            type="number"
            min="0"
            max="600"
            value={profile.experience_months}
            onChange={(e) =>
              setProfile({
                ...profile,
                experience_months: Number(e.target.value),
              })
            }
          />
        </label>
        <label>
          Preferred locations
          <input
            value={profile.preferred_locations.join(", ")}
            onChange={(e) =>
              setProfile({
                ...profile,
                preferred_locations: e.target.value
                  .split(",")
                  .map((s) => s.trim()),
              })
            }
          />
        </label>
      </div>
      <label>
        Skills, separated by commas
        <textarea
          aria-label="Skills, separated by commas"
          value={skillsText}
          onChange={(e) => setSkillsText(e.target.value)}
        />
      </label>
      <fieldset>
        <legend>Roles you are interested in</legend>
        <div className="role-options">
          {roles.map((role) => (
            <label className="check" key={role}>
              <input
                type="checkbox"
                checked={profile.preferred_roles.includes(role)}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    preferred_roles: e.target.checked
                      ? [...profile.preferred_roles, role]
                      : profile.preferred_roles.filter((r) => r !== role),
                  })
                }
              />
              {role}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="form-grid">
        <label className="check">
          <input
            type="checkbox"
            checked={profile.remote_preference}
            onChange={(e) =>
              setProfile({ ...profile, remote_preference: e.target.checked })
            }
          />
          Prefer remote opportunities
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={profile.paid_only}
            onChange={(e) =>
              setProfile({ ...profile, paid_only: e.target.checked })
            }
          />
          Prioritize paid internships
        </label>
      </div>
      <section className="resume-section">
        <h3>Import skills from your resume</h3>
        <p className="muted">
          PDF or text, up to 2 MB. The file is processed temporarily and is not
          saved.
        </p>
        <label className="upload">
          <Upload size={18} />
          Choose resume
          <input
            type="file"
            accept=".pdf,.txt"
            disabled={busy}
            onChange={(e) => e.target.files?.[0] && resume(e.target.files[0])}
          />
        </label>
        {extracted && (
          <div className="extracted">
            <h4>Review extracted information</h4>
            <p>{extracted.skills.join(", ") || "No recognized skills found"}</p>
            <p>{extracted.education.join(" · ")}</p>
            <button
              type="button"
              onClick={() => {
                setProfile({
                  ...profile,
                  skills: [
                    ...new Set([...profile.skills, ...extracted.skills]),
                  ],
                  education: profile.education || extracted.education[0] || "",
                });
                setSkillsText(
                  [
                    ...new Set([
                      ...skillsText
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean),
                      ...extracted.skills,
                    ]),
                  ].join(", "),
                );
                setExtracted(undefined);
              }}
            >
              Add to editable profile
            </button>
          </div>
        )}
      </section>
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      </fieldset>
    </form>
  );
}
