$(document).ready(() => {
    /**
     * Initializes the WebSocket connection and sets up event handlers.
     * This function also handles enabling or disabling the "Change IP" button
     * based on the validity of the link.
     */

    const linkIsValid = $("#link-stat").val();
    if (linkIsValid.toLowerCase() === "true") {
        $("#change-ip").attr("disabled", false);
    } else {
        $(".error").text("Link is invalid.");
    }

    /**
     * Creates a new WebSocket connection and sets up event handlers for
     * handling messages, errors, and connection closure.
     * @returns {WebSocket} The newly created WebSocket connection.
     */
    const createNewSocketConn = () => {
        const wsRootUrl = $("#ws-root-url").val();
        const socket = new WebSocket(wsRootUrl);

        /**
         * Event handler for when the WebSocket connection is opened.
         */
        socket.onopen = () => {
            console.log("WebSocket connection opened.");
        };

        /**
         * Event handler for receiving messages from the WebSocket server.
         * Processes incoming messages and updates the UI based on the content.
         * @param {MessageEvent} event - The event containing the message from the server.
         */
        socket.onmessage = (event) => {
            const response = event.data;
            console.log("Message from server:", response);
            const respIsJson = isJson(response);

            if (respIsJson) {
                const jsonData = JSON.parse(response);
                if (jsonData["error"] !== undefined) {
                    $(".error").text(jsonData.error);
                } else if (jsonData["oldIp"] !== undefined && jsonData["newIp"] !== undefined) {
                    $(".error").remove();
                    $("#old-ip").text(jsonData.oldIp);
                    $("#new-ip").text(jsonData.newIp);
                }

                $("#loading-spinner").hide();
            }
        };

        /**
         * Event handler for WebSocket errors.
         * Logs the error and hides the loading spinner.
         * @param {Event} error - The event containing the error details.
         */
        socket.onerror = (error) => {
            console.error("WebSocket error:", error);
            $("#loading-spinner").hide();
        };

        /**
         * Event handler for when the WebSocket connection is closed.
         * Logs the closure event.
         * @param {CloseEvent} event - The event containing the closure details.
         */
        socket.onclose = (event) => {
            console.log("WebSocket connection closed:", event);
        };

        return socket;
    };

    let ws = createNewSocketConn();

    /**
     * Event handler for the "Change IP" button click event.
     * Sends a message to the WebSocket server to start the IP change process.
     * Reopens the WebSocket connection if it is closed or closing.
     */
    $("#change-ip").on("click", () => {
        $("#loading-spinner").show();
        const modemId = $("#modem-id").val();

        if (ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
            ws = createNewSocketConn();
            ws.onopen = () => {
                console.log("WebSocket connection reopened.");
                if (modemId !== "None") {
                    ws.send(modemId);
                }
            };
        } else if (ws.readyState === WebSocket.OPEN) {
            if (modemId !== "None") {
                ws.send(modemId);
            }
        }
    });

    /**
     * Checks if a string is valid JSON.
     * @param {string} str - The string to check.
     * @returns {boolean} True if the string is a valid JSON; otherwise, false.
     */
    const isJson = (str) => {
        try {
            JSON.parse(str);
        } catch (e) {
            return false;
        }
        return true;
    };
});


