// speech.js

let voiceEnabled = false;

function enableVoice() {
    voiceEnabled = true;

    playAudio("/static/mp3/open.mp3");
}

function isVoiceEnabled() {
    return voiceEnabled === true;
}

function playAudio(src) {
    const audio = new Audio(src);
    audio.play();
}

async function playAudioPromise(src) {
    return new Promise((resolve) => {
        const audio = new Audio(src);

        audio.onended = resolve;

        audio.play().catch(() => {
            resolve();
        });
    });
}

async function speakQueue(queueNo) {

    if (!queueNo || queueNo === "---") {
        return;
    }

    if (!isVoiceEnabled()) {
        console.log("ยังไม่ได้เปิดระบบเสียง");
        return;
    }

    const digits = String(queueNo).split("");

    await playAudioPromise("/static/mp3/intro.mp3");

    for (const d of digits) {
        await playAudioPromise(`/static/mp3/${d}.mp3`);
    }

    await playAudioPromise("/static/mp3/outro.mp3");
}

async function speakFull() {
    if (!isVoiceEnabled()) {
        console.log("ยังไม่ได้เปิดระบบเสียง");
        return;
    }

    await playAudioPromise("/static/mp3/full.mp3");
}