import React, { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchClaimById, applyClaimUpdate } from "../redux/claimDetailsSlice";
import { openClaimDetailSocket } from "../utils/ws";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  FileText,
  File,
  Image,
  Download,
  Loader2,
} from "lucide-react";

export default function ClaimDetail() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const claim = useSelector((s) => s.claimDetails);
  const socketRef = useRef(null);

  useEffect(() => {
    if (id) dispatch(fetchClaimById(id));

    const ws = openClaimDetailSocket(id, (msg) => {
      // msg shapes:
      // { stage: "agent1", message: "...", result: {...}, claimId }
      // { stage: "done", message: "Completed", result: {...} }
      if (msg.claimId && msg.claimId !== id && msg.id && msg.id !== id) {
        // ignore others
      }
      // keep redux slice in sync
      dispatch(applyClaimUpdate(msg));
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [dispatch, id]);

  // mapping to preserve your original variable names used in your UI
  const result = claim.aiExtracted || {}; // this contains the pipeline "result" as returned by backend
  const submitted = claim.submittingUser || {};

  // Keep the same markup and style blocks from your original InsuranceAgentUI,
  // but remove the upload portion and show "Submitted by user" + "AI Extracted" sections.
  return (
    <div className="insurance-container">
      <div className="insurance-wrapper">
        {/* Header */}
        <div className="header">
          <div className="header-icon">
            <FileText className="header-icon-svg" />
          </div>
          <h1 className="header-title">
            Health Insurance Claim — Claim ID: {id}
          </h1>
          <p className="header-subtitle">
            Agency view — submitted data (left) and AI-extracted data (right)
          </p>
        </div>

        {/* Live agent stage indicator */}
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 12 }}>Verification Progress</h3>

          <div style={{ display: "flex", gap: 20 }}>
            {/* Agent 1 */}
            <div style={{ textAlign: "center" }}>
              <div
                className={`stage-circle ${
                  claim.status === "ocr" ||
                  claim.status === "agent1" ||
                  claim.status === "completed"
                    ? "active"
                    : ""
                }`}
              >
                1
              </div>
              <div>OCR / Extraction</div>
            </div>

            {/* Agent 2 */}
            <div style={{ textAlign: "center" }}>
              <div
                className={`stage-circle ${
                  claim.status === "agent1" || claim.status === "completed"
                    ? "active"
                    : ""
                }`}
              >
                2
              </div>
              <div>Coverage + Missing Docs</div>
            </div>

            {/* Agent 3 */}
            <div style={{ textAlign: "center" }}>
              <div
                className={`stage-circle ${
                  claim.status === "completed" ? "active" : ""
                }`}
              >
                3
              </div>
              <div>Final Report Generation</div>
            </div>
          </div>
        </div>

        <style jsx>{`
          .stage-circle {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 3px solid #ccc;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 6px auto;
            font-weight: 700;
          }
          .stage-circle.active {
            border-color: #2563eb;
            background: #dbeafe;
            color: #1e3a8a;
          }
        `}</style>

        {/* Top Info Cards: Submitted user info + AI Extracted summary */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            marginBottom: 16,
          }}
        >
          <div className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <h3 style={{ margin: 0 }}>Submitted by user</h3>
                <div className="small">Data sent from Flutter app</div>
              </div>
              <div className="small">
                Submitted:{" "}
                {submitted.createdAt
                  ? new Date(submitted.createdAt).toLocaleString()
                  : "-"}
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ marginBottom: 8 }}>
                <strong>Name:</strong> {submitted.name || "-"}
              </div>
              <div style={{ marginBottom: 8 }}>
                <strong>Insurance ID:</strong> {submitted.insuranceId || "-"}
              </div>
              <div style={{ marginBottom: 8 }}>
                <strong>Policy Name:</strong> {submitted.policyName || "-"}
              </div>
            </div>
          </div>

          <div className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <h3 style={{ margin: 0 }}>AI Extracted (Pipeline)</h3>
                <div className="small">
                  Data extracted and generated by agents
                </div>
              </div>
              <div className="small">Status: {claim.status || "-"}</div>
            </div>

            <div style={{ marginTop: 12 }}>
              {/* map many possible fields in result.report.summary */}
              {result.report && result.report.summary ? (
                <div className="summary-grid">
                  {result.report.summary.patient_name && (
                    <div className="summary-item">
                      <span className="summary-label">Patient Name:</span>
                      <span className="summary-value">
                        {result.report.summary.patient_name}
                      </span>
                    </div>
                  )}
                  {result.report.summary.policy_number && (
                    <div className="summary-item">
                      <span className="summary-label">Policy Number:</span>
                      <span className="summary-value">
                        {result.report.summary.policy_number}
                      </span>
                    </div>
                  )}
                  {result.report.summary.insurer_guess && (
                    <div className="summary-item">
                      <span className="summary-label">Insurer:</span>
                      <span className="summary-value">
                        {result.report.summary.insurer_guess}
                      </span>
                    </div>
                  )}
                  {result.report.summary.hospital && (
                    <div className="summary-item">
                      <span className="summary-label">Hospital:</span>
                      <span className="summary-value">
                        {result.report.summary.hospital}
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="small">
                  No AI extracted summary available yet
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Below we include the rest of your original UI, but read-only and driven by `result` */}
        {/* RESULTS SECTION: replicated from your original component but using the result variable */}
        {result && (
          <div className="results-section">
            {/* Report Summary */}
            {result.report && result.report.summary && (
              <div className="card">
                <div className="section-header">
                  <div className="section-icon section-icon-blue">
                    <FileText className="section-icon-svg" />
                  </div>
                  <h2 className="section-title">Claim Summary</h2>
                </div>

                <div className="summary-grid">
                  {result.report.summary.patient_name && (
                    <div className="summary-item">
                      <span className="summary-label">Patient Name:</span>
                      <span className="summary-value">
                        {result.report.summary.patient_name}
                      </span>
                    </div>
                  )}
                  {result.report.summary.policy_number && (
                    <div className="summary-item">
                      <span className="summary-label">Policy Number:</span>
                      <span className="summary-value">
                        {result.report.summary.policy_number}
                      </span>
                    </div>
                  )}
                  {result.report.summary.insurer_guess && (
                    <div className="summary-item">
                      <span className="summary-label">Insurer:</span>
                      <span className="summary-value">
                        {result.report.summary.insurer_guess}
                      </span>
                    </div>
                  )}
                  {result.report.summary.hospital && (
                    <div className="summary-item">
                      <span className="summary-label">Hospital:</span>
                      <span className="summary-value">
                        {result.report.summary.hospital}
                      </span>
                    </div>
                  )}
                  {result.report.summary.admission_date && (
                    <div className="summary-item">
                      <span className="summary-label">Admission Date:</span>
                      <span className="summary-value">
                        {result.report.summary.admission_date}
                      </span>
                    </div>
                  )}
                  {result.report.summary.discharge_date && (
                    <div className="summary-item">
                      <span className="summary-label">Discharge Date:</span>
                      <span className="summary-value">
                        {result.report.summary.discharge_date}
                      </span>
                    </div>
                  )}
                  {result.report.summary.diagnosis && (
                    <div className="summary-item full-width">
                      <span className="summary-label">Diagnosis:</span>
                      <span className="summary-value">
                        {result.report.summary.diagnosis}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Verdict */}
            {result.report && result.report.verdict && (
              <div className="card">
                <div className="section-header">
                  <div
                    className={`section-icon ${
                      result.report.verdict === "Eligible"
                        ? "section-icon-green"
                        : result.report.verdict.includes("Rejected")
                        ? "section-icon-red"
                        : "section-icon-orange"
                    }`}
                  >
                    {result.report.verdict === "Eligible" ? (
                      <CheckCircle className="section-icon-svg" />
                    ) : (
                      <AlertCircle className="section-icon-svg" />
                    )}
                  </div>
                  <h2 className="section-title">Claim Status</h2>
                </div>

                <div
                  className={`verdict-box verdict-${
                    result.report.verdict === "Eligible" ? "eligible" : "review"
                  }`}
                >
                  <div className="verdict-title">{result.report.verdict}</div>
                  {result.report.human_verdict && (
                    <div className="verdict-message">
                      {result.report.human_verdict}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Financial Summary */}
            {result.report && result.report.financial_summary && (
              <div className="card">
                <div className="section-header">
                  <div className="section-icon section-icon-blue">
                    <FileText className="section-icon-svg" />
                  </div>
                  <h2 className="section-title">Financial Summary</h2>
                </div>

                <div className="financial-grid">
                  {result.report.financial_summary.total_bill_amount && (
                    <div className="financial-item">
                      <span className="financial-label">
                        Total Bill Amount:
                      </span>
                      <span className="financial-value financial-total">
                        ₹
                        {Number(
                          result.report.financial_summary.total_bill_amount,
                        ).toLocaleString("en-IN")}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary
                    .total_payable_before_copay && (
                    <div className="financial-item">
                      <span className="financial-label">
                        Payable Before Co-pay:
                      </span>
                      <span className="financial-value">
                        ₹
                        {Number(
                          result.report.financial_summary
                            .total_payable_before_copay,
                        ).toLocaleString("en-IN")}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.co_pay_amount && (
                    <div className="financial-item">
                      <span className="financial-label">Co-pay Amount:</span>
                      <span className="financial-value financial-copay">
                        ₹
                        {Number(
                          result.report.financial_summary.co_pay_amount,
                        ).toLocaleString("en-IN")}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.final_insurance_payable && (
                    <div className="financial-item highlight">
                      <span className="financial-label">
                        Insurance Payable:
                      </span>
                      <span className="financial-value financial-insurance">
                        ₹
                        {Number(
                          result.report.financial_summary
                            .final_insurance_payable,
                        ).toLocaleString("en-IN")}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.user_payable_estimate && (
                    <div className="financial-item">
                      <span className="financial-label">
                        Your Estimated Share:
                      </span>
                      <span className="financial-value financial-user">
                        ₹
                        {Number(
                          result.report.financial_summary.user_payable_estimate,
                        ).toLocaleString("en-IN")}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Coverage Breakdown */}
            {result.coverage_result && result.coverage_result.breakdown && (
              <div className="card">
                <div className="section-header">
                  <div className="section-icon section-icon-blue">
                    <FileText className="section-icon-svg" />
                  </div>
                  <h2 className="section-title">Coverage Breakdown</h2>
                </div>

                <div className="breakdown-table">
                  <div className="breakdown-header">
                    <div className="breakdown-col">Category</div>
                    <div className="breakdown-col">Charged</div>
                    <div className="breakdown-col">Allowed</div>
                    <div className="breakdown-col">Not Allowed</div>
                  </div>
                  {Object.entries(result.coverage_result.breakdown).map(
                    ([key, value]) => (
                      <div key={key} className="breakdown-row">
                        <div className="breakdown-col breakdown-category">
                          {key
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (l) => l.toUpperCase())}
                        </div>
                        <div className="breakdown-col">
                          ₹{Number(value.charged || 0).toLocaleString("en-IN")}
                        </div>
                        <div className="breakdown-col breakdown-allowed">
                          ₹{Number(value.allowed || 0).toLocaleString("en-IN")}
                        </div>
                        <div
                          className={`breakdown-col ${
                            value.not_allowed > 0 ? "breakdown-not-allowed" : ""
                          }`}
                        >
                          ₹
                          {Number(value.not_allowed || 0).toLocaleString(
                            "en-IN",
                          )}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>
            )}

            {/* Missing Documents */}
            <div className="card">
              <div className="section-header">
                <div className="section-icon section-icon-orange">
                  <AlertCircle className="section-icon-svg" />
                </div>
                <h2 className="section-title">Missing Documents</h2>
              </div>

              {result.missing_documents &&
              result.missing_documents.length > 0 ? (
                <div>
                  <div className="doc-list">
                    {result.missing_documents.map((doc, index) => (
                      <div key={index} className="doc-item doc-item-missing">
                        <XCircle className="doc-icon" />
                        <span className="doc-text">
                          {doc
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (l) => l.toUpperCase())}
                        </span>
                      </div>
                    ))}
                  </div>
                  {result.missing_documents_full &&
                    result.missing_documents_full.recommended_actions && (
                      <div className="recommendations-box">
                        <h4 className="recommendations-title">
                          Recommendations:
                        </h4>
                        <ul className="recommendations-list">
                          {result.missing_documents_full.recommended_actions.map(
                            (action, idx) => (
                              <li key={idx}>{action}</li>
                            ),
                          )}
                        </ul>
                      </div>
                    )}
                </div>
              ) : (
                <div className="success-message">
                  <CheckCircle className="success-icon" />
                  <span className="success-text">
                    All required documents are present!
                  </span>
                </div>
              )}
            </div>

            {/* Reasons & Recommendations */}
            {result.report && (
              <div className="card">
                <div className="section-header">
                  <div className="section-icon section-icon-blue">
                    <AlertCircle className="section-icon-svg" />
                  </div>
                  <h2 className="section-title">Important Notes</h2>
                </div>

                {result.report.reasons && result.report.reasons.length > 0 && (
                  <div className="notes-section">
                    <h4 className="notes-title">Reasons:</h4>
                    <ul className="notes-list">
                      {result.report.reasons.map((reason, idx) => (
                        <li key={idx} className="note-item note-reason">
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.report.recommended_actions &&
                  result.report.recommended_actions.length > 0 && (
                    <div className="notes-section">
                      <h4 className="notes-title">Recommended Actions:</h4>
                      <ul className="notes-list">
                        {result.report.recommended_actions.map(
                          (action, idx) => (
                            <li key={idx} className="note-item note-action">
                              {action}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}
              </div>
            )}

            {/* Classified Documents */}
            {result.classified_documents &&
              Object.keys(result.classified_documents).length > 0 && (
                <div className="card">
                  <div className="section-header">
                    <div className="section-icon section-icon-green">
                      <File className="section-icon-svg" />
                    </div>
                    <h2 className="section-title">Uploaded Documents</h2>
                  </div>

                  <div className="classified-list">
                    {Object.entries(result.classified_documents).map(
                      ([filename, data]) => (
                        <div key={filename} className="classified-item">
                          <div className="classified-file">
                            <File className="classified-icon" />
                            <span className="classified-filename">
                              {filename}
                            </span>
                          </div>
                          <div className="classified-type">
                            <span className="type-badge">
                              {data.type
                                ? data.type
                                    .replace(/_/g, " ")
                                    .replace(/\b\w/g, (l) => l.toUpperCase())
                                : "Unknown"}
                            </span>
                            {data.debug && data.debug.confidence && (
                              <span className="confidence-badge">
                                {(data.debug.confidence * 100).toFixed(0)}%
                                confidence
                              </span>
                            )}
                          </div>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              )}

            {/* Generated PDFs */}
            {result.generated_pdfs &&
              Object.keys(result.generated_pdfs).length > 0 && (
                <div className="card">
                  <div className="section-header">
                    <div className="section-icon section-icon-green">
                      <Download className="section-icon-svg" />
                    </div>
                    <h2 className="section-title">Generated Reports</h2>
                  </div>

                  <div className="pdf-list">
                    {Object.entries(result.generated_pdfs).map(
                      ([name, url]) => (
                        <a
                          key={name}
                          href={`${
                            url.startsWith("http")
                              ? url
                              : `https://questionnaire-astrology-reasoning-dramatically.trycloudflare.com${url}`
                          }`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="pdf-link"
                        >
                          <div className="pdf-info">
                            <FileText className="pdf-icon" />
                            <span className="pdf-name">
                              {name
                                .replace(/_/g, " ")
                                .replace(/\b\w/g, (l) => l.toUpperCase())}
                            </span>
                          </div>
                          <Download className="download-icon" />
                        </a>
                      ),
                    )}
                  </div>
                </div>
              )}
          </div>
        )}
      </div>

      <style jsx>{`
        .insurance-container {
          min-height: 100vh;
          background: linear-gradient(
            135deg,
            #e0f2fe 0%,
            #ffffff 50%,
            #fae8ff 100%
          );
          padding: 3rem 1.5rem;
        }

        .insurance-wrapper {
          max-width: 1200px;
          margin: 0 auto;
        }

        .header {
          text-align: center;
          margin-bottom: 3rem;
        }

        .header-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 64px;
          height: 64px;
          background: #2563eb;
          border-radius: 16px;
          margin-bottom: 1rem;
        }

        .header-icon-svg {
          width: 32px;
          height: 32px;
          color: white;
        }

        .header-title {
          font-size: 2.5rem;
          font-weight: 700;
          color: #111827;
          margin-bottom: 0.5rem;
        }

        .header-subtitle {
          font-size: 1.125rem;
          color: #6b7280;
        }

        .card {
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
            0 10px 10px -5px rgba(0, 0, 0, 0.04);
          padding: 2rem;
          margin-bottom: 2rem;
          border: 1px solid #f3f4f6;
        }

        .results-section {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .section-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }

        .section-icon {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .section-icon-svg {
          width: 24px;
          height: 24px;
        }

        .section-icon-orange {
          background: #ffedd5;
        }
        .section-icon-orange .section-icon-svg {
          color: #ea580c;
        }

        .section-icon-blue {
          background: #dbeafe;
        }
        .section-icon-blue .section-icon-svg {
          color: #2563eb;
        }

        .section-icon-green {
          background: #d1fae5;
        }
        .section-icon-green .section-icon-svg {
          color: #059669;
        }

        .section-icon-red {
          background: #fee2e2;
        }
        .section-icon-red .section-icon-svg {
          color: #dc2626;
        }

        .section-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #111827;
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
        }

        .summary-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .summary-label {
          font-size: 0.875rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
        }

        .summary-value {
          font-size: 1rem;
          color: #111827;
        }

        .verdict-box {
          padding: 1.5rem;
          border-radius: 12px;
          text-align: center;
        }

        .verdict-eligible {
          background: #d1fae5;
          border: 2px solid #10b981;
        }

        .verdict-review {
          background: #ffedd5;
          border: 2px solid #f59e0b;
        }

        .verdict-title {
          font-size: 1.5rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
        }

        .verdict-message {
          font-size: 1rem;
        }

        .financial-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .financial-item {
          padding: 1rem;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .breakdown-table {
          overflow-x: auto;
        }

        .breakdown-header,
        .breakdown-row {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr;
          gap: 1rem;
          padding: 0.75rem 1rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .doc-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .doc-item-missing {
          background: #ffedd5;
          border: 1px solid #fed7aa;
        }

        .pdf-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .pdf-link {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: #d1fae5;
          border: 1px solid #34d399;
          border-radius: 12px;
          padding: 1rem;
          text-decoration: none;
        }
      `}</style>
    </div>
  );
}
