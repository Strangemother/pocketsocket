var cleanData = []

function bootstrap() {

    var c = document.getElementById('canvas');
    var ctx = c.getContext('2d');
    ctx.globalalpha = 0.3;
    for(var i=0; i<1000; i++) {
        ctx.beginPath();
        var r = Math.floor(Math.random() * 256);
        var g = Math.floor(Math.random() * 256);
        var b = Math.floor(Math.random() * 256);
        ctx.strokeStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
        ctx.moveTo(Math.random()*200, Math.random()*200);
        ctx.lineTo(Math.random()*200, Math.random()*200);
        ctx.stroke();
    }
}


    // Stereo
var channels = 2;
var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
// Create an empty two second stereo buffer at the
// sample rate of the AudioContext
var frameCount = audioCtx.sampleRate * 1.0;

var myArrayBuffer = audioCtx.createBuffer(
        channels, frameCount, audioCtx.sampleRate);
var whitenoiseGenerator = function(){

    makeNoise = function(multiplier=1.1) {
        // Fill the buffer with white noise;
        //just random values between -1.0 and 1.0
        for (var channel = 0; channel < channels; channel++) {
            // This gives us the actual array that contains the data
            var nowBuffering = myArrayBuffer.getChannelData(channel);
            for (var i = 0; i < frameCount; i++) {
                // Math.random() is in [0; 1.0]
                // audio needs to be in [-1.0; 1.0]
                nowBuffering[i] = Math.random() * multiplier - 1;
            }
        }

        // Get an AudioBufferSourceNode.
        // This is the AudioNode to use when we want to play an AudioBuffer
        var source = audioCtx.createBufferSource();
        // set the buffer in the AudioBufferSourceNode
        source.buffer = myArrayBuffer;
        // connect the AudioBufferSourceNode to the
        // destination so we can hear the sound
        source.connect(audioCtx.destination);
        // start the source playing
        source.start();
    }

    return makeNoise
}

var whitenoise = whitenoiseGenerator()




var soundController = {
    speakerContext: new AudioContext()
}


soundController.playCache = function(cache) {
    while (cache.length) {
        var buffer = cache.shift();
        var source = soundController.speakerContext.createBufferSource();
        source.buffer = buffer;
        source.connect(soundController.speakerContext.destination);
        if (soundController.nextTime == 0) {
            // add a delay of 0.05 seconds
            soundController.nextTime = soundController.speakerContext.currentTime + 0.05;
        }
        source.start(soundController.nextTime);
        // schedule buffers to be played consecutively
        soundController.nextTime += source.buffer.duration;
    }
};


var startRecvStream = function() {
    soundController.nextTime = 0;

    var init = false;
    var audioCache = [];

    var process = function(data) {
        var array = new Float32Array(data);
        var buffer = soundController.speakerContext.createBuffer(1, 2048, 44100);
        buffer.copyToChannel(array, 0);

        audioCache.push(buffer);
        // make sure we put at least 5 chunks in the buffer before starting
        if ( (init === true)
             || (
                 (init === false)
                 && (audioCache.length > 5)
                 )
             ) {
            init = true;
            soundController.playCache(audioCache);
        }
    }

    return process
}





function getBase64Image(img) {
    // Create an empty canvas element
    //var canvas = document.createElement("canvas");
    let canvas = document.getElementById('canvas')
    canvas.width = img.width;
    canvas.height = img.height;

    // Copy the image contents to the canvas
    var ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);

    // Get the data-URL formatted image
    // Firefox supports PNG and JPEG. You could check img.src to
    // guess the original format, but be aware the using "image/jpg"
    // will re-encode the image.
    var dataURL = canvas.toDataURL("image/png");

    return dataURL.replace(/^data:image\/(png|jpg);base64,/, "");
}



var jsonFetchApp = new Vue({
    el: '#main'
    , data: {
        address: 'ws://localhost:8009'
        , basePath: ''
        , requests: []
        , selected: {}
        , message: localStorage.lastMessage
        , socketMessages: []
        , connected: false
        , indexItem: -1
        , index: 0
        , autoConnect: true
        , selectOffset: 0
        , values: []
    }

    , mounted() {
        if(this.autoConnect){
            this.connect()
        }
    }

    , methods: {

        connect() {
            let p = this.address
            let ws = new WebSocket(p);
            ws.onmessage = this.socketMessage;
            ws.onopen = this.socketOpen;
            ws.onclose = this.socketClose;
            this.webSocket = ws;
        }

        , disconnect(){
            this.webSocket.close()
            this.connected = false
        }

        , socketMessage(d){
            this.$emit('websocketData', d)
            //console.log(d);
            this.socketMessages.push({
                type: 'in'
                , data: d.data
                , index: this.index++
            })

        }

        , keyupHandle(e){
            this.selectOffset += 1
            if(this.selectOffset > this.values.length) {
                this.selectOffset = 0
            }

            this.message = this.values[this.values.length - this.selectOffset]
        }

        , keydownHandle(e){
            this.selectOffset -= 1
            if(this.selectOffset < 0) {
                this.selectOffset = 0
            }

            this.message = this.values[this.values.length - this.selectOffset]
        }

        , socketOpen(d){
            console.log('open', d);
            this.connected = true
        }

        ,socketClose(e){
            console.log('Closed')
            this.connected = false
        }

        , clearMessages(){
            this.socketMessages = []

        }

        , sendMessage(){
            this.webSocket.send(this.message)
            this.values.push(this.message)
            if(this.values.length>100) {
                this.values.splice(0, this.values.length - 100)
            }
            this.socketMessages.push({
                type: 'out'
                , data: this.message
                , index: this.index++
            })
            localStorage.lastMessage = this.message
            this.message = ''
        }


        , fetch(event, partial){
            let path = partial == undefined ? this.$refs.address.value: partial;
            console.log('path', path)
            let fullpath = `${this.basePath}${path}`
            $.get(fullpath, function(data){
                this.renderPath(path, data)
            }.bind(this))
        }

        , renderPath(path, data) {
            console.log('got', data)
            cleanData.push({path, data})
            let dataCopy = JSON.parse(JSON.stringify(data))
            this.requests.push({ path, dataCopy })

        }
    }
})
