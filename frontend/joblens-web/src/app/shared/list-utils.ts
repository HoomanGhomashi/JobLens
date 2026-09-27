/** Client-side pagination — used identically in Local Mode and Demo Mode. */
export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

/** Case/accent-insensitive substring match across one or more text fields. */
export function matchesSearch(term: string, ...fields: (string | null | undefined)[]): boolean {
  if (!term.trim()) {
    return true;
  }
  const normalize = (s: string) =>
    s
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '');
  const needle = normalize(term);
  return fields.some((f) => !!f && normalize(f).includes(needle));
}
