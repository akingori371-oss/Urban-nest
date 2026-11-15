import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth.js";

const features = [
  ["⌕", "Find your dates", "Search by check-in and check-out to see homes that are ready for your stay."],
  ["◎", "Know the total", "Your nightly rate and trip length come together before you book."],
  ["↗", "Pay with M-Pesa", "Approve a secure prompt on your phone and keep your receipt close."],
];
const steps = ["Choose your dates and explore available homes", "Confirm your stay with a clear total", "Pay from your phone and get ready to arrive"];

export default function Landing() {
  const { username } = useAuth();
  if (username) return <Navigate to="/dashboard" replace />;
  return <div className="space-y-20 sm:space-y-28">
    <section className="relative isolate overflow-hidden rounded-[2rem] bg-nest-900 px-6 py-16 text-white shadow-soft sm:px-12 sm:py-24 lg:px-20">
      <div className="absolute -right-16 -top-24 -z-10 size-80 rounded-full bg-nest-600/30 blur-3xl" />
      <div className="absolute -bottom-32 left-1/3 -z-10 size-96 rounded-full bg-emerald-300/10 blur-3xl" />
      <div className="max-w-3xl">
        <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[.18em] text-nest-200"><span className="size-2 rounded-full bg-emerald-300" /> A better way to stay</span>
        <h1 className="mt-7 max-w-2xl text-5xl font-semibold leading-[1.04] tracking-[-.05em] text-white sm:text-6xl lg:text-7xl">A place that feels like <span className="text-nest-300">your place.</span></h1>
        <p className="mt-6 max-w-xl text-base leading-7 text-white/65 sm:text-lg">Find a welcoming home in the city. Browse open dates, see your price upfront, and book with confidence.</p>
        <div className="mt-9 flex flex-wrap gap-3"><Link to="/register" className="rounded-full bg-nest-200 px-6 py-3.5 text-sm font-bold text-nest-900 transition hover:-translate-y-0.5 hover:bg-white">Find your stay <span aria-hidden="true">→</span></Link><Link to="/login" className="rounded-full border border-white/20 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-white/10">I have an account</Link></div>
        <div className="mt-14 flex flex-wrap gap-x-8 gap-y-3 border-t border-white/15 pt-6 text-sm text-white/55"><span>Thoughtful city homes</span><span>·</span><span>Simple M-Pesa payments</span><span>·</span><span>Support when you need it</span></div>
      </div>
    </section>
    <section>
      <div className="mb-8 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">MADE FOR REAL LIFE</p><h2 className="mt-3 max-w-lg text-3xl font-semibold tracking-tight text-ink sm:text-4xl">The details that make booking feel easy.</h2></div><p className="max-w-sm text-sm leading-6 text-muted">From the first search to the last payment, everything you need stays in one calm place.</p></div>
      <div className="grid gap-4 md:grid-cols-3">{features.map(([icon, title, copy], i) => <article key={title} className="group rounded-card border border-line bg-white p-6 shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-soft sm:p-8"><span className={`grid size-12 place-items-center rounded-2xl text-xl ${i === 1 ? "bg-amber-50 text-amber-700" : "bg-nest-100 text-nest-700"}`}>{icon}</span><h3 className="mt-7 text-lg font-semibold text-ink">{title}</h3><p className="mt-2 text-sm leading-6 text-muted">{copy}</p></article>)}</div>
    </section>
    <section className="grid gap-10 rounded-[2rem] border border-line bg-white p-6 shadow-sm sm:p-10 lg:grid-cols-[.8fr_1.2fr] lg:p-14">
      <div><p className="text-xs font-bold uppercase tracking-[.18em] text-nest-600">THREE SIMPLE STEPS</p><h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">From searching to settled.</h2><p className="mt-4 max-w-sm text-sm leading-6 text-muted">A smooth booking leaves more room for the reason you came.</p></div>
      <ol className="divide-y divide-line">{steps.map((step, i) => <li key={step} className="flex gap-5 py-5 first:pt-0 last:pb-0"><span className="grid size-9 shrink-0 place-items-center rounded-full bg-nest-100 text-sm font-bold text-nest-700">0{i + 1}</span><p className="pt-1 text-base font-medium text-ink">{step}</p></li>)}</ol>
    </section>
    <footer className="flex flex-col items-center justify-between gap-4 border-t border-line py-6 text-sm text-muted sm:flex-row"><Link to="/" className="font-bold tracking-tight text-nest-900">Urban Nest</Link><span>Thoughtful stays, right where you need them.</span></footer>
  </div>;
}
