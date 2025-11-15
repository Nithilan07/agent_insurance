












import React, { useState } from "react";
import { Upload, FileText, CheckCircle, XCircle, Download, AlertCircle, Loader2, File, Image } from "lucide-react";


export default function InsuranceAgentUI() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles(droppedFiles);
    }
  };

  const handleSubmit = async () => {
    if (!files.length) {
      setError("Please upload at least one PDF or image.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    for (let file of files) {
      formData.append("files", file);
    }
    formData.append("generate_pdfs", "true");

    try {
      const res = await fetch("https://questionnaire-astrology-reasoning-dramatically.trycloudflare.com/process", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Something went wrong");
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    }

    setLoading(false);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const getFileIcon = (fileName) => {
    const ext = fileName.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
      return <Image className="file-icon file-icon-image" />;
    }
    return <File className="file-icon file-icon-file" />;
  };

  return (
    <div className="insurance-container">
      <div className="insurance-wrapper">
        {/* Header */}
        <div className="header">
          <div className="header-icon">
            <FileText className="header-icon-svg" />
          </div>
          <h1 className="header-title">
            Health Insurance Claim with Agentic AI
          </h1>
          <p className="header-subtitle">
            Upload your documents for instant claim verification and analysis
          </p>
        </div>

        {/* Upload Section */}
        <div className="card">
          <div
            className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              className="file-input-hidden"
              id="file-upload"
              accept=".pdf,.jpg,.jpeg,.png"
            />
            <label htmlFor="file-upload" className="upload-label">
              <Upload className="upload-icon" />
              <p className="upload-title">
                Drop your files here or click to browse
              </p>
              <p className="upload-subtitle">
                Supports PDF, JPG, PNG • Multiple files accepted
              </p>
            </label>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="file-list">
              <h3 className="file-list-title">
                Selected Files ({files.length})
              </h3>
              <div className="file-items">
                {files.map((file, index) => (
                  <div key={index} className="file-item">
                    <div className="file-info">
                      {getFileIcon(file.name)}
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">
                        ({(file.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                    <button
                      onClick={() => removeFile(index)}
                      className="remove-btn"
                    >
                      <XCircle className="remove-icon" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={loading || files.length === 0}
            className={`submit-btn ${loading || files.length === 0 ? 'disabled' : ''}`}
          >
            {loading ? (
              <span className="btn-content">
                <Loader2 className="spinner" />
                Processing Claims...
              </span>
            ) : (
              "Analyze Documents"
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="alert alert-error">
            <AlertCircle className="alert-icon" />
            <div>
              <h3 className="alert-title">Error</h3>
              <p className="alert-message">{error}</p>
            </div>
          </div>
        )}

        {/* Results Section */}
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
                      <span className="summary-value">{result.report.summary.patient_name}</span>
                    </div>
                  )}
                  {result.report.summary.policy_number && (
                    <div className="summary-item">
                      <span className="summary-label">Policy Number:</span>
                      <span className="summary-value">{result.report.summary.policy_number}</span>
                    </div>
                  )}
                  {result.report.summary.insurer_guess && (
                    <div className="summary-item">
                      <span className="summary-label">Insurer:</span>
                      <span className="summary-value">{result.report.summary.insurer_guess}</span>
                    </div>
                  )}
                  {result.report.summary.hospital && (
                    <div className="summary-item">
                      <span className="summary-label">Hospital:</span>
                      <span className="summary-value">{result.report.summary.hospital}</span>
                    </div>
                  )}
                  {result.report.summary.admission_date && (
                    <div className="summary-item">
                      <span className="summary-label">Admission Date:</span>
                      <span className="summary-value">{result.report.summary.admission_date}</span>
                    </div>
                  )}
                  {result.report.summary.discharge_date && (
                    <div className="summary-item">
                      <span className="summary-label">Discharge Date:</span>
                      <span className="summary-value">{result.report.summary.discharge_date}</span>
                    </div>
                  )}
                  {result.report.summary.diagnosis && (
                    <div className="summary-item full-width">
                      <span className="summary-label">Diagnosis:</span>
                      <span className="summary-value">{result.report.summary.diagnosis}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Verdict */}
            {result.report && result.report.verdict && (
              <div className="card">
                <div className="section-header">
                  <div className={`section-icon ${result.report.verdict === "Eligible"
                    ? "section-icon-green"
                    : result.report.verdict.includes("Rejected")
                      ? "section-icon-red"
                      : "section-icon-orange"
                    }`}>
                    {result.report.verdict === "Eligible" ? (
                      <CheckCircle className="section-icon-svg" />
                    ) : (
                      <AlertCircle className="section-icon-svg" />
                    )}
                  </div>
                  <h2 className="section-title">Claim Status</h2>
                </div>

                <div className={`verdict-box verdict-${result.report.verdict === "Eligible" ? "eligible" : "review"}`}>
                  <div className="verdict-title">{result.report.verdict}</div>
                  {result.report.human_verdict && (
                    <div className="verdict-message">{result.report.human_verdict}</div>
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
                      <span className="financial-label">Total Bill Amount:</span>
                      <span className="financial-value financial-total">
                        ₹{Number(result.report.financial_summary.total_bill_amount).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.total_payable_before_copay && (
                    <div className="financial-item">
                      <span className="financial-label">Payable Before Co-pay:</span>
                      <span className="financial-value">
                        ₹{Number(result.report.financial_summary.total_payable_before_copay).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.co_pay_amount && (
                    <div className="financial-item">
                      <span className="financial-label">Co-pay Amount:</span>
                      <span className="financial-value financial-copay">
                        ₹{Number(result.report.financial_summary.co_pay_amount).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.final_insurance_payable && (
                    <div className="financial-item highlight">
                      <span className="financial-label">Insurance Payable:</span>
                      <span className="financial-value financial-insurance">
                        ₹{Number(result.report.financial_summary.final_insurance_payable).toLocaleString('en-IN')}
                      </span>
                    </div>
                  )}
                  {result.report.financial_summary.user_payable_estimate && (
                    <div className="financial-item">
                      <span className="financial-label">Your Estimated Share:</span>
                      <span className="financial-value financial-user">
                        ₹{Number(result.report.financial_summary.user_payable_estimate).toLocaleString('en-IN')}
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
                  {Object.entries(result.coverage_result.breakdown).map(([key, value]) => (
                    <div key={key} className="breakdown-row">
                      <div className="breakdown-col breakdown-category">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </div>
                      <div className="breakdown-col">
                        ₹{Number(value.charged || 0).toLocaleString('en-IN')}
                      </div>
                      <div className="breakdown-col breakdown-allowed">
                        ₹{Number(value.allowed || 0).toLocaleString('en-IN')}
                      </div>
                      <div className={`breakdown-col ${value.not_allowed > 0 ? 'breakdown-not-allowed' : ''}`}>
                        ₹{Number(value.not_allowed || 0).toLocaleString('en-IN')}
                      </div>
                    </div>
                  ))}
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

              {result.missing_documents && result.missing_documents.length > 0 ? (
                <div>
                  <div className="doc-list">
                    {result.missing_documents.map((doc, index) => (
                      <div key={index} className="doc-item doc-item-missing">
                        <XCircle className="doc-icon" />
                        <span className="doc-text">{doc.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                      </div>
                    ))}
                  </div>
                  {result.missing_documents_full && result.missing_documents_full.recommended_actions && (
                    <div className="recommendations-box">
                      <h4 className="recommendations-title">Recommendations:</h4>
                      <ul className="recommendations-list">
                        {result.missing_documents_full.recommended_actions.map((action, idx) => (
                          <li key={idx}>{action}</li>
                        ))}
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
                        <li key={idx} className="note-item note-reason">{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.report.recommended_actions && result.report.recommended_actions.length > 0 && (
                  <div className="notes-section">
                    <h4 className="notes-title">Recommended Actions:</h4>
                    <ul className="notes-list">
                      {result.report.recommended_actions.map((action, idx) => (
                        <li key={idx} className="note-item note-action">{action}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Classified Documents */}
            {result.classified_documents && Object.keys(result.classified_documents).length > 0 && (
              <div className="card">
                <div className="section-header">
                  <div className="section-icon section-icon-green">
                    <File className="section-icon-svg" />
                  </div>
                  <h2 className="section-title">Uploaded Documents</h2>
                </div>

                <div className="classified-list">
                  {Object.entries(result.classified_documents).map(([filename, data]) => (
                    <div key={filename} className="classified-item">
                      <div className="classified-file">
                        <File className="classified-icon" />
                        <span className="classified-filename">{filename}</span>
                      </div>
                      <div className="classified-type">
                        <span className="type-badge">
                          {data.type ? data.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Unknown'}
                        </span>
                        {data.debug && data.debug.confidence && (
                          <span className="confidence-badge">
                            {(data.debug.confidence * 100).toFixed(0)}% confidence
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Generated PDFs */}
            {result.generated_pdfs && Object.keys(result.generated_pdfs).length > 0 && (
              <div className="card">
                <div className="section-header">
                  <div className="section-icon section-icon-green">
                    <Download className="section-icon-svg" />
                  </div>
                  <h2 className="section-title">Generated Reports</h2>
                </div>

                <div className="pdf-list">
                  {Object.entries(result.generated_pdfs).map(([name, url]) => (
                    <a
                      key={name}
                      href={`https://questionnaire-astrology-reasoning-dramatically.trycloudflare.com${url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="pdf-link"
                    >
                      <div className="pdf-info">
                        <FileText className="pdf-icon" />
                        <span className="pdf-name">{name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                      </div>
                      <Download className="download-icon" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .insurance-container {
          min-height: 100vh;
          background: linear-gradient(135deg, #e0f2fe 0%, #ffffff 50%, #fae8ff 100%);
          padding: 3rem 1.5rem;
        }

        .insurance-wrapper {
          max-width: 1200px;
          margin: 0 auto;
        }

        /* Header */
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

        /* Card */
        .card {
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          padding: 2rem;
          margin-bottom: 2rem;
          border: 1px solid #f3f4f6;
        }

        /* Upload Zone */
        .upload-zone {
          border: 2px dashed #d1d5db;
          border-radius: 12px;
          padding: 3rem;
          text-align: center;
          background: #f9fafb;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .upload-zone:hover {
          background: #f3f4f6;
        }

        .upload-zone.drag-active {
          border-color: #2563eb;
          background: #eff6ff;
        }

        .file-input-hidden {
          display: none;
        }

        .upload-label {
          cursor: pointer;
          display: block;
        }

        .upload-icon {
          width: 64px;
          height: 64px;
          color: #9ca3af;
          margin: 0 auto 1rem;
        }

        .upload-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.5rem;
        }

        .upload-subtitle {
          font-size: 0.875rem;
          color: #6b7280;
        }

        /* File List */
        .file-list {
          margin-top: 1.5rem;
        }

        .file-list-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.75rem;
        }

        .file-items {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .file-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: #f9fafb;
          padding: 0.75rem 1rem;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .file-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .file-icon {
          width: 20px;
          height: 20px;
        }

        .file-icon-image {
          color: #3b82f6;
        }

        .file-icon-file {
          color: #6b7280;
        }

        .file-name {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .file-size {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .remove-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 0.25rem;
          transition: color 0.2s;
        }

        .remove-icon {
          width: 20px;
          height: 20px;
          color: #ef4444;
        }

        .remove-btn:hover .remove-icon {
          color: #dc2626;
        }

        /* Submit Button */
        .submit-btn {
          width: 100%;
          margin-top: 1.5rem;
          padding: 1rem 1.5rem;
          border-radius: 12px;
          font-weight: 600;
          font-size: 1rem;
          color: white;
          border: none;
          cursor: pointer;
          background: linear-gradient(135deg, #2563eb 0%, #9333ea 100%);
          box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
          transition: all 0.3s ease;
        }

        .submit-btn:hover:not(.disabled) {
          transform: scale(1.02);
          box-shadow: 0 15px 20px -3px rgba(37, 99, 235, 0.4);
        }

        .submit-btn.disabled {
          background: #9ca3af;
          cursor: not-allowed;
          transform: none;
        }

        .btn-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
        }

        .spinner {
          animation: spin 1s linear infinite;
          width: 20px;
          height: 20px;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Alert */
        .alert {
          border-radius: 12px;
          padding: 1rem;
          margin-bottom: 2rem;
          display: flex;
          gap: 0.75rem;
          align-items: flex-start;
        }

        .alert-error {
          background: #fef2f2;
          border: 1px solid #fecaca;
        }

        .alert-icon {
          width: 24px;
          height: 24px;
          color: #dc2626;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .alert-title {
          font-weight: 600;
          color: #7f1d1d;
          margin-bottom: 0.25rem;
        }

        .alert-message {
          color: #b91c1c;
        }

        /* Results Section */
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

        /* Summary Grid */
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

        .summary-item.full-width {
          grid-column: 1 / -1;
        }

        .summary-label {
          font-size: 0.875rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .summary-value {
          font-size: 1rem;
          font-weight: 500;
          color: #111827;
        }

        /* Verdict Box */
        .verdict-box {
          padding: 1.5rem;
          border-radius: 12px;
          text-align: center;
        }

        .verdict-eligible {
          background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
          border: 2px solid #10b981;
        }

        .verdict-review {
          background: linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%);
          border: 2px solid #f59e0b;
        }

        .verdict-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #111827;
          margin-bottom: 0.5rem;
        }

        .verdict-message {
          font-size: 1rem;
          color: #374151;
        }

        /* Financial Grid */
        .financial-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .financial-item {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          padding: 1rem;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .financial-item.highlight {
          background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
          border-color: #3b82f6;
        }

        .financial-label {
          font-size: 0.875rem;
          font-weight: 600;
          color: #6b7280;
        }

        .financial-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #111827;
        }

        .financial-total {
          color: #1f2937;
        }

        .financial-insurance {
          color: #2563eb;
        }

        .financial-copay {
          color: #f59e0b;
        }

        .financial-user {
          color: #dc2626;
        }

        /* Breakdown Table */
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

        .breakdown-header {
          background: #f9fafb;
          font-weight: 600;
          color: #374151;
          border-bottom: 2px solid #d1d5db;
        }

        .breakdown-row:hover {
          background: #f9fafb;
        }

        .breakdown-col {
          font-size: 0.875rem;
          color: #374151;
        }

        .breakdown-category {
          font-weight: 500;
          color: #111827;
        }

        .breakdown-allowed {
          color: #059669;
          font-weight: 600;
        }

        .breakdown-not-allowed {
          color: #dc2626;
          font-weight: 600;
        }

        /* Recommendations Box */
        .recommendations-box {
          margin-top: 1.5rem;
          padding: 1rem;
          background: #fef3c7;
          border: 1px solid #fcd34d;
          border-radius: 8px;
        }

        .recommendations-title {
          font-size: 1rem;
          font-weight: 600;
          color: #92400e;
          margin-bottom: 0.75rem;
        }

        .recommendations-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .recommendations-list li {
          padding: 0.5rem 0;
          padding-left: 1.5rem;
          position: relative;
          color: #78350f;
          font-size: 0.875rem;
        }

        .recommendations-list li:before {
          content: "→";
          position: absolute;
          left: 0;
          color: #f59e0b;
          font-weight: bold;
        }

        /* Notes Section */
        .notes-section {
          margin-bottom: 1.5rem;
        }

        .notes-section:last-child {
          margin-bottom: 0;
        }

        .notes-title {
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.75rem;
        }

        .notes-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .note-item {
          padding: 0.75rem 1rem;
          margin-bottom: 0.5rem;
          border-radius: 8px;
          font-size: 0.875rem;
          line-height: 1.5;
        }

        .note-reason {
          background: #fef2f2;
          border-left: 4px solid #ef4444;
          color: #991b1b;
        }

        .note-action {
          background: #eff6ff;
          border-left: 4px solid #3b82f6;
          color: #1e40af;
        }

        /* Classified Documents */
        .classified-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .classified-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
        }

        .classified-file {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex: 1;
        }

        .classified-icon {
          width: 20px;
          height: 20px;
          color: #6b7280;
        }

        .classified-filename {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .classified-type {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .type-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          background: #dbeafe;
          color: #1e40af;
        }

        .confidence-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 500;
          background: #f3f4f6;
          color: #6b7280;
        }

        /* Missing Documents */
        .doc-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .doc-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          border-radius: 8px;
        }

        .doc-item-missing {
          background: #ffedd5;
          border: 1px solid #fed7aa;
        }

        .doc-icon {
          width: 20px;
          height: 20px;
          color: #ea580c;
          flex-shrink: 0;
        }

        .doc-text {
          color: #1f2937;
        }

        .success-message {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem;
          background: #d1fae5;
          border: 1px solid #6ee7b7;
          border-radius: 8px;
        }

        .success-icon {
          width: 24px;
          height: 24px;
          color: #059669;
        }

        .success-text {
          color: #065f46;
          font-weight: 500;
        }

        /* Coverage Result */
        .code-block {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 1.5rem;
          overflow-x: auto;
        }

        .code-pre {
          font-size: 0.875rem;
          color: #1f2937;
          font-family: 'Courier New', monospace;
          white-space: pre-wrap;
          word-break: break-word;
          margin: 0;
        }

        /* Generated PDFs */
        .pdf-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .pdf-link {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem;
          background: linear-gradient(135deg, #d1fae5 0%, #dbeafe 100%);
          border: 1px solid #6ee7b7;
          border-radius: 12px;
          text-decoration: none;
          transition: all 0.3s ease;
        }

        .pdf-link:hover {
          border-color: #34d399;
          transform: translateY(-2px);
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .pdf-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .pdf-icon {
          width: 20px;
          height: 20px;
          color: #059669;
        }

        .pdf-name {
          font-weight: 500;
          color: #1f2937;
        }

        .download-icon {
          width: 20px;
          height: 20px;
          color: #059669;
          transition: transform 0.2s;
        }

        .pdf-link:hover .download-icon {
          transform: translateY(2px);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .insurance-container {
            padding: 1.5rem 1rem;
          }

          .header-title {
            font-size: 2rem;
          }

          .card {
            padding: 1.5rem;
          }

          .upload-zone {
            padding: 2rem 1rem;
          }
        }
      `}</style>
    </div>
  );
}