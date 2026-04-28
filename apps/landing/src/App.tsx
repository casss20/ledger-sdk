import { useState, useEffect } from 'react'
import {
  Shield, EyeOff, ClipboardList, Settings,
  ArrowDownLeft, Scale, FileSearch,
  Zap, Activity, Clock,
  CheckCircle2, AlertTriangle, XCircle,
  Users, GitBranch, Globe, FileText, Lock,
  LayoutDashboard, Menu, X, DollarSign,
} from 'lucide-react'

/* ─── Navigation ─── */
function Navigation() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const links = [
    { label: 'Features', href: '#features' },
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Docs', href: 'https://citadelsdk.com/docs' },
  ]

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'glass-strong shadow-sm border-b border-white/60' : 'bg-transparent'
    }`}>
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <a href="#" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-200">
            <Shield size={16} className="text-white" />
          </div>
          <span className="font-serif text-xl font-semibold text-slate-900">Citadel</span>
        </a>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8">
          {links.map(({ label, href }) => (
            <a key={label} href={href}
              className="font-sans text-sm text-slate-600 hover:text-slate-900 transition-colors">
              {label}
            </a>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-3">
          <a href="/demo/"
            className="flex items-center gap-1.5 bg-slate-900 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-slate-800 transition-colors">
            <LayoutDashboard size={14} />
            Dashboard
          </a>
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden p-2 rounded-lg hover:bg-slate-100 transition-colors"
          onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
          {mobileOpen ? <X size={20} className="text-slate-600" /> : <Menu size={20} className="text-slate-600" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden glass-strong border-t border-white/60 px-6 py-4 space-y-3">
          {links.map(({ label, href }) => (
            <a key={label} href={href} onClick={() => setMobileOpen(false)}
              className="block font-sans text-sm text-slate-700 hover:text-slate-900 py-2">
              {label}
            </a>
          ))}
          <a href="/demo/"
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-full bg-slate-900 text-white text-sm font-medium mt-2">
            <LayoutDashboard size={14} />
            Open Dashboard
          </a>
        </div>
      )}
    </nav>
  )
}

/* ─── Hero ─── */
function Hero() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden">
      {/* Gradient orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-sky-200/40 blur-[120px] pointer-events-none" />
      <div className="absolute top-[10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-blue-200/30 blur-[100px] pointer-events-none" />
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full bg-sky-100/50 blur-[80px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="flex flex-col items-center text-center">
          {/* Badge */}
          <div className="mb-8 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 text-blue-600 border border-blue-100 font-sans text-sm font-semibold tracking-wide">
            <Zap size={14} />
            AI Governance Infrastructure
          </div>

          {/* H1 */}
          <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl font-medium tracking-tight text-slate-900 max-w-5xl leading-[1.05]">
            The Constitution for<br />your AI Agents.
          </h1>

          {/* Sub */}
          <p className="mt-8 max-w-2xl font-sans text-base md:text-lg text-slate-600 leading-relaxed">
            One SDK call to control, audit, and approve every action your agents take.
            Policy enforcement, human approvals, budget controls, kill switches, and tamper-proof audit — out of the box.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
            <a href="/demo/"
              className="animate-shimmer px-8 py-4 rounded-full text-white font-semibold text-base shadow-lg hover:shadow-xl transition-shadow">
              Get Started Free
            </a>
            <a href="https://citadelsdk.com/docs"
              className="px-8 py-4 rounded-full text-slate-700 font-semibold text-base border border-slate-200 hover:border-blue-300 hover:text-blue-700 transition-colors bg-white/60 backdrop-blur-sm">
              Read the Docs
            </a>
          </div>

          <p className="mt-4 text-slate-400 text-sm font-sans">
            No credit card required · Apache 2.0 SDK · 5-minute setup
          </p>

          {/* Pill strip */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-3">
            {['Policy Engine', 'Human-in-the-Loop', 'Cost Controls', 'Kill Switch', 'Tamper-Proof Audit', 'Multi-Tenant', 'Open SDK'].map((label) => (
              <span key={label} className="px-3 py-1.5 rounded-full glass border border-white/60 text-slate-500 text-xs font-medium">
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── Floating Feature Cards ─── */
const floatingFeatures = [
  {
    icon: <Shield size={20} />,
    title: 'Real-time Control',
    description: 'Intercept and approve agent actions in milliseconds. Zero latency overhead.',
    floatClass: 'animate-float',
  },
  {
    icon: <EyeOff size={20} />,
    title: 'Undetectable Layer',
    description: 'Invisible middleware. Your agents never know governance is running.',
    floatClass: 'animate-float-delayed',
  },
  {
    icon: <ClipboardList size={20} />,
    title: 'Full Audit Trail',
    description: 'Every decision, every action, every rejection — cryptographically logged.',
    floatClass: 'animate-float-slow',
  },
  {
    icon: <Settings size={20} />,
    title: 'Policy Engine',
    description: 'ALLOW, BLOCK, or route to approval. Policies defined in code or dashboard.',
    floatClass: 'animate-float-delayed',
  },
  {
    icon: <DollarSign size={20} />,
    title: 'Cost Controls',
    description: 'Set LLM budgets by tenant, project, agent, or key before provider spend happens.',
    floatClass: 'animate-float-slow',
  },
]

function FloatingFeatures() {
  return (
    <section id="features" className="py-24 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] rounded-full bg-sky-100/30 blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl md:text-5xl font-medium text-slate-900 tracking-tight">
            Governance that just works
          </h2>
          <p className="mt-4 max-w-xl mx-auto font-sans text-base md:text-lg text-slate-600 leading-relaxed">
            Four powerful primitives. Zero configuration headache. Citadel handles the
            complexity so you can focus on building.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {floatingFeatures.map((f) => (
            <div key={f.title}
              className={`glass border-glow rounded-2xl p-6 ${f.floatClass} hover:shadow-lg transition-shadow`}>
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-xl bg-blue-50 text-blue-600">{f.icon}</div>
                <h3 className="font-sans font-semibold text-slate-900 text-sm">{f.title}</h3>
              </div>
              <p className="font-sans text-sm text-slate-600 leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Live Status ─── */
function LiveStatus() {
  return (
    <section className="py-12">
      <div className="max-w-4xl mx-auto px-6">
        <div className="glass-strong border-glow rounded-2xl p-6 md:p-8">
          <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
            <span className="font-sans text-sm font-semibold tracking-wide uppercase text-slate-500">
              System Status
            </span>
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-pulse-glow absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
              </span>
              <span className="font-sans text-sm font-medium text-emerald-600">
                All systems operational
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              { icon: <Zap size={18} className="text-slate-400" />, value: '2.4ms', label: 'avg latency' },
              { icon: <Activity size={18} className="text-slate-400" />, value: '99.99%', label: 'uptime' },
              { icon: <Clock size={18} className="text-slate-400" />, value: '12M+', label: 'actions governed' },
            ].map(({ icon, value, label }) => (
              <div key={label} className="flex items-center gap-3">
                {icon}
                <div>
                  <p className="font-mono text-lg font-medium text-slate-900">{value}</p>
                  <p className="font-sans text-xs text-slate-500">{label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── Code Window ─── */
const consoleLogs = [
  { time: '14:32:01.243', msg: 'Citadel initialized — policy: strict', type: 'ok' },
  { time: '14:32:01.245', msg: 'Agent action intercepted', type: 'ok' },
  { time: '14:32:01.246', msg: 'Policy check passed', type: 'ok' },
  { time: '14:32:01.248', msg: 'Action approved — 1.2ms', type: 'ok' },
  { time: '14:32:01.250', msg: 'Audit log written', type: 'ok' },
  { time: '14:32:01.252', msg: 'Action executed successfully', type: 'ok' },
  { time: '14:32:01.255', msg: 'Rate limit: 34/1000 req/min', type: 'info' },
]

function typeIcon(type: string) {
  if (type === 'ok') return <CheckCircle2 size={12} className="text-emerald-400 shrink-0" />
  if (type === 'warn') return <AlertTriangle size={12} className="text-amber-400 shrink-0" />
  return <XCircle size={12} className="text-red-400 shrink-0" />
}

function CodeWindow() {
  return (
    <section id="how-it-works" className="py-24">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-12">
          <h2 className="font-serif text-4xl md:text-5xl font-medium text-slate-900 tracking-tight">
            See it in action
          </h2>
          <p className="mt-4 max-w-xl mx-auto font-sans text-base text-slate-600 leading-relaxed">
            Install, configure, govern. Every action flows through Citadel before it touches your systems.
          </p>
        </div>

        <div className="rounded-2xl overflow-hidden shadow-2xl border border-slate-200">
          {/* Window chrome */}
          <div className="bg-slate-100 border-b border-slate-200 px-4 py-3 flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-window-red" />
              <span className="w-3 h-3 rounded-full bg-window-yellow" />
              <span className="w-3 h-3 rounded-full bg-window-green" />
            </div>
            <div className="flex-1 text-center">
              <span className="font-mono text-xs text-slate-500 font-medium">agent.py — citadel-demo</span>
            </div>
            <div className="w-14" />
          </div>

          {/* Split body */}
          <div className="flex flex-col md:flex-row">
            {/* Code */}
            <div className="flex-1 bg-slate-900 p-6 md:p-8 overflow-x-auto">
              <pre className="font-mono text-sm leading-relaxed">
                <code>
                  <span className="text-blue-400">import</span>{' '}
                  <span className="text-slate-300">citadel_governance</span>{' '}
                  <span className="text-blue-400">as</span>{' '}
                  <span className="text-slate-300">cg</span>
                  {'\n\n'}
                  <span className="text-slate-500">{'# Configure once at startup'}</span>
                  {'\n'}
                  <span className="text-slate-300">cg.</span>
                  <span className="text-purple-400">configure</span>
                  <span className="text-slate-300">{'({'}</span>
                  {'\n  '}
                  <span className="text-slate-300">base_url=</span>
                  <span className="text-emerald-400">&apos;https://api.citadelsdk.com&apos;</span>
                  <span className="text-slate-300">,</span>
                  {'\n  '}
                  <span className="text-slate-300">api_key=</span>
                  <span className="text-slate-300">os.environ[</span>
                  <span className="text-emerald-400">&apos;CITADEL_KEY&apos;</span>
                  <span className="text-slate-300">],</span>
                  {'\n  '}
                  <span className="text-slate-300">actor_id=</span>
                  <span className="text-emerald-400">&apos;my-agent&apos;</span>
                  {'\n'}
                  <span className="text-slate-300">{'});'}</span>
                  {'\n\n'}
                  <span className="text-slate-500">{'# Every action is governed'}</span>
                  {'\n'}
                  <span className="text-slate-300">result = </span>
                  <span className="text-blue-400">await </span>
                  <span className="text-slate-300">cg.</span>
                  <span className="text-purple-400">execute</span>
                  <span className="text-slate-300">{'({'}</span>
                  {'\n  '}
                  <span className="text-slate-300">action=</span>
                  <span className="text-emerald-400">&apos;stripe.refund&apos;</span>
                  <span className="text-slate-300">,</span>
                  {'\n  '}
                  <span className="text-slate-300">payload={'{'}</span>
                  <span className="text-emerald-400">&apos;amount&apos;</span>
                  <span className="text-slate-300">: </span>
                  <span className="text-amber-400">5000</span>
                  <span className="text-slate-300">{'}'}</span>
                  {'\n'}
                  <span className="text-slate-300">{'});'}</span>
                </code>
              </pre>
            </div>

            {/* Live console */}
            <div className="flex-1 bg-slate-950 p-6 md:p-8 border-t md:border-t-0 md:border-l border-slate-800">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-sans text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Live Console
                </span>
              </div>
              <div className="space-y-2">
                {consoleLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-2">
                    {typeIcon(log.type)}
                    <span className="font-mono text-xs text-slate-500 shrink-0">{log.time}</span>
                    <span className="font-mono text-xs text-slate-300">{log.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── Control Plane ─── */
const controlFeatures = [
  {
    icon: <ArrowDownLeft size={24} strokeWidth={1.5} />,
    title: 'Intercept',
    description: 'Every agent action routes through Citadel first. We evaluate, log, and either approve or reject — before anything reaches your systems.',
  },
  {
    icon: <Scale size={24} strokeWidth={1.5} />,
    title: 'Govern',
    description: 'Set budgets, rate limits, content policies, and approval workflows. Our engine handles the complexity so you write zero custom middleware.',
  },
  {
    icon: <FileSearch size={24} strokeWidth={1.5} />,
    title: 'Audit',
    description: 'Query every decision. Export compliance reports. Prove governance to regulators and customers with cryptographically chained logs.',
  },
]

function ControlPlane() {
  return (
    <section className="py-24">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-start">
          {/* Sticky left */}
          <div className="lg:sticky lg:top-32">
            <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl font-medium text-slate-900 tracking-tight leading-tight">
              Your Control Plane.
              <br />
              Their Blind Spot.
            </h2>
            <p className="mt-6 font-sans text-base md:text-lg text-slate-600 leading-relaxed max-w-md">
              Citadel operates silently between your agents and the outside world.
              You see everything. They see nothing.
            </p>
            <a href="/demo/"
              className="mt-8 inline-flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-full text-sm font-medium hover:bg-slate-800 transition-colors">
              <LayoutDashboard size={14} />
              Open Dashboard
            </a>
          </div>

          {/* Right features */}
          <div className="space-y-12">
            {controlFeatures.map((f) => (
              <div key={f.title} className="flex gap-5">
                <div className="mt-1 p-3 rounded-xl bg-slate-100 text-slate-700 shrink-0 h-fit">
                  {f.icon}
                </div>
                <div>
                  <h3 className="font-sans text-lg font-semibold text-slate-900 mb-2">{f.title}</h3>
                  <p className="font-sans text-base text-slate-500 leading-relaxed">{f.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── All Features Grid ─── */
const allFeatures = [
  { icon: Shield,      title: 'Policy Engine',      body: 'Precedence-based rules evaluate every action: ALLOW, BLOCK, or route to approval.',    color: 'text-blue-600',    bg: 'bg-blue-50'    },
  { icon: Users,       title: 'Human Approvals',    body: 'High-risk actions pause and wait for a human decision in the dashboard.',               color: 'text-violet-600',  bg: 'bg-violet-50'  },
  { icon: Lock,        title: 'Kill Switch',        body: 'One click blocks all agent actions globally, per tenant, or per agent. Instant.',       color: 'text-red-600',     bg: 'bg-red-50'     },
  { icon: FileText,    title: 'Tamper-Proof Audit', body: 'Every decision is cryptographically hashed and chained. Cannot be modified.',           color: 'text-emerald-600', bg: 'bg-emerald-50' },
  { icon: DollarSign,  title: 'Cost Controls',      body: 'Pre-request LLM budget checks block, throttle, or require approval before spend.',      color: 'text-amber-600',   bg: 'bg-amber-50'   },
  { icon: GitBranch,   title: 'Multi-Tenant',       body: 'PostgreSQL Row-Level Security. Each customer sees only their own data.',                color: 'text-sky-600',     bg: 'bg-sky-50'     },
  { icon: Globe,       title: 'Open SDK',           body: 'pip install citadel-governance. Works with LangChain, AutoGen, custom. Apache 2.0.', color: 'text-teal-600',    bg: 'bg-teal-50'    },
]

function FeaturesGrid() {
  return (
    <section className="py-24 bg-slate-50 border-t border-slate-100">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl md:text-5xl font-medium text-slate-900 tracking-tight">
            Everything you need.
          </h2>
          <p className="mt-4 max-w-xl mx-auto font-sans text-base text-slate-600 leading-relaxed">
            Six primitives, one SDK. Citadel handles the complexity so you can focus on shipping.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {allFeatures.map(({ icon: Icon, title, body, color, bg }) => (
            <div key={title}
              className="glass border-glow rounded-2xl p-6 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
              <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center mb-4`}>
                <Icon size={20} className={color} />
              </div>
              <h3 className="font-sans font-semibold text-slate-900 mb-2">{title}</h3>
              <p className="font-sans text-sm text-slate-500 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── CTA ─── */
