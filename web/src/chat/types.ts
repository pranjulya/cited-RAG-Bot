export type Collection = { collection_id: string; name: string; status: string };

export type ChatDocument = {
  document_id: string;
  logical_name: string;
  status: string | null;
  document_version_id?: string | null;
  failure_code?: string | null;
};

export type Citation = {
  document_id: string;
  document_version_id: string;
  document_name: string;
  page_start: number;
  page_end: number;
};

export type Evidence = {
  id: string;
  document_id: string;
  document_version_id: string;
  document_name: string;
  page_start: number;
  page_end: number;
  text: string;
  truncated: boolean;
};

export type QueryResponse = {
  request_id: string;
  status: "ANSWERED" | "INSUFFICIENT_EVIDENCE";
  answer: string;
  citations: Citation[];
  reason: string | null;
  trace?: { correlation_id: string; evidence: Evidence[] };
};

export type Turn =
  | { id: string; question: string; state: "pending" }
  | { id: string; question: string; state: "done"; response: QueryResponse }
  | { id: string; question: string; state: "error"; message: string; code: string | null; retryable: boolean };

export type SourceView = {
  citation: Citation;
  index: number;
  evidence: Evidence[];
  url: string | null;
  error: string | null;
};
