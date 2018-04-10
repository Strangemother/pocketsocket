

    // Stereo
var channels = 2;
var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
// Create an empty two second stereo buffer at the
// sample rate of the AudioContext
var frameCount = audioCtx.sampleRate * 4.0;

var myArrayBuffer = audioCtx.createBuffer(
        channels, frameCount, audioCtx.sampleRate);

class Noise {

    constructor(){
        this.channels = 2
        this.seconds = 1
        this.multiplier = 1
        this.init()
    }

    init(channels, seconds){
        if(channels == undefined){
            channels = this.channels;
        }

        this.audioCtx = this.newContext()
        this.buffer = this.newBuffer(channels, seconds)
    }

    setSeconds(value) {
        this.seconds = value
        if(this.buffer != undefined) {
            this.buffer = this.newBuffer(this.channels, value)
        }
    }

    newContext(){
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        return audioCtx;
    }

    newBuffer(channels=2, seconds){
        let sr = this.sampleRate()
        return this.audioCtx.createBuffer(channels, this.frameCount(sr, seconds), sr);
    }

    frameCount(sampleRate, seconds){
        if(seconds == undefined) seconds = this.seconds
        if(sampleRate == undefined) sampleRate = this.sampleRate()
        return this.audioCtx.sampleRate * seconds
    }

    sampleRate(){
        return this.audioCtx.sampleRate
    }


    generator(typeFunc, multiplier, seconds){
        if(multiplier == undefined) {
            multiplier = this.multiplier
        }
        if(typeFunc == undefined){
            typeFunc = this.brown
        }

        if(seconds != undefined || seconds != this.seconds) {
            this.setSeconds(seconds)
        }

        if(this.buffer == undefined) {
            this.init()
        }
        // Fill the buffer with white noise;
        //just random values between -1.0 and 1.0
        for (var channel = 0; channel < this.channels; channel++) {
            // This gives us the actual array that contains the data
            var buffer = this.buffer.getChannelData(channel);
            typeFunc(buffer, frameCount, multiplier)
        }

        // Get an AudioBufferSourceNode.
        // This is the AudioNode to use when we want to play an AudioBuffer
        var source = this.audioCtx.createBufferSource();
        // set the buffer in the AudioBufferSourceNode
        source.buffer = this.buffer;
        // connect the AudioBufferSourceNode to the
        // destination so we can hear the sound
        source.connect(this.audioCtx.destination);

        return this.source = source
    }

    play(typeFunc, multiplier, count){

        if(this.source == undefined || typeFunc != undefined || count != undefined) {
            this.generator(typeFunc, multiplier, count)
        }

        this.source.start()
        this.source = undefined
    }

    playBuff(vals, multiplier, count){
        /*
            Play an array of values from as a buffer. The array values
            are cycled at the end, looping until the frame count of seconds is
            complete.

                noise.playBuff([.3,.5,.1,.3,.2,-.3,-.5,-.1,-.3,-.2,])

         */
        var func = function(buffer, _count, _multiplier){
            for (var i = 0; i < _count; i++) {
                // Math.random() is in [0; 1.0]
                // audio needs to be in [-1.0; 1.0]
                buffer[i] = vals[Math.round(i % vals.length)] * _multiplier - 1;
            }
        }

        this.play(func, multiplier, count)
    }

    playStepFunc(stepFunction, multiplier, count) {
        var func = function(buffer, _count, _multiplier){
            for (var i = 0; i < _count; i++) {
                // Math.random() is in [0; 1.0]
                // audio needs to be in [-1.0; 1.0]
                buffer[i] = stepFunction(buffer, _count, multiplier, i)
            }
        }

        this.play(func, multiplier, count)
    }

    toneStepFunc(buffer, count, multiplier, index){
        return [-.9, .4, -.8, .4, -.5, -.9][Math.round(index % 6)] * multiplier
    }

    white(buffer, count, multiplier=1.1){
        if(buffer==undefined) {
            return this.play(this.white, multiplier, count)
        }

        for (var i = 0; i < count; i++) {
            // Math.random() is in [0; 1.0]
            // audio needs to be in [-1.0; 1.0]
            buffer[i] = Math.random() * multiplier - 1;
        }
    }

    whoop(buffer, count, multiplier=-.3){
        if(buffer==undefined) {
            return this.play(this.whoop, multiplier, count)
        }
        let last = 0
        if(multiplier == undefined) multiplier = -.3
        for (var i = 0; i < count; i++) {
            // Math.random() is in [0; 1.0]
            // audio needs to be in [-1.0; 1.0]
            buffer[i] = Math.sin((i * last) * .00003) * multiplier
            last = i * .2
        }
    }

    brown(buffer, count, multiplier=1){
        if(buffer==undefined) {
            return this.play(this.brown, multiplier, count)
        }
        let lastOut = 0.0

        for (var i = 0; i < count; i++) {
            var white = Math.random() * 2 - 1;
            buffer[i] = (lastOut + (0.02 * white)) / 1.02;
            lastOut = buffer[i];
            buffer[i] *= 3.5; // (roughly) compensate for gain
        }
    }

