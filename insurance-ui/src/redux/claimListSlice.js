import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";

const API_ROOT = "http://localhost:8000";

export const fetchClaims = createAsyncThunk("claims/fetchAll", async () => {
    const res = await fetch(`${API_ROOT}/claims`);
    if (!res.ok) throw new Error("Failed to load claims");
    return res.json();
});

const claimsListSlice = createSlice({
    name: "claimsList",
    initialState: {
        items: [],
        status: "idle",
        error: null,
    },
    reducers: {
        upsertClaim(state, action) {
            const incoming = action.payload;
            const idx = state.items.findIndex((c) => c.id === incoming.claimId || c.id === incoming.id);
            const claimObj = {
                id: incoming.claimId || incoming.id,
                name: incoming.name || incoming.patient_name || "Unknown",
                insuranceId: incoming.insuranceId || incoming.policy_number || "",
                policyName: incoming.policyName || incoming.policy_name || "",
                status: incoming.status || incoming.stage || "pending",
                currentStage: incoming.currentStage || incoming.stage || "",
                createdAt: incoming.createdAt || new Date().toISOString(),
            };
            if (idx === -1) {
                state.items.unshift(claimObj);
            } else {
                state.items[idx] = { ...state.items[idx], ...claimObj };
            }
        },
        setClaimStatus(state, action) {
            const { claimId, status, stage } = action.payload;
            const idx = state.items.findIndex((c) => c.id === claimId);
            if (idx !== -1) {
                state.items[idx].status = status || state.items[idx].status;
                if (stage) state.items[idx].currentStage = stage;
            }
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchClaims.pending, (state) => {
                state.status = "loading";
            })
            .addCase(fetchClaims.fulfilled, (state, action) => {
                state.status = "succeeded";
                state.items = action.payload;
            })
            .addCase(fetchClaims.rejected, (state, action) => {
                state.status = "failed";
                state.error = action.error.message;
            });
    },
});

export const { upsertClaim, setClaimStatus } = claimsListSlice.actions;
export default claimsListSlice.reducer;
