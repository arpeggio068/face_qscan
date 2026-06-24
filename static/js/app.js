// app.js

let lastEventId = 0;

function loadStatus() {
    $.ajax({
        url: "/api/status",
        method: "GET",
        dataType: "json",
        cache: false,
        success: function (res) {
            updateUI(res);
        },
        error: function () {
            $("#stateText").text("เชื่อมต่อระบบไม่ได้");
            $("#messageText").text("กรุณาตรวจสอบ server");
        }
    });
}

function updateUI(res) {

    $("#stateText").text(getStateText(res.state));
    $("#messageText").text(res.message || "");

    // =========================
    // แสดงจำนวนคิว
    // =========================
    if (res.max_queue !== undefined) {
        $("#maxQueueText").text(res.max_queue);
    } else {
        $("#maxQueueText").text("-");
    }

    if (res.used_queue !== undefined) {
        $("#usedQueueText").text(res.used_queue);
    } else {
        $("#usedQueueText").text("-");
    }

    // =========================
    // แสดงคิวของผู้ใช้งาน
    // =========================
    if (res.queue_no) {
        $("#queueNo").text(res.queue_no);
    } else {
        $("#queueNo").text("---");
    }

    // =========================
    // det score
    // =========================
    if (res.det_score) {
        $("#detScore").text(
            "det_score: " +
            Number(res.det_score).toFixed(3)
        );
    } else {
        $("#detScore").text("det_score: -");
    }

    updateCameraPreview(res);

    checkAndSpeakQueue(res);
}

function checkAndSpeakQueue(res) {

    if (
        res.state === "QUEUE_FULL" &&
        res.last_event_id &&
        res.last_event_id !== lastEventId
    ) {
        lastEventId = res.last_event_id;

        speakFull();

        return;
    }

    if (
        res.state === "CAPTURED" &&
        res.queue_no &&
        res.last_event_id &&
        res.last_event_id !== lastEventId
    ) {
        lastEventId = res.last_event_id;

        speakQueue(res.queue_no);
    }
}

function updateCameraPreview(res) {

    const img = $("#cameraPreview");

    if (res.video_enabled === true) {

        img.show();

        const currentSrc = img.attr("src");

        if (!currentSrc || currentSrc === "") {
            img.attr(
                "src",
                "/video_feed?t=" + Date.now()
            );
        }

        $(".camera-title").text(
            "กล้องสแกนใบหน้า"
        );

        return;
    }

    img.hide();
    img.attr("src", "");

    let waitText = "กรุณารอสักครู่";

    if (res.wait_remaining) {
        waitText =
            "กรุณารอ " +
            res.wait_remaining +
            " วินาที";
    }

    $(".camera-title").text(waitText);
}

function getStateText(state) {

    switch (state) {

        case "STARTUP":
            return "กำลังเริ่มระบบ";

        case "READY":
            return "พร้อมสแกน";

        case "SCANNING":
            return "กำลังสแกน";

        case "CAPTURED":
            return "สแกนสำเร็จ";

        case "WAITING":
            return "กรุณารอสักครู่";

        case "MULTI_FACE":
            return "พบหลายใบหน้า";

        case "ERROR":
            return "ระบบผิดพลาด";

        case "QUEUE_FULL":
            return "คิวเต็ม";

        default:
            return "ระบบพร้อมทำงาน";
    }
}

$(document).ready(function () {

    $("#enableVoiceBtn").on("click", function () {

        enableVoice();

        $(this).text("เปิดเสียงแล้ว");
        $(this).prop("disabled", true);

        $(this).removeClass("btn-primary");
        $(this).addClass("btn-success");
    });

    loadStatus();

    setInterval(loadStatus, 1000);
});