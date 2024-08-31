$(document).ready(() => {
    $("#otp-form").on("submit", (event) => {
        event.preventDefault();

        $("#otp-message").text("");

        const enteredOtp = $("#otp-input").val();
        const url = $("#otp-form").data("url");
        const token = $("#token").val();
        const uid = $("#uid").val();

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
                $("#otp-message").text(response["success"]).addClass("success").removeClass("error");;
            },
            error: (jqXHR, textStatus, errorThrown) => {
                $("#otp-message").text(jqXHR.responseJSON["error"]).addClass("error").removeClass("success");
            }
        })
    });
});