"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Check, UserRound } from "lucide-react";
import api from "@/lib/api";
import type { User } from "@/types";

interface ProfileResponse extends User {
  bio?: string | null;
  skills?: string | null;
  target_roles?: string | null;
  location?: string | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  college?: string | null;
  graduation_year?: string | null;
}

interface ProfileForm {
  full_name: string;
  bio: string;
  skills: string;
  target_roles: string;
  location: string;
  github_url: string;
  linkedin_url: string;
  college: string;
  graduation_year: string;
}

const emptyForm: ProfileForm = {
  full_name: "",
  bio: "",
  skills: "",
  target_roles: "",
  location: "",
  github_url: "",
  linkedin_url: "",
  college: "",
  graduation_year: "",
};

const basicFields: { key: keyof Pick<ProfileForm, "full_name" | "college" | "graduation_year" | "location" | "github_url" | "linkedin_url">; label: string; placeholder: string; type?: string }[] = [
  { key: "full_name", label: "Full name", placeholder: "Your name" },
  { key: "college", label: "College or university", placeholder: "University name" },
  { key: "graduation_year", label: "Graduation year", placeholder: "2028" },
  { key: "location", label: "Location", placeholder: "City, country" },
  { key: "github_url", label: "GitHub profile", placeholder: "https://github.com/you", type: "url" },
  { key: "linkedin_url", label: "LinkedIn profile", placeholder: "https://linkedin.com/in/you", type: "url" },
];

export default function ProfilePage() {
  const [user, setUser] = useState<ProfileResponse | null>(null);
  const [form, setForm] = useState<ProfileForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<ProfileResponse>("/auth/me");
      const profile = response.data;
      setUser(profile);
      setForm({
        full_name: profile.full_name ?? "",
        bio: profile.bio ?? "",
        skills: profile.skills ?? "",
        target_roles: profile.target_roles ?? "",
        location: profile.location ?? "",
        github_url: profile.github_url ?? "",
        linkedin_url: profile.linkedin_url ?? "",
        college: profile.college ?? "",
        graduation_year: profile.graduation_year ?? "",
      });
    } catch {
      setError("Your profile couldn’t load. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadProfile(); }, [loadProfile]);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      await api.patch("/auth/me", form);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Your changes couldn’t be saved. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  const setField = (key: keyof ProfileForm, value: string) => setForm(current => ({ ...current, [key]: value }));
  const initials = (form.full_name || user?.email || "?").trim().slice(0, 1).toUpperCase();

  if (loading) {
    return <div className="page-wrap"><div className="page-head"><div><div className="eyebrow">Make it yours</div><h1 className="page-title">Your profile</h1></div></div><div className="skeleton profile-skeleton" /><div className="skeleton profile-skeleton" /></div>;
  }

  if (error && !user) {
    return <div className="page-wrap"><header className="page-head"><div><div className="eyebrow">Make it yours</div><h1 className="page-title">Your profile</h1></div></header><div className="panel empty-state"><div><span className="empty-icon"><UserRound size={18} aria-hidden="true" /></span><p className="empty-title">Your profile couldn’t load.</p><p className="empty-copy">{error}</p><button className="button button-secondary empty-action" onClick={() => void loadProfile()}>Try again</button></div></div></div>;
  }

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div><div className="eyebrow">Make it yours</div><h1 className="page-title">Your profile</h1><p className="page-description">Help Career Agent understand what you’re looking for.</p></div>
      </header>

      <section className="profile-summary panel">
        <span className="profile-avatar profile-avatar-large">{initials}</span>
        <div className="profile-summary-copy">
          <h2>{form.full_name || "Your name"}</h2>
          <p>{user?.email}</p>
          {(form.college || form.graduation_year) && <span>{[form.college, form.graduation_year].filter(Boolean).join(" · ")}</span>}
        </div>
        <div className="profile-summary-mark"><Check size={16} aria-hidden="true" /> Personal workspace</div>
      </section>

      <form className="profile-form" onSubmit={handleSave}>
        <section className="panel profile-section">
          <div className="profile-section-heading"><div><h2 className="section-title">About you</h2><p className="section-caption">A few details that make this workspace feel like yours.</p></div></div>
          <div className="form-grid">
            {basicFields.map(({ key, label, placeholder, type }) => (
              <label className="field-wrap" htmlFor={`profile-${key}`} key={key}>
                <span className="field-label">{label}</span>
                <input autoComplete={key === "full_name" ? "name" : undefined} className="field" id={`profile-${key}`} onChange={event => setField(key, event.target.value)} placeholder={placeholder} type={type ?? "text"} value={form[key]} />
              </label>
            ))}
          </div>
        </section>

        <section className="panel profile-section">
          <div className="profile-section-heading"><div><h2 className="section-title">Career direction</h2><p className="section-caption">These details help shape your recommendations and outreach drafts.</p></div></div>
          <div className="profile-direction-fields">
            <label className="field-wrap" htmlFor="profile-skills">
              <span className="field-label">Skills <span className="field-hint">Separate each skill with a comma</span></span>
              <input className="field" id="profile-skills" onChange={event => setField("skills", event.target.value)} placeholder="Python, React, product design" value={form.skills} />
              {!!form.skills && <span className="skill-preview">{form.skills.split(",").map(skill => skill.trim()).filter(Boolean).map(skill => <span className="tag tag-green" key={skill}>{skill}</span>)}</span>}
            </label>
            <label className="field-wrap" htmlFor="profile-target-roles">
              <span className="field-label">Roles you’re interested in <span className="field-hint">Separate roles with a comma</span></span>
              <input className="field" id="profile-target-roles" onChange={event => setField("target_roles", event.target.value)} placeholder="Software intern, product design, open source" value={form.target_roles} />
            </label>
            <label className="field-wrap" htmlFor="profile-bio">
              <span className="field-label">A little about you</span>
              <textarea className="field profile-bio" id="profile-bio" onChange={event => setField("bio", event.target.value)} placeholder="What are you learning, building, or hoping to do next?" rows={4} value={form.bio} />
            </label>
          </div>
        </section>

        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="profile-save-row">
          <button className="button" disabled={saving} type="submit">{saving ? "Saving changes…" : saved ? <><Check size={15} /> Saved</> : "Save changes"}</button>
          {saved && <span className="save-note" role="status">Your profile is up to date.</span>}
          {(form.github_url || form.linkedin_url) && <span className="profile-links-note"><ArrowUpRight size={13} /> Your profile links are saved privately.</span>}
        </div>
      </form>
    </div>
  );
}
