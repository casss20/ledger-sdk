import { useState } from 'react'
import {
  Shield, Eye, Zap, FileText, Users, Code2,
  Copy, Check, ChevronRight, AlertTriangle,
  BookOpen, LayoutDashboard, ArrowRight,
  Lock, GitBranch, Globe, Menu, X
} from 'lucide-react'

function CopyButton({ text, light = false }: { text: string; light?: boolean }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={copy}
      aria-label="Copy to clipboard"
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all duration-200 cursor-pointer ${
        light
          ? 'bg-white hover:bg-orange-50 border-slate-200 hover:border-orange-300'
          : 'bg-slate-800 hover:bg-slate-700 border-slate-700 hover:border-orange-500/40'
      }`}
    >
      {copied
        ? <Check size={13} className="text-emerald-500" />
        : <Copy size={13} className={light ? 'text-slate-400' : 'text-slate-400'} />}
      <span className={`mono text-xs ${light ? 'text-slate-500' : 'text-slate-400'}`}>
        {copied ? 'Copied!' : 'Copy'}
      </span>
    </button>
  )
}

function CodeBlock({ lines }: { lines: { type: string; text: string }[][] }) {
  return (
    <pre className="mono text-sm leading-7 overflow-x-auto">
      {lines.map((line, i) => (
        <div key={i}>
          {line.length === 0
            ? <span>&nbsp;</span>
            : line.map((token, j) => (
                <span key={j} className={`token-${token.type}`}>{token.text}</span>
              ))}
        </div>
      ))}
    </pre>
  )
}

const installCommand = 'pip install citadel-governance'

const codeLines = [
  [{ type: 'keyword', text: 'import' }, { type: 'plain', text: ' citadel' }],
  [],
  [{ type: 'comment', text: '# 1. Point at your Citadel instance' }],
  [{ type: 'function', text: 'citadel.configure' }, { type: 'plain', text: '(' }],
  [{ type: 'plain', text: '    base_url=' }, { type: 'string', text: '"https://api.citadelsdk.com"' }, { type: 'plain', text: ',' }],
  [{ type: 'plain', text: '    api_key=' }, { type: 'string', text: '"your-api-key"' }, { type: 'plain', text: ',' }],
  [{ type: 'plain', text: '    actor_id=' }, { type: 'string', text: '"my-agent"' }, { type: 'plain', text: ',' }],
  [{ type: 'plain', text: ')' }],
  [],
  [{ type: 'comment', text: '# 2. Every agent action goes through governance' }],
  [{ type: 'plain', text: 'result = ' }, { type: 'keyword', text: 'await' }, { type: 'plain', text: ' ' }, { type: 'function', text: 'citadel.execute' }, { type: 'plain', text: '(' }],
  [{ type: 'plain', text: '    action=' }, { type: 'string', text: '"stripe.refund"' }, { type: 'plain', text: ',' }],
  [{ type: 'plain', text: '    resource=' }, { type: 'string', text: '"charge:ch_123"' }, { type: 'plain', text: ',' }],
  [{ type: 'plain', text: '    payload={ ' }, { type: 'string', text: '"amount"' }, { type: 'plain', text: ': ' }, { type: 'number', text: '5000' }, { type: 'plain', text: ' },' }],
  [{ type: 'plain', text: ')' }],
  [],
  [{ type: 'keyword', text: 'if' }, { type: 'plain', text: ' result.status == ' }, { type: 'string', text: '"executed"' }, { type: 'plain', text: ':' }],
  [{ type: 'plain', text: '    ' }, { type: 'function', text: 'print' }, { type: 'plain', text: '(' }, { type: 'string', text: '"Permitted and logged"' }, { type: 'plain', text: ')' }],
  [{ type: 'keyword', text: 'elif' }, { type: 'plain', text: ' result.status == ' }, { type: 'string', text: '"pending_approval"' }, { type: 'plain', text: ':' }],
  [{ type: 'plain', text: '    ' }, { type: 'function', text: 'print' }, { type: 'plain', text: '(' }, { type: 'string', text: '"Queued for human review"' }, { type: 'plain', text: ')' }],
  [{ type: 'keyword', text: 'else' }, { type: 'plain', text: ':' }],
  [{ type: 'plain', text: '    ' }, { type: 'function', text: 'print' }, { type: 'plain', text: '(f' }, { type: 'string', text: '"Blocked: {result.reason}"' }, { type: 'plain', text: ')' }],
]

const problems = [
  {
    icon: AlertTriangle,
    title: 'Agents act without oversight',
    body: 'Autonomous agents make high-stakes decisions — sending emails, executing payments, modifying infrastructure — with zero human visibility.',
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-100',
  },
  {
    icon: Eye,
    title: 'No audit trail',
    body: 'When something goes wrong, you have no record of what your agent did, why it was allowed, or who approved it.',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-100',
  },
  {
    icon: Zap,
    title: 'No kill switch',
    body: "When an agent goes rogue, you can't stop it. One bad prompt can trigger a cascade you have no way to interrupt.",
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-100',
  },
]

const features = [
  { icon: Shield,    title: 'Policy Engine',       body: 'Precedence-based rules evaluate every action: ALLOW, BLOCK, or route to approval. Define policies in code or via the dashboard.',       color: 'text-orange-600', bg: 'bg-orange-50' },
  { icon: Users,     title: 'Human Approvals',     body: 'High-risk actions pause and wait for a human decision. Reviewers approve or reject from the dashboard in real time.',                   color: 'text-violet-600', bg: 'bg-violet-50' },
  { icon: Lock,      title: 'Kill Switch',         body: 'One click blocks all agent actions globally, per tenant, or per agent. Instant. No redeploy needed.',                                   color: 'text-red-600',    bg: 'bg-red-50'    },
  { icon: FileText,  title: 'Tamper-Proof Audit',  body: 'Every decision is cryptographically hashed and chained in PostgreSQL. The audit trail cannot be modified or deleted.',                  color: 'text-emerald-600',bg: 'bg-emerald-50'},
  { icon: GitBranch, title: 'Multi-Tenant',        body: 'Full tenant isolation via PostgreSQL Row-Level Security. Each customer sees only their own agents, policies, and audit logs.',           color: 'text-blue-600',   bg: 'bg-blue-50'   },
  { icon: Globe,     title: 'Open SDK',            body: 'One pip install. Works with any agent framework — LangChain, AutoGen, custom. MIT licensed.',                                           color: 'text-teal-600',   bg: 'bg-teal-50'   },
]

const steps = [
  { step: '01', title: 'Install', body: "One pip install. No servers to run \u2014 point at our hosted API and you're ready in seconds." },
  { step: '02', title: 'Configure', body: 'Set your API URL, key, and actor ID. Works with any Python async framework.' },
  { step: '03', title: 'Govern', body: 'Every action is evaluated by policy, logged to the audit chain, and optionally routed for human approval.' },
]

export default function App() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="min-h-dvh bg-white text-slate-900">

      {/* ── Nav ── */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center shadow-md shadow-orange-200">
              <Shield size={16} className="text-white" />
            </div>
            <span className="text-base font-black tracking-tighter text-slate-900">CITADEL</span>
          </div>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            {[{ label: 'Docs', href: '/docs' }, { label: 'Features', href: '#features' }, { label: 'How it works', href: '#how-it-works' }].map(({ label, href }) => (
              <a key={label} href={href} className="nav-link text-sm text-slate-500 hover:text-slate-900 font-medium transition-colors duration-200">
                {label}
              </a>
            ))}
          </div>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-3">
            <a href="/docs" className="text-sm text-slate-500 hover:text-slate-900 font-medium transition-colors duration-200">
              Documentation
            </a>
            <a href="https://dashboard.citadelsdk.com"
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-500 text-white text-sm font-semibold transition-all duration-200 shadow-sm shadow-orange-200">
              <LayoutDashboard size={14} />
              Dashboard
            </a>
          </div>

          {/* Mobile menu toggle */}
          <button
            className="md:hidden p-2 rounded-lg hover:bg-slate-100 transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={20} className="text-slate-600" /> : <Menu size={20} className="text-slate-600" />}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden border-t border-slate-100 bg-white px-6 py-4 space-y-3">
            {[{ label: 'Docs', href: '/docs' }, { label: 'Features', href: '#features' }, { label: 'How it works', href: '#how-it-works' }].map(({ label, href }) => (
              <a key={label} href={href} onClick={() => setMobileOpen(false)}
                className="block text-sm text-slate-600 hover:text-slate-900 font-medium py-2">
                {label}
              </a>
            ))}
            <a href="https://dashboard.citadelsdk.com"
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-orange-600 text-white text-sm font-semibold mt-2">
              <LayoutDashboard size={14} />
              Open Dashboard
            </a>
          </div>
        )}
      </nav>

      {/* ── Hero ── */}
      <section className="hero-grid relative pt-32 pb-24 px-6 overflow-hidden">
        <div className="hero-glow absolute inset-0 pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center animate-fade-up">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-orange-50 border border-orange-200 mb-8">
            <div className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
            <span className="text-xs font-semibold text-orange-700 tracking-wide">AI Governance Infrastructure</span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tighter text-slate-900 leading-[1.05] mb-6">
            The Constitution<br />
            <span className="gradient-text">for your AI agents</span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-slate-500 max-w-2xl mx-auto leading-relaxed mb-12">
            One SDK call to control, audit, and approve every action your agents take.
            Policy enforcement, human approvals, kill switches, and tamper-proof audit — out of the box.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <div className="flex items-center gap-3 px-5 py-3.5 rounded-xl bg-slate-900 border border-slate-800 w-full sm:w-auto">
              <span className="text-slate-500 mono text-sm select-none">$</span>
              <span className="mono text-sm text-white flex-1">{installCommand}</span>
              <CopyButton text={installCommand} />
            </div>
            <a href="https://dashboard.citadelsdk.com"
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-semibold transition-all duration-200 shadow-lg shadow-orange-200 hover:-translate-y-0.5 w-full sm:w-auto justify-center">
              View Dashboard
              <ArrowRight size={16} />
            </a>
          </div>

          {/* Feature strip */}
          <div className="mt-16 flex flex-wrap items-center justify-center gap-3">
            {['Policy Engine', 'Human-in-the-Loop', 'Kill Switch', 'Tamper-Proof Audit', 'Multi-Tenant', 'Open SDK'].map((label) => (
              <span key={label} className="px-3 py-1 rounded-full bg-slate-100 text-slate-500 text-xs font-medium">
                {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Social proof bar ── */}
      <div className="border-y border-slate-100 bg-slate-50 py-5 px-6">
        <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-center gap-8 text-slate-400 text-sm">
          <span className="flex items-center gap-2"><Shield size={14} className="text-orange-400" /> MIT Licensed</span>
          <span className="flex items-center gap-2"><GitBranch size={14} className="text-orange-400" /> Open Source</span>
          <span className="flex items-center gap-2"><FileText size={14} className="text-orange-400" /> Cryptographic Audit</span>
          <span className="flex items-center gap-2"><Users size={14} className="text-orange-400" /> Human-in-the-Loop</span>
          <span className="flex items-center gap-2"><Zap size={14} className="text-orange-400" /> One-Click Kill Switch</span>
        </div>
      </div>

      {/* ── Problem ── */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="inline-block px-3 py-1 rounded-full bg-red-50 text-red-600 text-xs font-bold uppercase tracking-widest mb-4 border border-red-100">
              The Problem
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter text-slate-900">
              Agents are powerful.<br />
              <span className="text-slate-400">Uncontrolled agents are dangerous.</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {problems.map(({ icon: Icon, title, body, color, bg, border }) => (
              <div key={title} className={`card-lift p-7 rounded-2xl bg-white border ${border} shadow-sm`}>
                <div className={`w-11 h-11 rounded-xl ${bg} flex items-center justify-center mb-5`}>
                  <Icon size={22} className={color} />
                </div>
                <h3 className="font-bold text-slate-900 text-lg mb-2">{title}</h3>
                <p className="text-slate-500 leading-relaxed text-sm">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="py-24 px-6 bg-slate-50 section-divider">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="inline-block px-3 py-1 rounded-full bg-orange-50 text-orange-600 text-xs font-bold uppercase tracking-widest mb-4 border border-orange-100">
              How it works
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter text-slate-900">
              Three steps to governed agents
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
            {/* Steps */}
            <div className="space-y-8 pt-2">
              {steps.map(({ step, title, body }, i) => (
                <div key={step} className="flex gap-5">
                  <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-orange-600 flex items-center justify-center shadow-md shadow-orange-200">
                    <span className="mono text-xs font-bold text-white">{step}</span>
                  </div>
                  <div className="pt-1">
                    <h3 className="font-bold text-slate-900 text-lg mb-1">{title}</h3>
                    <p className="text-slate-500 text-sm leading-relaxed">{body}</p>
                    {i < steps.length - 1 && (
                      <div className="w-px h-6 bg-slate-200 ml-0.5 mt-6" />
                    )}
                  </div>
                </div>
              ))}

              <a href="/docs"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-200 hover:border-orange-300 bg-white hover:bg-orange-50 text-sm text-slate-700 hover:text-orange-700 font-medium transition-all duration-200 group">
                <BookOpen size={15} />
                Read the full docs
                <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform duration-200" />
              </a>
            </div>

            {/* Code block — dark on purpose (standard for technical products) */}
            <div className="rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden shadow-xl shadow-slate-200">
              <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-900">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/60" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                  <div className="w-3 h-3 rounded-full bg-green-500/60" />
                </div>
                <span className="mono text-xs text-slate-400">agent.py</span>
                <CopyButton text={`import citadel\n\ncitadel.configure(\n    base_url="https://api.citadelsdk.com",\n    api_key="your-api-key",\n    actor_id="my-agent",\n)\n\nresult = await citadel.execute(\n    action="stripe.refund",\n    resource="charge:ch_123",\n    payload={"amount": 5000},\n)`} />
              </div>
              <div className="p-6">
                <CodeBlock lines={codeLines} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="inline-block px-3 py-1 rounded-full bg-violet-50 text-violet-600 text-xs font-bold uppercase tracking-widest mb-4 border border-violet-100">
              Features
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter text-slate-900">
              Everything you need.<br />
              <span className="text-slate-400">Nothing you don't.</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, body, color, bg }) => (
              <div key={title} className="card-lift p-7 rounded-2xl bg-white border border-slate-100 shadow-sm">
                <div className={`w-11 h-11 rounded-xl ${bg} flex items-center justify-center mb-5`}>
                  <Icon size={22} className={color} />
                </div>
                <h3 className="font-bold text-slate-900 text-base mb-2">{title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Decorator section ── */}
      <section className="py-24 px-6 bg-slate-50 section-divider">
        <div className="max-w-6xl mx-auto">
          <div className="rounded-3xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-2">
              {/* Left */}
              <div className="p-10 lg:p-12 flex flex-col justify-center">
                <div className="inline-flex items-center gap-2 mb-5">
                  <div className="w-8 h-8 rounded-lg bg-orange-50 border border-orange-100 flex items-center justify-center">
                    <Code2 size={16} className="text-orange-600" />
                  </div>
                  <span className="text-xs font-bold text-orange-600 uppercase tracking-widest">Decorator API</span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tighter text-slate-900 mb-4">
                  Wrap any function<br />in one line
                </h2>
                <p className="text-slate-500 leading-relaxed mb-8 text-sm">
                  Use <code className="mono text-orange-600 text-sm bg-orange-50 px-1.5 py-0.5 rounded">@citadel.guard</code> to protect
                  any async function. If governance blocks it, an exception is raised.
                  If it needs approval, execution pauses automatically.
                </p>
                <a href="/docs"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-sm font-semibold transition-all duration-200 shadow-sm shadow-orange-200 self-start">
                  View decorator docs
                  <ArrowRight size={14} />
                </a>
              </div>

              {/* Right — code */}
              <div className="bg-slate-950 p-8 flex items-center">
                <div className="w-full">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="mono text-xs text-slate-500">decorator_example.py</span>
                  </div>
                  <CodeBlock lines={[
                    [{ type: 'keyword', text: 'import' }, { type: 'plain', text: ' citadel' }],
                    [],
                    [{ type: 'plain', text: '@' }, { type: 'function', text: 'citadel.guard' }, { type: 'plain', text: '(' }],
                    [{ type: 'plain', text: '    action=' }, { type: 'string', text: '"github.repo_delete"' }, { type: 'plain', text: ',' }],
                    [{ type: 'plain', text: '    resource=' }, { type: 'string', text: '"repo:{name}"' }],
                    [{ type: 'plain', text: ')' }],
                    [{ type: 'keyword', text: 'async' }, { type: 'plain', text: ' ' }, { type: 'keyword', text: 'def' }, { type: 'plain', text: ' ' }, { type: 'function', text: 'delete_repo' }, { type: 'plain', text: '(name: ' }, { type: 'keyword', text: 'str' }, { type: 'plain', text: '):' }],
                    [{ type: 'comment', text: '    # Only runs if governance allows it' }],
                    [{ type: 'plain', text: '    ' }, { type: 'keyword', text: 'await' }, { type: 'plain', text: ' github.repos.delete(name)' }],
                  ]} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-600 items-center justify-center mx-auto mb-8 shadow-xl shadow-orange-200">
            <Shield size={30} className="text-white" />
          </div>
          <h2 className="text-4xl sm:text-5xl font-black tracking-tighter text-slate-900 mb-4">
            Start governing your<br />agents in 5 minutes
          </h2>
          <p className="text-slate-500 text-lg mb-10 leading-relaxed">
            One install. No infrastructure to run. Connect to our hosted API
            and see every agent action in the dashboard instantly.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            <div className="flex items-center gap-3 px-5 py-3.5 rounded-xl bg-slate-900 border border-slate-800 w-full sm:w-auto">
              <span className="text-slate-500 mono text-sm select-none">$</span>
              <span className="mono text-sm text-white">{installCommand}</span>
              <CopyButton text={installCommand} />
            </div>
            <a href="https://dashboard.citadelsdk.com"
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-semibold transition-all duration-200 shadow-lg shadow-orange-200 hover:-translate-y-0.5 w-full sm:w-auto justify-center">
              Open Dashboard
              <ArrowRight size={16} />
            </a>
          </div>

          <p className="text-slate-400 text-sm">
            MIT licensed SDK · Hosted API · No credit card required
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-100 bg-slate-50 py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-orange-600 flex items-center justify-center">
              <Shield size={12} className="text-white" />
            </div>
            <span className="text-sm font-black tracking-tighter text-slate-700">CITADEL</span>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-6">
            {[
              { label: 'Docs', href: '/docs' },
              { label: 'Dashboard', href: 'https://dashboard.citadelsdk.com' },
              { label: 'GitHub', href: 'https://github.com/casss20/ledger-sdk' },
              { label: 'PyPI', href: 'https://pypi.org/project/citadel-governance/' },
            ].map(({ label, href }) => (
              <a key={label} href={href}
                className="text-sm text-slate-400 hover:text-slate-700 font-medium transition-colors duration-200">
                {label}
              </a>
            ))}
          </div>
          <p className="text-xs text-slate-400">© 2026 Citadel. MIT License.</p>
        </div>
      </footer>
    </div>
  )
}
