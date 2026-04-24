import { useState } from 'react'
import {
  Shield, Eye, Zap, FileText, Users, Code2,
  Copy, Check, ChevronRight, AlertTriangle,
  BookOpen, LayoutDashboard, ArrowRight,
  Lock, GitBranch, Globe
} from 'lucide-react'

function CopyButton({ text }: { text: string }) {
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
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-orange-500/40 transition-all duration-200 cursor-pointer"
    >
      {copied
        ? <Check size={13} className="text-emerald-400" />
        : <Copy size={13} className="text-slate-400" />}
      <span className="mono text-xs text-slate-400">{copied ? 'Copied!' : 'Copy'}</span>
    </button>
  )
}

function CodeBlock({ lines }: { lines: { type: string; text: string }[][] }) {
  return (
    <pre className="mono text-sm leading-7 overflow-x-auto">
      {lines.map((line, i) => (
        <div key={i}>
          {line.map((token, j) => (
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
  [{ type: 'comment', text: '# 3. React to the governance decision' }],
  [{ type: 'keyword', text: 'if' }, { type: 'plain', text: ' result.status == ' }, { type: 'string', text: '"executed"' }, { type: 'plain', text: ':' }],
  [{ type: 'plain', text: '    ' }, { type: 'function', text: 'print' }, { type: 'plain', text: '(' }, { type: 'string', text: '"✓ Permitted and logged"' }, { type: 'plain', text: ')' }],
  [{ type: 'keyword', text: 'elif' }, { type: 'plain', text: ' result.status == ' }, { type: 'string', text: '"pending_approval"' }, { type: 'plain', text: ':' }],
  [{ type: 'plain', text: '    ' }, { type: 'function', text: 'print' }, { type: 'plain', text: '(' }, { type: 'string', text: '"⏳ Queued for human review"' }, { type: 'plain', text: ')' }],
  [{ type: 'keyword', text: 'else' }, { type: 'plain', text: ':' }],
  [{ type: 'plain', text: '    ' }, { type: 'function', text: 'print' }, { type: 'plain', text: '(f' }, { type: 'string', text: '"✗ Blocked: {result.reason}"' }, { type: 'plain', text: ')' }],
]

const problems = [
  {
    icon: AlertTriangle,
    title: 'Agents act without oversight',
    body: 'Autonomous agents make high-stakes decisions — sending emails, executing payments, modifying infrastructure — with zero human visibility.',
  },
  {
    icon: Eye,
    title: 'No audit trail',
    body: 'When something goes wrong, you have no record of what your agent did, why it was allowed, or who approved it.',
  },
  {
    icon: Zap,
    title: 'No kill switch',
    body: "When an agent goes rogue, you can't stop it. One bad prompt can trigger a cascade you have no way to interrupt.",
  },
]

const features = [
  {
    icon: Shield,
    title: 'Policy Engine',
    body: 'Precedence-based rules evaluate every action: ALLOW, BLOCK, or route to approval. Define policies in code or via the dashboard.',
  },
  {
    icon: Users,
    title: 'Human Approvals',
    body: 'High-risk actions pause and wait for a human decision. Reviewers approve or reject from the dashboard in real time.',
  },
  {
    icon: Lock,
    title: 'Kill Switch',
    body: 'One click blocks all agent actions globally, per tenant, or per agent. Instant. No redeploy needed.',
  },
  {
    icon: FileText,
    title: 'Tamper-Proof Audit',
    body: 'Every decision is cryptographically hashed and chained in PostgreSQL. The audit trail cannot be modified or deleted.',
  },
  {
    icon: GitBranch,
    title: 'Multi-Tenant',
    body: 'Full tenant isolation via PostgreSQL Row-Level Security. Each customer sees only their own agents, policies, and audit logs.',
  },
  {
    icon: Globe,
    title: 'Open SDK',
    body: 'One pip install. Works with any agent framework — LangChain, AutoGen, custom. MIT licensed.',
  },
]

const steps = [
  { step: '01', title: 'Install', body: 'One pip install. No servers to run — point at our hosted API.' },
  { step: '02', title: 'Configure', body: 'Set your API URL, key, and actor ID. Works with any Python async framework.' },
  { step: '03', title: 'Govern', body: 'Every action is evaluated, logged, and optionally routed to a human approver.' },
]

export default function App() {
  return (
    <div className="min-h-dvh bg-[#020617] text-slate-100">

      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-slate-800/60 backdrop-blur-md bg-[#020617]/80">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center shadow-lg shadow-orange-900/30">
              <Shield size={16} className="text-white" />
            </div>
            <span className="text-base font-black tracking-tighter text-white">CITADEL</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            {['Docs', 'Features', 'How it works'].map(label => (
              <a key={label} href={label === 'Docs' ? '/docs' : `#${label.toLowerCase().replace(/ /g, '-')}`}
                className="nav-link text-sm text-slate-400 hover:text-white transition-colors duration-200">
                {label}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <a href="https://dashboard.citadelsdk.com"
              className="hidden sm:flex items-center gap-1.5 px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-500 text-white text-sm font-semibold transition-all duration-200 shadow-lg shadow-orange-900/30">
              <LayoutDashboard size={14} />
              Dashboard
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-grid relative pt-32 pb-24 px-6 overflow-hidden">
        <div className="hero-fade absolute inset-0 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#020617] pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-orange-500/30 bg-orange-500/10 mb-8">
            <div className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
            <span className="text-xs font-semibold text-orange-400 tracking-wide uppercase">AI Governance Infrastructure</span>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tighter text-white leading-[1.05] mb-6">
            The Constitution<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-orange-600">
              for your AI agents
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-12">
            One SDK call to control, audit, and approve every action your agents take.
            Policy enforcement, human approvals, kill switches, and tamper-proof audit —
            out of the box.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {/* Install command */}
            <div className="flex items-center gap-3 px-5 py-3 rounded-xl bg-slate-900 border border-slate-700 w-full sm:w-auto">
              <span className="text-slate-500 mono text-sm select-none">$</span>
              <span className="mono text-sm text-slate-100 flex-1">{installCommand}</span>
              <CopyButton text={installCommand} />
            </div>

            <a href="https://dashboard.citadelsdk.com"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-semibold transition-all duration-200 shadow-lg shadow-orange-900/30 hover:shadow-orange-900/50 hover:-translate-y-0.5 w-full sm:w-auto justify-center">
              View Dashboard
              <ArrowRight size={16} />
            </a>
          </div>

          {/* Social proof strip */}
          <div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-slate-600 text-xs font-medium uppercase tracking-widest">
            <span>Policy Engine</span>
            <span className="text-slate-800">·</span>
            <span>Human-in-the-Loop</span>
            <span className="text-slate-800">·</span>
            <span>Kill Switch</span>
            <span className="text-slate-800">·</span>
            <span>Tamper-Proof Audit</span>
            <span className="text-slate-800">·</span>
            <span>Multi-Tenant</span>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section id="features" className="py-24 px-6 border-t border-slate-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-orange-500 text-xs font-bold uppercase tracking-widest mb-3">The Problem</p>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter text-white">
              Agents are powerful.<br />Uncontrolled agents are dangerous.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {problems.map(({ icon: Icon, title, body }) => (
              <div key={title}
                className="card-glow p-6 rounded-2xl bg-slate-900/60 border border-slate-800 transition-all duration-300">
                <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
                  <Icon size={20} className="text-red-400" />
                </div>
                <h3 className="font-bold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6 border-t border-slate-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-orange-500 text-xs font-bold uppercase tracking-widest mb-3">How it works</p>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter text-white">
              Three steps to governed agents
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
            {/* Steps */}
            <div className="space-y-8">
              {steps.map(({ step, title, body }) => (
                <div key={step} className="flex gap-5">
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
                    <span className="mono text-xs font-bold text-orange-500">{step}</span>
                  </div>
                  <div>
                    <h3 className="font-bold text-white mb-1">{title}</h3>
                    <p className="text-sm text-slate-400 leading-relaxed">{body}</p>
                  </div>
                </div>
              ))}

              <a href="/docs"
                className="inline-flex items-center gap-2 text-sm text-orange-400 hover:text-orange-300 font-medium transition-colors duration-200 group">
                <BookOpen size={15} />
                Read the full docs
                <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform duration-200" />
              </a>
            </div>

            {/* Code block */}
            <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-950/50">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-slate-700" />
                  <div className="w-3 h-3 rounded-full bg-slate-700" />
                  <div className="w-3 h-3 rounded-full bg-slate-700" />
                </div>
                <span className="mono text-xs text-slate-500">agent.py</span>
                <CopyButton text={`import citadel\n\ncitadel.configure(\n    base_url="https://api.citadelsdk.com",\n    api_key="your-api-key",\n    actor_id="my-agent",\n)\n\nresult = await citadel.execute(\n    action="stripe.refund",\n    resource="charge:ch_123",\n    payload={"amount": 5000},\n)`} />
              </div>
              <div className="p-5">
                <CodeBlock lines={codeLines} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6 border-t border-slate-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-orange-500 text-xs font-bold uppercase tracking-widest mb-3">Features</p>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter text-white">
              Everything you need.<br />Nothing you don't.
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, body }) => (
              <div key={title}
                className="card-glow group p-6 rounded-2xl bg-slate-900/40 border border-slate-800 hover:border-slate-700 transition-all duration-300">
                <div className="w-10 h-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mb-4 group-hover:bg-orange-500/15 transition-colors duration-300">
                  <Icon size={20} className="text-orange-500" />
                </div>
                <h3 className="font-bold text-white mb-2">{title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Decorator / use as decorator section */}
      <section className="py-24 px-6 border-t border-slate-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-900/50 border border-slate-800 p-8 md:p-12">
            <div className="flex flex-col md:flex-row items-start gap-10">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-4">
                  <Code2 size={18} className="text-orange-500" />
                  <span className="text-xs font-bold text-orange-500 uppercase tracking-widest">Decorator API</span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tighter text-white mb-4">
                  Wrap any function<br />in one line
                </h2>
                <p className="text-slate-400 leading-relaxed mb-6">
                  Use <code className="mono text-orange-400 text-sm">@citadel.guard</code> to protect any async function.
                  If governance blocks it, an exception is raised. If it needs approval, execution pauses automatically.
                </p>
                <a href="/docs"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-700 hover:border-orange-500/40 text-sm text-slate-300 hover:text-white font-medium transition-all duration-200">
                  View decorator docs
                  <ArrowRight size={14} />
                </a>
              </div>

              <div className="flex-1 w-full rounded-xl bg-slate-950 border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
                  <span className="mono text-xs text-slate-500">decorator_example.py</span>
                </div>
                <div className="p-5">
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

      {/* CTA */}
      <section className="py-24 px-6 border-t border-slate-800/50">
        <div className="max-w-3xl mx-auto text-center">
          <div className="w-14 h-14 rounded-2xl bg-orange-600 flex items-center justify-center mx-auto mb-8 shadow-xl shadow-orange-900/40">
            <Shield size={28} className="text-white" />
          </div>
          <h2 className="text-4xl sm:text-5xl font-black tracking-tighter text-white mb-4">
            Start governing your<br />agents in 5 minutes
          </h2>
          <p className="text-slate-400 text-lg mb-10">
            One install. No infrastructure to run. Connect to our hosted API and see every agent action in the dashboard instantly.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            <div className="flex items-center gap-3 px-5 py-3.5 rounded-xl bg-slate-900 border border-slate-700 w-full sm:w-auto">
              <span className="text-slate-500 mono text-sm select-none">$</span>
              <span className="mono text-sm text-slate-100">{installCommand}</span>
              <CopyButton text={installCommand} />
            </div>
            <a href="https://dashboard.citadelsdk.com"
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-semibold transition-all duration-200 shadow-lg shadow-orange-900/30 hover:-translate-y-0.5 w-full sm:w-auto justify-center">
              Open Dashboard
              <ArrowRight size={16} />
            </a>
          </div>

          <p className="text-slate-600 text-sm">
            MIT licensed SDK · Hosted API · No credit card required
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-orange-600 flex items-center justify-center">
              <Shield size={12} className="text-white" />
            </div>
            <span className="text-sm font-black tracking-tighter text-slate-400">CITADEL</span>
          </div>
          <div className="flex items-center gap-8">
            {[
              { label: 'Docs', href: '/docs' },
              { label: 'Dashboard', href: 'https://dashboard.citadelsdk.com' },
              { label: 'GitHub', href: 'https://github.com/casss20/ledger-sdk' },
              { label: 'PyPI', href: 'https://pypi.org/project/citadel-governance/' },
            ].map(({ label, href }) => (
              <a key={label} href={href}
                className="text-sm text-slate-500 hover:text-slate-300 transition-colors duration-200">
                {label}
              </a>
            ))}
          </div>
          <p className="text-xs text-slate-700">© 2026 Citadel. MIT License.</p>
        </div>
      </footer>
    </div>
  )
}
