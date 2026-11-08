const STYLES = {
  APPLIED: 'bg-slate-700 text-slate-300 border-slate-600',
  SHORTLISTED: 'bg-amber-950/60 text-amber-300 border-amber-700',
  INTERVIEW_CLEARED: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
  REJECTED: 'bg-rose-950/80 text-rose-300 border-rose-800',
  OFFERED: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
  ACCEPTED: 'bg-emerald-900/70 text-emerald-200 border-emerald-600',
  DECLINED: 'bg-rose-950/80 text-rose-300 border-rose-800',
  PASS: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
  FAIL: 'bg-rose-950/80 text-rose-300 border-rose-800',
  PENDING: 'bg-slate-700 text-slate-300 border-slate-600',
  ISSUED: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
};

export default function StatusBadge({ status }) {
  const label = status === 'INTERVIEW_CLEARED' ? 'SELECTION COMPLETED' : status.replaceAll('_', ' ');
  const style = STYLES[status] || 'bg-slate-700 text-slate-300 border-slate-600';
  return (
    <span className={`px-3 py-1 rounded-full text-xs border ${style}`}>
      {label}
    </span>
  );
}