    pink(buffer, count, multiplier=1){
        if(buffer==undefined) {
            return this.play(this.pink, multiplier, count)
        }

        let b0, b1, b2, b3, b4, b5, b6;
        b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0;

        for (var i = 0; i < count; i++) {
            var white = Math.random() * 2 - 1;
            b0 = 0.99886 * b0 + white * 0.0555179;
            b1 = 0.99332 * b1 + white * 0.0750759;
            b2 = 0.96900 * b2 + white * 0.1538520;
            b3 = 0.86650 * b3 + white * 0.3104856;
            b4 = 0.55000 * b4 + white * 0.5329522;
            b5 = -0.7616 * b5 - white * 0.0168980;
            buffer[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
            buffer[i] *= 0.11; // (roughly) compensate for gain
            b6 = white * 0.115926;
        }
    }

    oscillator(hertz=200){
        if(this.audioCtx == undefined) {
            this.init()
        }

        var oscillator = this.audioCtx.createOscillator();

        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(hertz, this.audioCtx.currentTime); // value in hertz
        oscillator.connect(this.audioCtx.destination);
        oscillator.start();
        return oscillator
    }

    wave(){
        var real = new Float32Array(2);
        var imag = new Float32Array(2);
        var ac = this.audioCtx
        var osc = ac.createOscillator();

        real[0] = -1;
        imag[0] = 1;
        real[1] = 1;
        imag[1] = 0;

        var wave = ac.createPeriodicWave(real, imag);

        osc.setPeriodicWave(wave);

        osc.connect(ac.destination);

        osc.start();
        osc.stop(2);
    }


    createAnalyser(){

        var analyser = this.audioCtx.createAnalyser();
        analyser.fftSize = 2048;
        var bufferLength = analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
        analyser.getByteTimeDomainData(this.dataArray);

        return this.analyser = analyser
    }

    createCanvas(){

        // Get a canvas defined with ID "oscilloscope"
        var canvas = document.getElementById("oscilloscope");
        var canvasCtx = canvas.getContext("2d");
        let analyser = this.analyser
        let dataArray = this.dataArray
        var bufferLength = analyser.frequencyBinCount;

        var draw = function draw() {
            let drawVisual = requestAnimationFrame(draw);

            //analyser.getByteTimeDomainData(dataArray);


            canvasCtx.fillStyle = 'rgb(200, 200, 200)';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

            canvasCtx.lineWidth = 2;
            canvasCtx.strokeStyle = 'rgb(0, 0, 0)';

            canvasCtx.beginPath();

            var sliceWidth = canvas.width * 1.0 / bufferLength;
            var x = 0;

            for (var i = 0; i < bufferLength; i++) {

                var v = dataArray[i] / 128.0;
                var y = v * canvas.height / 2;

                if (i === 0) {
                  canvasCtx.moveTo(x, y);
                } else {
                  canvasCtx.lineTo(x, y);
                }

                x += sliceWidth;

                canvasCtx.lineTo(canvas.width, canvas.height / 2);
                canvasCtx.stroke();
            }

            //draw();
        }
        this._drawFunc = draw
        return this.canvas = canvas
    }

}

var noise = new Noise();

var noiseGenerator = function(typeFunc){

    if(typeFunc == undefined){
        typeFunc = noise.brown
    }

    let makeNoise = function(multiplier) {
        // Fill the buffer with white noise;
        //just random values between -1.0 and 1.0
        for (var channel = 0; channel < channels; channel++) {
            // This gives us the actual array that contains the data
            var nowBuffering = myArrayBuffer.getChannelData(channel);
            typeFunc(nowBuffering, frameCount, multiplier)
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

        return source
    }

    return makeNoise
}

var whitenoise = noiseGenerator(noise.white)
var brownnoise = noiseGenerator(noise.brown)
var pinknoise = noiseGenerator(noise.pink)

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

$('body').append('<h2>Set stereo panning</h2><input class="panning-control" type="range" min="-1" max="1" step="0.1" value="0"><span class="panning-value">0</span><pre></pre>')
var audioPanner = function(source){
    var pre = document.querySelector('pre');
    var myScript = document.querySelector('script');

    var panControl = document.querySelector('.panning-control');
    var panValue = document.querySelector('.panning-value');

    pre.innerHTML = myScript.innerHTML;

    // Create a MediaElementAudioSourceNode
    // Feed the HTMLMediaElement into it
    //var source = audioCtx.createMediaElementSource(myAudio);

    // Create a stereo panner
    var panNode = audioCtx.createStereoPanner();

    // Event handler function to increase panning to the right and left
    // when the slider is moved

    panControl.oninput = function() {
      panNode.pan.value = panControl.value;
      panValue.innerHTML = panControl.value;
    }

    // connect the AudioBufferSourceNode to the gainNode
    // and the gainNode to the destination, so we can play the
    // music and adjust the panning using the controls
    source.connect(panNode);
    panNode.connect(audioCtx.destination);

}

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
