/** Null means the source has no value. Show that, never 0 or an empty string. */
export function displayValue(value: string | number | null | undefined): string {
  return value === null || value === undefined ? 'Not available' : String(value)
}
