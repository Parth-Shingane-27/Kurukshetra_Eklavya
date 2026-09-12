import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { deleteUploadedDocument, generateChecklist, listUploadedDocuments, uploadDocument } from "../api/client";
import AppShell from "../components/layout/AppShell";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, LoadingMessage } from "../components/StateMessage";

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",")[1] || "");
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function Checklist() {
  const { bundleId } = useParams();
  const [searchParams] = useSearchParams();
  const citizenId = searchParams.get("citizen");
  const navigate = useNavigate();
  const [{ loading, error, checklist }, setState] = useState({ loading: true, error: null, checklist: null });
  const [uploads, setUploads] = useState([]);
  const [uploadError, setUploadError] = useState(null);
  const [uploadingType, setUploadingType] = useState(null);

  const loadUploads = useCallback(() => {
    if (!citizenId) return;
    listUploadedDocuments(citizenId)
      .then(setUploads)
      .catch(() => {});
  }, [citizenId]);

  useEffect(() => loadUploads(), [loadUploads]);

  async function handleFileSelected(documentType, file) {
    if (!file || !citizenId) return;
    setUploadError(null);
    setUploadingType(documentType);
    try {
      const fileBase64 = await readFileAsBase64(file);
      await uploadDocument(citizenId, {
        documentType,
        filename: file.name,
        contentType: file.type || "application/octet-stream",
        fileBase64,
      });
      loadUploads();
    } catch (err) {
      setUploadError(err);
    } finally {
      setUploadingType(null);
    }
  }

  async function handleRemoveUpload(uploadId) {
    if (!citizenId) return;
    try {
      await deleteUploadedDocument(citizenId, uploadId);
      loadUploads();
    } catch (err) {
      setUploadError(err);
    }
  }

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, checklist: null });
    generateChecklist(bundleId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, checklist: data });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, checklist: null });
      });
    return () => {
      cancelled = true;
    };
  }, [bundleId]);

  useEffect(() => run(), [run]);

  const items = checklist?.checklist_items ?? [];
  const heldCount = items.filter((i) => i.status === "held").length;
  const progressPct = items.length > 0 ? Math.round((heldCount / items.length) * 100) : 0;
  const nothingMissing = items.length > 0 && items.every((i) => i.status === "held");

  const reuseItem = useMemo(() => items.find((i) => (i.related_scheme_names || []).length > 1), [items]);

  const grouped = useMemo(() => {
    const groups = new Map();
    items.forEach((item) => {
      (item.related_scheme_names || ["General"]).forEach((schemeName) => {
        if (!groups.has(schemeName)) groups.set(schemeName, []);
        groups.get(schemeName).push(item);
      });
    });
    return [...groups.entries()];
  }, [items]);

  const stages = [
    { key: "profile", label: "Profile complete", done: true },
    { key: "docs", label: "Documents ready", done: nothingMissing, current: !nothingMissing },
    { key: "review", label: "Review", done: false },
    { key: "prepare", label: "Application preparation", done: false },
    { key: "submit", label: "Submission", done: false },
  ];
  const firstNotDoneIndex = stages.findIndex((s) => !s.done);

  return (
    <AppShell
      active="checklist"
      title="Your Application Plan"
      subtitle="Complete the required steps for your selected schemes."
      actions={
        <button className="secondary small" onClick={() => window.print()}>
          Print checklist
        </button>
      }
    >
      {loading && <LoadingMessage>Building your checklist…</LoadingMessage>}
      {error && error.status === 404 && <ErrorMessage error={error} onRetry={run} />}
      {error && error.status !== 404 && (
        <ErrorMessage error={error} onRetry={run}>
          {error.status ? "Something went wrong generating your checklist. Please try again." : undefined}
        </ErrorMessage>
      )}

      {checklist && items.length === 0 && (
        <EmptyState icon="✓" title="Nothing to prepare" description="No documents are required for your selected schemes." />
      )}

      {items.length > 0 && (
        <>
          <div className="card">
            <div className="progress-summary">
              <span>Application readiness</span>
              <span>{progressPct}%</span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <div className="progress-summary" style={{ marginTop: "0.5rem" }}>
              <span>{heldCount} of {items.length} documents ready</span>
              <span>{items.length - heldCount} pending</span>
            </div>
          </div>

          <div className="timeline">
            {stages.map((s, i) => (
              <span key={s.key} className={`timeline-step${s.done ? " done" : i === firstNotDoneIndex ? " current" : ""}`}>
                {s.done ? "✓" : "○"} {s.label}
              </span>
            ))}
          </div>

          {nothingMissing && (
            <EmptyState icon="✓" title="No documents missing" description="You already have everything you need." />
          )}

          {reuseItem && (
            <div className="insight-card">
              <span className="insight-card-icon" aria-hidden="true">💡</span>
              <div>
                <strong>Document reuse opportunity</strong>
                <p>
                  Your {reuseItem.document_type} may be usable across {reuseItem.related_scheme_names.length} selected
                  schemes: {reuseItem.related_scheme_names.join(", ")}.
                </p>
              </div>
            </div>
          )}

          <div className="card">
            <h2>Consolidated checklist</h2>
            {items.map((item) => {
              const existing = uploads.filter((u) => u.document_type === item.document_type);
              return (
                <div className="checklist-item" key={item.document_type}>
                  <div>
                    <strong>{item.document_type}</strong>
                    <div className="schemes">Needed for: {item.related_scheme_names.join(", ")}</div>
                    {citizenId && (
                      <div className="doc-upload-row">
                        <label className="doc-upload-label">
                          {uploadingType === item.document_type ? "Uploading…" : "Attach a copy"}
                          <input
                            type="file"
                            hidden
                            disabled={uploadingType === item.document_type}
                            onChange={(e) => handleFileSelected(item.document_type, e.target.files[0])}
                          />
                        </label>
                        {existing.map((u) => (
                          <span className="doc-upload-chip" key={u.id}>
                            {u.filename}
                            <button type="button" onClick={() => handleRemoveUpload(u.id)} aria-label={`Remove ${u.filename}`}>
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              );
            })}
            {uploadError && <ErrorMessage error={uploadError} />}
            <p className="hint doc-upload-note">
              This just stores a copy for your own reference and marks the document as held — it
              isn&apos;t verified or checked for authenticity by this platform.
            </p>
          </div>

          <h2>Documents by scheme</h2>
          {grouped.map(([schemeName, schemeItems]) => (
            <div className="doc-group" key={schemeName}>
              <div className="doc-group-title">{schemeName}</div>
              <div className="card" style={{ marginBottom: 0 }}>
                {schemeItems.map((item) => (
                  <div className="checklist-item" key={item.document_type}>
                    <strong>{item.document_type}</strong>
                    <StatusBadge status={item.status} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </>
      )}

      {checklist && (
        <div className="actions">
          {citizenId && (
            <button className="secondary" onClick={() => navigate(`/citizens/${citizenId}/trace`)}>
              View reasoning trace →
            </button>
          )}
        </div>
      )}
    </AppShell>
  );
}
