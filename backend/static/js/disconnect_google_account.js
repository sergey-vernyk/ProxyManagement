$(document).ready(() => {
    $("#google-disconnect").on("click", (event) => {
        event.preventDefault();
        const url = $("#google-disconnect").attr("href") || null;

        if (url !== null) {
            const disconnect = prompt("Are you sure for fully disconnecting from Google account? (Yes/No)");
            if (disconnect !== null) {
                if (disconnect.toLocaleLowerCase() === "yes") {
                    $.ajax({
                        url: url,
                        method: "POST",
                        success: (response, textStatus, xhr) => {
                            console.log("Disconnected");
                            window.location.reload();
                        },
                        error: (jqXHR, textStatus, errorThrown) => {
                            console.log(errorThrown);
                        }
                    })
                } else if (disconnect.toLocaleLowerCase() === "No") {
                    console.log("No");
                } else {
                    console.log("WTF?");
                }
            }
        }
    })
})