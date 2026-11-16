import Link from "next/link";
import {
  ArrowRight,
  BookmarkCheck,
  Bot,
  Compass,
  PenLine,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";

const features = [
  {
    icon: Compass,
    title: "Describe the goal, not the steps",
    description: "Type what you want in plain English. The agent plans the search, picks the best-fit role, and decides who to contact.",
  },
  {
    icon: UserRound,
    title: "Reaches a real person",
    description: "Finds hiring managers and recruiters with Crustdata people data, or uses the application email on the posting. Every contact shows its source.",
  },
  {
    icon: PenLine,
    title: "Writes like you, not a template",
    description: "Each email is drafted from your skills, education and projects, and ties one concrete strength to the role.",
  },
  {
    icon: ShieldCheck,
    title: "You approve every send",
    description: "The AI has no way to send. It pauses with the exact draft; you edit, approve, or reject. Invented email addresses are blocked.",
  },
  {
    icon: Bot,
    title: "Watch it think",
    description: "A live trace shows every tool call, the agent's one-line reasoning, timing, and the credits it spent.",
  },
  {
    icon: BookmarkCheck,
    title: "Every lead, tracked",
    description: "Drafts, approvals and sends are saved as an outreach history alongside your applications.",
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
          <div className="landing-kicker"><span className="proof-dot" /> AI outreach agent with human approval</div>
          <h1 className="landing-title">From career goal to <span>personal outreach</span> in one minute.</h1>
          <p className="landing-lead">
            Tell Career Agent what you&apos;re looking for. It finds a matching opportunity, identifies the right person to contact, and drafts a personalized email. Nothing is sent until you approve it.
          </p>
          <div className="landing-cta">
            <Link className="button" href="/register">Try the agent <ArrowRight size={15} aria-hidden="true" /></Link>
            <Link className="button button-secondary" href="/login">I already have an account</Link>
          </div>
          <p className="landing-note">Hours of searching, LinkedIn-stalking and cold-email writing, done in a reviewed draft.</p>
        </div>

        <div className="visual-card" aria-label="Agent run preview">
          <div className="visual-top">
            <div className="visual-window-dots" aria-hidden="true"><span /><span /><span /></div>
            <span className="visual-label">&ldquo;Find me an ML internship&rdquo;</span>
            <span className="visual-indicator"><span className="proof-dot" /> Agent run</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><Compass size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">Discover</div><div className="visual-row-sub">Ranks saved roles against your profile</div></div>
            <span className="visual-chip">Free</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><UserRound size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">Find the right person</div><div className="visual-row-sub">Hiring manager + verified email, with source</div></div>
            <span className="visual-chip">Crustdata</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><PenLine size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">Personalize</div><div className="visual-row-sub">Email written from your skills and the role</div></div>
            <span className="visual-chip">LLM</span>
          </div>
          <div className="visual-row">
            <span className="visual-symbol"><ShieldCheck size={15} aria-hidden="true" /></span>
            <div><div className="visual-row-title">You approve</div><div className="visual-row-sub">Edit, approve or reject. Only you can send.</div></div>
            <span className="visual-chip">Human</span>
          </div>
        </div>
      </section>

      <section className="landing-section" id="features">
        <div className="landing-section-head">
          <div className="eyebrow">How it works</div>
          <h2>An agent that does the legwork, and leaves the decision to you.</h2>
          <p>Job seekers spend hours finding roles, guessing who to email, and rewriting the same cold message. Career Agent does all three. You stay in control of what gets sent.</p>
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
        <span>Career Agent · Find the role. Reach the person. You approve.</span>
        <span>Made for students finding their way forward.</span>
      </footer>
    </main>
  );
}
