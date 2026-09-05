export function projectCardHref(driveFolderId: string, name: string): string {
  return `/projects/${encodeURIComponent(driveFolderId)}?name=${encodeURIComponent(name)}`;
}
