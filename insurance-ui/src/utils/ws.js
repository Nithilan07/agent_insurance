const WS_ROOT = "ws://localhost:8000";

function createReconnectWebSocket(url, onMessage) {
    let ws = new WebSocket(url);
    let shouldReconnect = true;

    const connect = () => {
        ws = new WebSocket(url);

        ws.onopen = () => console.log("[WS] Connected:", url);

        ws.onmessage = (evt) => {
            try {
                const data = JSON.parse(evt.data);
                onMessage && onMessage(data);
            } catch (e) {
                console.warn("[WS] parse error", e);
            }
        };

        ws.onclose = () => {
            console.warn("[WS] Closed:", url);
            if (shouldReconnect) {
                console.log("[WS] Reconnecting in 1s...");
                setTimeout(connect, 1000);
            }
        };

        ws.onerror = (err) => {
            console.error("[WS] Error:", err);
            ws.close();
        };
    };

    connect();

    return {
        close: () => {
            shouldReconnect = false;
            ws.close();
        }
    };
}

export function openClaimsListSocket(onMessage) {
    return createReconnectWebSocket(`${WS_ROOT}/ws/claims`, onMessage);
}

export function openClaimDetailSocket(claimId, onMessage) {
    if (!claimId) return;
    return createReconnectWebSocket(`${WS_ROOT}/ws/claims/${claimId}`, onMessage);
}
