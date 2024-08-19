$(document).ready(() => {
    const token = $("#token").val();
    const hashedValue = $("#hashed-value").val();

    if (!token || !hashedValue) {
        $("#messages").text("Token or hashed value is missing in the URL.");
        return;
    }

    const createNewSocketConn = () => {
        const wsRootUrl = $("#ws-root-url").val();
        const socket = new WebSocket(`${wsRootUrl}${token}/${hashedValue}`);

        socket.onopen = () => {
            console.log("WebSocket connection opened.");
        };

        socket.onmessage = function (event) {
            console.log("Message from server:", event.data);
            const response = JSON.parse(event.data);

            $("#loading-spinner").hide(); // Hide spinner after receiving response

            if (response.error) {
                alert(response.error);
            } else {
                $("#old-ip").text(response.old_ip);
                $("#new-ip").text(response.new_ip);
            }
        };

        socket.onerror = function (error) {
            console.error("WebSocket error:", error);
            $("#loading-spinner").hide(); // Hide spinner in case of error
        };

        socket.onclose = function (event) {
            console.log("WebSocket connection closed:", event);
        };

        return socket;
    }

    let ws = createNewSocketConn();

    $("#change-ip").on("click", () => {
        $("#loading-spinner").show(); // Show spinner when button is clicked

        if (ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
            ws = createNewSocketConn();
            ws.onopen = () => {
                console.log("WebSocket connection reopened.");
                ws.send("start");
            };
        } else if (ws.readyState === WebSocket.OPEN) {
            ws.send("start");
        }
    });
});


