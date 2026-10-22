/** T.C. Kimlik No resmi kontrol hanesi algoritması. */
export function isValidTcKimlik(value: string): boolean {
  if (!/^[1-9][0-9]{10}$/.test(value)) return false;
  const d = value.split('').map(Number);
  const odd = d[0] + d[2] + d[4] + d[6] + d[8];
  const even = d[1] + d[3] + d[5] + d[7];
  const tenth = (((odd * 7 - even) % 10) + 10) % 10;
  if (tenth !== d[9]) return false;
  const eleventh = d.slice(0, 10).reduce((sum, n) => sum + n, 0) % 10;
  return eleventh === d[10];
}

export function maskTcKimlik(value: string): string {
  return value.length === 11 ? `${value.slice(0, 3)}******${value.slice(9)}` : value;
}
