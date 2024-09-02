$(document).ready(() => {
    const compareUrl = $("#otp-form").data("url");
    const repeatCompareUrl = $("#otp-form").data("repeat-url");
    const token = $("#token").val();
    const uid = $("#uid").val();

    /**
     * Event listener for the dynamically created "Get new code" link.
     * It triggers an AJAX POST request to generate a new OTP code, 
     * resets the input field, and clears any existing error messages.
     *
     * @param {Object} event - The event object for the click event.
     */
    $("#otp-message").on("click", "#repeat-create-otp", (event) => {
        event.preventDefault();
        $("#otp-message").text("").removeClass("error");
        $("#repeat-create-otp").remove();
        $("#otp-input").val("");

        $.ajax({
            url: repeatCompareUrl,
            method: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                token: token,
                uid: uid,
            }),
            success: (response, textStatus, xhr) => {
                console.log(response);
                $("#otp-message").text("Check your email for incoming message with the new code.");
            },
            error: (jqXHR, textStatus, errorThrown) => {
                console.log(errorThrown);
                console.log(jqXHR);
            }
        });
    });

    /**
     * Event listener for the OTP form submission.
     * It prevents the default form submission, clears any existing messages, 
     * and triggers the compareCodes function if an OTP is entered.
     *
     * @param {Object} event - The event object for the submit event.
     */
    $("#otp-form").on("submit", (event) => {
        event.preventDefault();
        const enteredOtp = $("#otp-input").val();

        $("#otp-message").text("");
        if (enteredOtp) {
            compareCodes(compareUrl, enteredOtp, token, uid);
        }
    });

    /**
     * Sends a POST request to the provided URL to compare the entered OTP with the server-stored OTP.
     * Updates the OTP message area with the result of the comparison. If an error occurs, 
     * an option to request a new OTP is provided.
     *
     * @param {string} url - The URL to send the OTP comparison request to.
     * @param {string} enteredOtp - The OTP entered by the user.
     * @param {string} token - The token associated with the user session.
     * @param {string} uid - The unique identifier of the user.
     */
    const compareCodes = (url, enteredOtp, token, uid) => {
        $.ajax({
            url: url,
            method: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                entered_otp: enteredOtp,
                token: token,
                uid: uid,
            }),
            success: (response, textStatus, xhr) => {
                $("#otp-message").text(response["success"]).addClass("success").removeClass("error");
            },
            error: (jqXHR, textStatus, errorThrown) => {
                $("#otp-message").text(jqXHR.responseJSON["error"]).addClass("error").removeClass("success");
                $("#otp-message").append('<br><a href="#" id="repeat-create-otp">Get new code</a>');
            }
        });
    };
});

