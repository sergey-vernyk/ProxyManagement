import getCookie from "./get_cookies.js"


$(document).ready(() => {
    $("#logout-link").on("click", (event) => {
        event.preventDefault();
        const logoutUrl = $("#logout-link").attr("href");
        const csrfToken = getCookie("csrftoken");

        $.ajax({
            url: logoutUrl,
            method: "POST",
            headers: { "X-CSRFToken": csrfToken },
            success: (response, textStatus, xhr) => {
                const loginPageUrl = response.redirect_url;
                window.location.href = loginPageUrl;
            },
            error: (jqXHR, textStatus, errorThrown) => {
                console.log(errorThrown);
            }

        })
    });
})