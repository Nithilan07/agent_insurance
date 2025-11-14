import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

const API_ROOT = "http://localhost:8000";

export const fetchClaimById = createAsyncThunk("claim/fetchById", async (id) => {
    const res = await fetch(`${API_ROOT}/claims/${id}`);
    if (!res.ok) throw new Error("Claim not found");
    return res.json();
});

const claimDetailsSlice = createSlice({
    name: "claimDetails",
    initialState: {
        id: null,
        submittingUser: null,  // flutter submitted fields
        aiExtracted: null,     // process result
        status: "idle",
        error: null,
    },
    reducers: {
        applyClaimUpdate(state, action) {
            const payload = action.payload;
            if (payload.claimId || payload.id) {
                state.id = payload.claimId || payload.id;
            }
            // payload may contain stage/status/result
            if (payload.stage || payload.status) {
                state.status = payload.status || state.status;
            }
            if (payload.result) {
                // attach result to aiExtracted
                state.aiExtracted = payload.result;
            }
            // if backend provides summary fields directly
            if (payload.summary) {
                state.aiExtracted = payload.summary;
            }
            if (payload.submitted) {
                state.submittingUser = payload.submitted;
            }
        },
        setSubmittingUser(state, action) {
            state.submittingUser = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchClaimById.pending, (state) => {
                state.status = "loading";
            })
            .addCase(fetchClaimById.fulfilled, (state, action) => {
                state.status = "succeeded";
                const data = action.payload;
                state.id = data.id;
                // submitted user fields from DB (from create_claim)
                state.submittingUser = {
                    name: data.name,
                    insuranceId: data.insuranceId,
                    policyName: data.policyName,
                    createdAt: data.createdAt,
                };
                state.aiExtracted = data.result || null;
                state.status = data.status || "idle";
            })
            .addCase(fetchClaimById.rejected, (state, action) => {
                state.status = "failed";
                state.error = action.error.message;
            });
    },
});

export const { applyClaimUpdate, setSubmittingUser } = claimDetailsSlice.actions;
export default claimDetailsSlice.reducer;
