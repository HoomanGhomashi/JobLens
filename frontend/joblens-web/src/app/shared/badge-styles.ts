const BASE = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium';

const TONE = {
  green: `${BASE} bg-emerald-100 text-emerald-700`,
  blue: `${BASE} bg-blue-100 text-blue-700`,
  amber: `${BASE} bg-amber-100 text-amber-700`,
  red: `${BASE} bg-red-100 text-red-700`,
  slate: `${BASE} bg-slate-100 text-slate-600`,
  indigo: `${BASE} bg-indigo-100 text-indigo-700`,
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
    case 'Freelance':
      return TONE.indigo;
    default:
      return TONE.slate;
  }
}

export function activeOpportunityBadgeClass(isActive: boolean): string {
  return isActive ? TONE.green : TONE.slate;
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
      return TONE.slate;
  }
}

export function companyStatusBadgeClass(status: string): string {
  switch (status) {
    case 'ACTIVE_RELEVANT':
      return TONE.green;
    case 'MONITOR':
    case 'POTENTIALLY_RELEVANT':
      return TONE.blue;
    case 'LOW_PRIORITY':
      return TONE.amber;
    case 'NOT_RELEVANT':
      return TONE.red;
    default:
      return TONE.slate;
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
      return TONE.slate;
  }
}

export function urlFlagBadgeClass(ok: boolean): string {
  return ok ? TONE.green : TONE.red;
}
