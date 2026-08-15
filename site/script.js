function detectOperatingSystem() {
    const platform = navigator.userAgentData?.platform || navigator.platform || "";
    const userAgent = navigator.userAgent || "";
    const normalizedPlatform = platform.toLowerCase();
    const normalizedUserAgent = userAgent.toLowerCase();

    if (/android/.test(normalizedUserAgent)) {
        return "android";
    }

    if (/iphone|ipad|ipod/.test(normalizedUserAgent) ||
      (normalizedPlatform === "macintel" && navigator.maxTouchPoints > 1)) {
        return "ios";
    }

    if (/win/.test(normalizedPlatform) || /windows/.test(normalizedUserAgent)) {
        return "windows";
    }

    if (/mac/.test(normalizedPlatform) || /macintosh|mac os/.test(normalizedUserAgent)) {
        return "macosx";
    }

    if (/linux/.test(normalizedPlatform) || /linux/.test(normalizedUserAgent)) {
        return "linux";
    }

      return "unknown";
}

const themeToggle = document.querySelector("[data-theme-toggle]");
const root = document.documentElement;

function setTheme(theme) {
    const isLight = theme === "light";
    root.classList.toggle("light-theme", isLight);
    themeToggle.setAttribute("aria-pressed", String(isLight));
    themeToggle.textContent = isLight ? "Use dark mode" : "Use light mode";
    localStorage.setItem("pocketsocket-theme", theme);
}

const savedTheme = localStorage.getItem("pocketsocket-theme");
setTheme(savedTheme === "light" ? "light" : "dark");

themeToggle.addEventListener("click", () => {
    setTheme(root.classList.contains("light-theme") ? "dark" : "light");
});


async function detectArchitecture() {
    const userAgentData = navigator.userAgentData;

    if (userAgentData?.getHighEntropyValues) {
        const { architecture, bitness } = await userAgentData.getHighEntropyValues([
            "architecture",
            "bitness"
        ]);

        if (architecture === "arm" && bitness === "64") {
            return "arm64";
        }

        if (architecture === "x86" && bitness === "64") {
            return "amd64";
        }
    }

    const userAgent = navigator.userAgent.toLowerCase();
    if (/arm64|aarch64|armv8/.test(userAgent)) {
        return "arm64";
    }

    if (/x86_64|amd64|win64|x64/.test(userAgent)) {
        return "amd64";
    }

    return "unknown";
}


const { createApp, ref } = Vue

// https://github.com/Strangemother/pocketsocket-2/releases/download/
// v2.0.4/
// pocketsocket-cli-linux_arm64
const nameMap = {
    tag: 'v2.0.4'
    , host: 'https://github.com/Strangemother/pocketsocket'
    , urlFix: 'releases/download/'
    , appFix: 'pocketsocket-cli'
    , linux: {
        "amd64": "-linux_amd64",
        "arm64": "-linux_arm64",
    }
    , macosx: {
        "amd64": "-macosx_amd64",
        "arm64": "-macosx_arm64",
    }
    , windows: {
        "amd64": "-windows_amd64.exe",
    }
};

const buildUrl = function(os, arch) {
    const osMap = nameMap[os] || {};
    const suffix = osMap[arch];

    if (!suffix) {
        return "#";
    }

    return `${nameMap.host}/${nameMap.urlFix}${nameMap.tag}/${nameMap.appFix}${suffix}`;
}

createApp({
    setup() {
        const os = detectOperatingSystem();
        const downloadLink = ref("#");

        detectArchitecture().then((architecture) => {
            downloadLink.value = buildUrl(os, architecture);
        });

        return {
            nameMap,
            os,
            downloadLink,
            host: nameMap.host,
            socketAddress: ref('127.0.0.1:8090'),
            messages: ref([])
        };
    }
    , data() {
        return {
            isDownloadClicked: false,
            isRunClicked: false,
            isConnectedClicked: false,
            socketConnected: false,
        };
    }
    , methods: {
        getDownloadLink() {
            return this.downloadLink;
        }
        , testConnectClick(){
            let socket = this.ws = new WebSocket(`ws://${this.socketAddress}`)
            socket.addEventListener("open", () => {
                this.setConnected(true);
                this.addMessage("Connected to PocketSocket");
                // messageInput.focus();
            });
            socket.addEventListener("message", (event) => this.addMessage(event.data));
            socket.addEventListener("close", () => {
                socket = null;
                this.setConnected(false);
                this.addMessage("Disconnected");
            });
            socket.addEventListener("error", () => this.addMessage("Connection error"));
        }
        , setConnected(c) {
            console.log('connected', c)
            this.socketConnected = c
        }
        , addMessage(m) {
            // console.log('message', m)
            this.messages.push(m)
        }
        , downloadClicked() {
            this.isDownloadClicked = true;
            this.isRunClicked = false;
            this.isConnectedClicked = false
            console.log("Download button clicked");
            // You can add additional logic here if needed
        }
        , runClicked() {
            this.isRunClicked = true;
            this.isConnectedClicked = false
            this.isDownloadClicked = false;
            console.log("Run button clicked");
            // You can add additional logic here if needed
        }
        , connectClicked() {
            this.isConnectedClicked = true;
            this.isRunClicked = false;
            this.isDownloadClicked = false;
            console.log("connect button clicked");
        }
    }

}).mount('#app')