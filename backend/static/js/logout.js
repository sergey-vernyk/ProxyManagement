$(document).ready(() => {
    $("#logout-link").on("click", (event) => {
        event.preventDefault();
        const logoutUrl = $("#logout-link").attr("href");

        $.ajax({
            url: logoutUrl,
            method: "POST",
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