$(document).ready(() => {
    const deleteAccountUrl = $("#delete-account").attr("href");

    $("#delete-account").on("click", (event) => {
        event.preventDefault();
        const deleteAccount = prompt("Are you sure for deleting your account? (Yes/No)");
        if (deleteAccount.toLocaleLowerCase() === "yes") {
            $.ajax({
                url: deleteAccountUrl,
                method: "DELETE",
                success: (response, textStatus, xhr) => {
                    window.location.href = response.redirect_url;
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

    })
})