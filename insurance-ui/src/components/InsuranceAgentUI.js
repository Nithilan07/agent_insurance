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
      const res = await fetch("http://localhost:8000/process", {
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
            {/* Missing Documents */}
            <div className="card">
              <div className="section-header">
                <div className="section-icon section-icon-orange">
                  <AlertCircle className="section-icon-svg" />
                </div>
                <h2 className="section-title">Missing Documents</h2>
              </div>
              
              {result.missing_documents && result.missing_documents.length > 0 ? (
                <div className="doc-list">
                  {result.missing_documents.map((doc, index) => (
                    <div key={index} className="doc-item doc-item-missing">
                      <XCircle className="doc-icon" />
                      <span className="doc-text">{doc}</span>
                    </div>
                  ))}
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

            {/* Coverage Result */}
            <div className="card">
              <div className="section-header">
                <div className="section-icon section-icon-blue">
                  <CheckCircle className="section-icon-svg" />
                </div>
                <h2 className="section-title">Coverage Analysis</h2>
              </div>
              
              <div className="code-block">
                <pre className="code-pre">
                  {JSON.stringify(result.coverage_result, null, 2)}
                </pre>
              </div>
            </div>

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
                      href={`http://localhost:8000${url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="pdf-link"
                    >
                      <div className="pdf-info">
                        <FileText className="pdf-icon" />
                        <span className="pdf-name">{name}</span>
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

        .section-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #111827;
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