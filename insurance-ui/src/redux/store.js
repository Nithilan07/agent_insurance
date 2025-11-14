import { configureStore } from "@reduxjs/toolkit";
import claimsListReducer from "./claimListSlice.js";
import claimDetailsReducer from "./claimDetailsSlice.js";

export const store = configureStore({
    reducer: {
        claimsList: claimsListReducer,
        claimDetails: claimDetailsReducer,
    },
});
