import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookmarkCheck,
  BriefcaseBusiness,
  Check,
  Compass,
  Sparkles,
} from "lucide-react";

const features = [
  {
    icon: Compass,
    title: "Find your next move",
    description: "Explore opportunities from student programs, startups, and remote-first teams in one place.",
  },
  {
    icon: BookmarkCheck,
    title: "Keep every application close",
    description: "Save roles, track your progress, and keep the details you need for every follow-up.",
  },
  {
    icon: Sparkles,
    title: "Make discovery more personal",
    description: "Get keyword-matched recommendations informed by your interests and career profile.",
  },
  {
    icon: BarChart3,
    title: "See your momentum",
    description: "Understand your application activity and where your search is gaining traction.",
  },
  {
    icon: BriefcaseBusiness,
    title: "Bring your tracker with you",
    description: "Import an existing Google Sheet and continue your search without starting over.",
  },
  {
    icon: Check,
    title: "Built for the whole journey",
    description: "Move from finding an opening to tracking interviews and celebrating an offer.",
  },
];

export default function HomePage() {
  return (
    <main className="landing">
      <nav className="landing-nav" aria-label="Main navigation">
        <Link className="auth-brand" href="/" aria-label="Career Agent home">
          <span className="brand-icon"><Sparkles size={17} aria-hidden="true" /></span>
          <span>Career Agent</span>
        </Link>
        <div className="landing-nav-actions">
          <a className="landing-nav-link" href="#features">Why Career Agent</a>
          <Link className="landing-nav-link" href="/login">Sign in</Link>
          <Link className="button" href="/register">Get started <ArrowRight size={14} aria-hidden="true" /></Link>
        </div>
      </nav>

      <section className="landing-hero">
        <div>
          <div className="landing-kicker"><span className="proof-dot" /> Your next chapter starts here</div>
          <h1 className="landing-title">A clearer path to <span>what&apos;s next.</span></h1>
          <p className="landing-lead">
            Find opportunities worth pursuing, keep your applications moving, and make your career search feel a little less like guesswork.
          </p>
          <div className="landing-cta">
            <Link className="button" href="/register">Build your career workspace <ArrowRight size={15} aria-hidden="true" /></Link>
            <Link className="button button-secondary" href="/login">I already have an account</Link>
          </div>
          <p className="landing-note">Free for students. Your search, all in one place.</p>
        </div>

        <div className="visual-card" aria-label="Career Agent feature preview">
          <div className="visual-top">
            <div className="visual-window-dots" aria-hidden="true"><span /><span /><span /></div>
            <span className="visual-label">Your career workspace</span>
            <span className="visual-indicator"><span className="proof-dot" /> Ready</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><Compass size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">Discover opportunities</div><div className="visual-row-sub">Roles and programs in one place</div></div>
            <span className="visual-chip">Explore</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><BookmarkCheck size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">Track your applications</div><div className="visual-row-sub">Keep every next step in view</div></div>
            <span className="visual-chip">Organize</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><Sparkles size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">Find a better fit</div><div className="visual-row-sub">Recommendations shaped by your profile</div></div>
            <span className="visual-chip">Match</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><BarChart3 size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">See your progress</div><div className="visual-row-sub">A little more clarity, every week</div></div>
            <span className="visual-chip">Grow</span>
          </div>
        </div>
      </section>

      <section className="landing-section" id="features">
        <div className="landing-section-head">
          <div className="eyebrow">One workspace, more possibilities</div>
          <h2>Make room for the work that moves you forward.</h2>
          <p>Less tab-hopping. More clarity on the opportunities, people, and progress that matter to your next step.</p>
        </div>
        <div className="feature-grid">
          {features.map(({ icon: Icon, title, description }) => (
            <article className="feature-card" key={title}>
              <span className="feature-icon"><Icon size={17} aria-hidden="true" /></span>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <span>Career Agent · Your career, in motion.</span>
        <span>Made for students finding their way forward.</span>
      </footer>
    </main>
  );
}
