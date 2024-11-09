$(document).ready(() => {
    const captchaVerifyUrl = $("#authentication-form").data("captcha-verify-url");
    const cloudflareSiteKey = $("#sitekey").val();
    const idempotencyKey = crypto.randomUUID();

    // make 'Signin' key disabled until success verification
    $("#signin").prop("disabled", true);

    // sends token from CF response to backend endpoint
    // in order to verify the token and proceed auth process
    const callback = (token) => {
        $.ajax({
            url: captchaVerifyUrl,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                token: token,
                idempotency_key: idempotencyKey
            }),
            success: (response) => {
                const verificationResult = response.message;
                if (verificationResult === "success") {
                    $("#signin").prop("disabled", false);
                }
            },
            error: (xhr, status, error) => {
                console.log("Verification error:", error);
            },
        });
    };

    window.onloadTurnstileCallback = () => {
        turnstile.execute("#cloudflare-captcha", {
            sitekey: cloudflareSiteKey,
            callback: callback,
            error: () => {
                console.log("Some error occurred.");
            },
            "expired-callback": () => {
                $("#signin").prop("disabled", true);
            },
            "timeout-callback": () => {
                $("#signin").prop("disabled", true);
            }
        });
    };

    $("#google-oauth").on("click", () => {
        const googleLoginUrl = $("#authentication-form").data("google-login-url");
        window.location.href = googleLoginUrl;
    });

    $("#authentication-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const enteredPassword = $("#password").val();
        const basicLoginUrl = $("#authentication-form").data("basic-login-url");
        $("#password-error").text("");
        $("#email-error").text("");

        $.ajax({
            url: basicLoginUrl,
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data: new URLSearchParams({
                "email": enteredEmail,
                "password": enteredPassword,
            }).toString(),
            success: (response, textStatus, xhr) => {
                // Redirect the user after the cookie is set
                window.location.href = response.redirect_url;
            },
            error: (jqXHR, textStatus, errorThrown) => {
                if (jqXHR.status === 422) {
                    $("#password-error").text(`${jqXHR.responseJSON.detail[0].msg}.`);
                }

                if (jqXHR.status === 400) {
                    if (jqXHR.responseJSON.detail["email_invalid"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["email_invalid"])
                    }

                    if (jqXHR.responseJSON.detail["incorrect_email_or_password"] !== undefined) {
                        $("#password-error").text(jqXHR.responseJSON.detail["incorrect_email_or_password"])
                    }
                }

                if (jqXHR.status === 404) {
                    if (jqXHR.responseJSON.detail["user_not_exists"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["user_not_exists"])
                    }
                }
            }
        });
    })
});
