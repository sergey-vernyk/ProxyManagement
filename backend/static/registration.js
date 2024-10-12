$(document).ready(() => {
    $("#google-oauth").on("click", () => {
        const googleHubAuthUrl = $("#registration-form").data("auth-url");
        const clientId = $("#registration-form").data("client-id");
        const redirectUri = $("#registration-form").data("redirect-uri");
        const state = $("#registration-form").data("state");
        const responseType = $("#registration-form").data("response-type")
        const accessType = $("#registration-form").data("access-type")
        const scope = $("#registration-form").data("scope")
        const grantedScopes = $("#registration-form").data("granted-scopes")

        const params = new URLSearchParams({
            client_id: clientId,
            redirect_uri: redirectUri,
            state: state,
            access_type: accessType,
            response_type: responseType,
            scope: scope,
            include_granted_scopes: grantedScopes,
        })
        // redirect the user to GitHub's OAuth authorization page
        window.location.href = `${googleHubAuthUrl}?${params}`;
    });

    $("#registration-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const enteredPassword = $("#password").val();
        const regUrl = $("#registration-form").data("reg-url");
        $("#password-error").text("");
        $("#email-error").text("");

        $.ajax({
            url: regUrl,
            method: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                email: enteredEmail,
                password: enteredPassword,
            }),
            success: (response, textStatus, xhr) => {
                // redirect to page with text about successful registration.
                const redirectUrl = response.redirect_url;
                window.location.href = redirectUrl;
            },
            error: (jqXHR, textStatus, errorThrown) => {
                if (jqXHR.status === 422) {
                    $("#password-error").text(`${jqXHR.responseJSON.detail[0].msg}.`);
                }

                if (jqXHR.status === 400) {
                    if (jqXHR.responseJSON.detail["email_invalid"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["email_invalid"])
                    }

                    if (jqXHR.responseJSON.detail["user_exists"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["user_exists"])
                    }
                }
            }
        });
    })
})