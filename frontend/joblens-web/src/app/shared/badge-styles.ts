const BASE = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset';

// Translucent tint over a dark surface — standard pattern for badges in a
// dark UI (solid light-mode pills like bg-emerald-100 would look out of
// place on a near-black background).
const TONE = {
  green: `${BASE} bg-emerald-500/10 text-emerald-400 ring-emerald-500/20`,
  blue: `${BASE} bg-sky-500/10 text-sky-400 ring-sky-500/20`,
  amber: `${BASE} bg-amber-500/10 text-amber-400 ring-amber-500/20`,
  red: `${BASE} bg-red-500/10 text-red-400 ring-red-500/20`,
  zinc: `${BASE} bg-zinc-500/10 text-zinc-400 ring-zinc-500/20`,
  // Reserved for genuine "active opportunity" / "actively relevant" signals —
  // the one badge tone allowed to use the brand accent, per design direction.
  brand: `${BASE} bg-brand-600/10 text-brand-400 ring-brand-600/25`,
};

export function contractBadgeClass(contractType: string | null): string {
  switch (contractType) {
    case 'CDI':
      return TONE.green;
    case 'CDD':
      return TONE.blue;
    case 'Stage':
    case 'Alternance':
      return TONE.amber;
    default:
      return TONE.zinc;
  }
}

export function activeOpportunityBadgeClass(isActive: boolean): string {
  return isActive ? TONE.brand : TONE.zinc;
}

export function hiringSignalBadgeClass(signal: string): string {
  switch (signal) {
    case 'HIGH':
      return TONE.green;
    case 'MEDIUM':
      return TONE.amber;
    case 'LOW':
      return TONE.red;
    default:
      return TONE.zinc;
  }
}

export function companyStatusBadgeClass(status: string): string {
  switch (status) {
    case 'ACTIVE_RELEVANT':
      return TONE.brand;
    case 'MONITOR':
    case 'POTENTIALLY_RELEVANT':
      return TONE.blue;
    case 'LOW_PRIORITY':
      return TONE.amber;
    case 'NOT_RELEVANT':
      return TONE.red;
    default:
      return TONE.zinc;
  }
}

export function coverageBadgeClass(state: string | null): string {
  switch (state) {
    case 'COMPLETE':
      return TONE.green;
    case 'PARTIAL':
      return TONE.amber;
    case 'FAILED':
      return TONE.red;
    default:
      return TONE.zinc;
  }
}

export function urlFlagBadgeClass(ok: boolean): string {
  return ok ? TONE.green : TONE.red;
}
