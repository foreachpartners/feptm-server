export type ApiClientErrorKind = 'network' | 'api' | 'invalid_json';

export class ApiClientError extends Error {
  readonly kind: ApiClientErrorKind;
  readonly status: number | null;

  constructor(message: string, kind: ApiClientErrorKind, status: number | null = null) {
    super(message);
    this.name = 'ApiClientError';
    this.kind = kind;
    this.status = status;
  }
}
