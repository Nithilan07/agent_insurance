import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  fetchClaims,
  upsertClaim,
  setClaimStatus,
} from "../redux/claimListSlice";
import { Link } from "react-router-dom";
import { openClaimsListSocket } from "../utils/ws";

export default function Dashboard() {
  const dispatch = useDispatch();
  const { items, status, error } = useSelector((s) => s.claimsList);

  useEffect(() => {
    dispatch(fetchClaims());

    const ws = openClaimsListSocket((msg) => {
      if (msg.claimId) {
        dispatch(upsertClaim(msg));
        if (msg.status) {
          dispatch(
            setClaimStatus({
              claimId: msg.claimId,
              status: msg.status,
              stage: msg.stage,
            }),
          );
        }
      } else if (msg.id) {
        dispatch(upsertClaim(msg));
      }
    });

    return () => {
      try {
        ws && ws.close();
      } catch (_) {}
    };
  }, [dispatch]);

  return (
    <div className="dash-root">
      <div className="dash-header">
        <h2>🧾 Claims Dashboard</h2>
        <p>Live updates from processing pipeline</p>
      </div>

      {status === "loading" && (
        <div className="loading-banner">Loading claims...</div>
      )}

      {status === "failed" && (
        <div className="error-banner">Error: {error}</div>
      )}

      <div className="dash-table-wrapper">
        <table className="dash-table">
          <thead>
            <tr>
              <th>Claim ID</th>
              <th>Name</th>
              <th>Insurance ID</th>
              <th>Policy</th>
              <th>Status</th>
              <th>Stage</th>
              <th>Submitted</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id} className="dash-row">
                <td className="claim-id">{c.id}</td>
                <td>{c.name}</td>
                <td>{c.insuranceId}</td>
                <td>{c.policyName}</td>

                <td>
                  <span className={`badge badge-${c.status}`}>{c.status}</span>
                </td>

                <td>
                  {c.currentStage ? (
                    <span className="stage-chip">{c.currentStage}</span>
                  ) : (
                    "-"
                  )}
                </td>

                <td>{new Date(c.createdAt).toLocaleString()}</td>

                <td>
                  <Link to={`/claim/${c.id}`} className="view-btn">
                    View →
                  </Link>
                </td>
              </tr>
            ))}

            {items.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-state">
                  No claims found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* CSS */}
      <style jsx>{`
        .dash-root {
          padding: 24px;
          max-width: 1300px;
          margin: 0 auto;
          animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: none;
          }
        }

        .dash-header h2 {
          margin: 0;
          font-size: 28px;
          font-weight: 700;
          color: #111827;
        }

        .dash-header p {
          color: #6b7280;
          margin-top: 4px;
          font-size: 15px;
        }

        .loading-banner,
        .error-banner {
          padding: 12px 16px;
          margin-top: 16px;
          border-radius: 8px;
          font-weight: 600;
        }

        .loading-banner {
          background: #dbeafe;
          color: #1e3a8a;
        }

        .error-banner {
          background: #fee2e2;
          color: #991b1b;
        }

        .dash-table-wrapper {
          margin-top: 20px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
          overflow-x: auto;
        }

        .dash-table {
          width: 100%;
          border-collapse: collapse;
          min-width: 1000px;
        }

        thead tr {
          background: #f3f4f6;
        }

        th {
          text-align: left;
          padding: 14px;
          font-size: 14px;
          color: #374151;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .dash-row:hover {
          background: #f9fafb;
          transition: 0.2s;
        }

        td {
          padding: 14px;
          font-size: 15px;
          color: #1f2937;
          border-bottom: 1px solid #eee;
        }

        .claim-id {
          font-family: monospace;
          color: #4b5563;
          font-weight: 600;
        }

        /* Status badges */
        .badge {
          padding: 6px 10px;
          border-radius: 8px;
          font-size: 12px;
          font-weight: 600;
          text-transform: capitalize;
        }

        .badge-completed {
          background: #d1fae5;
          color: #065f46;
        }

        .badge-rejected {
          background: #fee2e2;
          color: #991b1b;
        }

        .badge-pending,
        .badge-processing {
          background: #fef3c7;
          color: #92400e;
        }

        /* Stage chip */
        .stage-chip {
          display: inline-block;
          padding: 6px 12px;
          background: #e0f2fe;
          color: #1e40af;
          border-radius: 20px;
          font-weight: 600;
          font-size: 12px;
        }

        /* View button */
        .view-btn {
          text-decoration: none;
          color: #2563eb;
          font-weight: 700;
          padding: 6px 10px;
          border-radius: 8px;
          transition: 0.2s ease;
        }

        .view-btn:hover {
          background: #e0f2fe;
        }

        .empty-state {
          padding: 24px;
          text-align: center;
          color: #6b7280;
          font-size: 16px;
        }
      `}</style>
    </div>
  );
}
