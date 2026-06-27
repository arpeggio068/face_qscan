// app.js

let lastEventId = 0;

function formatThaiDateWithWeekday(thDate) {

    if (!thDate) return "-";

    const parts = thDate.split("/");

    if (parts.length !== 3) return thDate;

    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10);
    const thaiYear = parseInt(parts[2], 10);

    const christianYear = thaiYear - 543;

    const date = new Date(christianYear, month - 1, day);

    let weekday = "";

    switch (date.getDay()) {
        case 0:
            weekday = "วันอาทิตย์";
            break;
        case 1:
            weekday = "วันจันทร์";
            break;
        case 2:
            weekday = "วันอังคาร";
            break;
        case 3:
            weekday = "วันพุธ";
            break;
        case 4:
            weekday = "วันพฤหัสบดี";
            break;
        case 5:
            weekday = "วันศุกร์";
            break;
        case 6:
            weekday = "วันเสาร์";
            break;
    }

    return `${weekday} ที่ ${thDate}`;
}

function loadStatus() {
    $.ajax({
        url: "/api/status",
        method: "GET",
        dataType: "json",
        cache: false,
        success: function (res) {

            console.log("========== /api/status ==========");
            console.log(res);
            console.log("checked_at =", res.checked_at);
            console.log("api_state =", res.api_state);

            updateUI(res);
        },
        error: function (xhr, status, error) {

            console.log("AJAX ERROR");
            console.log(status);
            console.log(error);

            $("#stateText").text("เชื่อมต่อระบบไม่ได้");
            $("#messageText").text("กรุณาตรวจสอบ server");
        }
    });
}



function updateUI(res) {

    console.log("queue_date_display =", res.queue_date_display);
    console.log("max_queue =", res.max_queue);
    

    $("#stateText").text(getStateText(res.state));
    $("#messageText").text(res.message || "");

    // =========================
    // แสดงสถานะ API
    // =========================

    if (res.api_state === "online") {
        $("#apiStateIcon").text("🟢");
    } else {
        $("#apiStateIcon").text("🔴");
    }

    // =========================
    // แสดงวันที่คิว
    // =========================
    
    if (res.queue_date_display) {
        $("#queueDateText").text(
            formatThaiDateWithWeekday(res.queue_date_display)
        );
    } else {
        $("#queueDateText").text("-");
    }

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

    setInterval(loadStatus, 2000);
});