function CTA() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] rounded-full bg-blue-100/40 blur-[120px] pointer-events-none" />

      <div className="max-w-3xl mx-auto px-6 text-center relative z-10">
        <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto mb-8 shadow-xl shadow-blue-200">
          <Shield size={30} className="text-white" />
        </div>
        <h2 className="font-serif text-4xl md:text-5xl font-medium text-slate-900 tracking-tight mb-4">
          Start governing your<br />agents today.
        </h2>
        <p className="font-sans text-base md:text-lg text-slate-600 leading-relaxed mb-10 max-w-md mx-auto">
          One install. No infrastructure. Connect to our hosted API and see every
          agent action in the dashboard within minutes.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <div className="glass border border-white/60 rounded-xl px-5 py-3.5 flex items-center gap-3">
            <span className="text-slate-400 font-mono text-sm select-none">$</span>
            <span className="font-mono text-sm text-slate-800">pip install citadel-governance</span>
          </div>
          <a href="/demo/"
            className="animate-shimmer px-8 py-3.5 rounded-full text-white font-semibold text-sm shadow-lg hover:shadow-xl transition-shadow">
            Open Dashboard →
          </a>
        </div>

        <p className="mt-6 font-sans text-sm text-slate-400">
          Apache 2.0 SDK · Hosted API · No credit card required
        </p>
      </div>
    </section>
  )
}

/* ─── Footer ─── */
function Footer() {
  return (
    <footer className="border-t border-slate-200 py-12">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <a href="#" className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center">
            <Shield size={12} className="text-white" />
          </div>
          <span className="font-serif text-lg font-semibold text-slate-900">Citadel</span>
        </a>

        <div className="flex items-center gap-6">
          {[
            { label: 'Docs', href: 'https://citadelsdk.com/docs' },
            { label: 'Dashboard', href: '/demo/' },
            { label: 'GitHub', href: 'https://github.com/casss20/citadel-sdk' },
            { label: 'PyPI', href: 'https://pypi.org/project/citadel-governance/' },
          ].map(({ label, href }) => (
            <a key={label} href={href}
              className="font-sans text-sm text-slate-600 hover:text-slate-900 transition-colors">
              {label}
            </a>
          ))}
        </div>

        <p className="font-sans text-sm text-slate-400">© 2026 Citadel SDK Authors. Open SDK under Apache 2.0.</p>
      </div>
    </footer>
  )
}

/* ─── App ─── */
export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-50 via-white to-white">
      <Navigation />
      <main>
        <Hero />
        <FloatingFeatures />
        <LiveStatus />
        <CodeWindow />
        <ControlPlane />
        <FeaturesGrid />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}
