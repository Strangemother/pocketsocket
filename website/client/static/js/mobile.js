
var x = 0, y = 0,
    vx = 0, vy = 0,
    ax = 0, ay = 0;

var sphere = document.getElementById("sphere");
var _send = false;

if (window.DeviceMotionEvent != undefined) {

    window.ondevicemotion = function(e) {
        if(event.accelerationIncludingGravity.x != null) {
            _send = true;
        }
        ax = parseInt(event.accelerationIncludingGravity.x * -5);
        ay = parseInt(event.accelerationIncludingGravity.y * -5);
    }

    setInterval(function(){
        var landscapeOrientation = window.innerWidth/window.innerHeight > 1;
        if ( landscapeOrientation) {
            vx = vx + ay;
            vy = vy + ax;
        } else {
            vy = vy - ay;
            vx = vx + ax;
        };

        vx = vx * 0.98;
        vy = vy * 0.98;
        y = parseInt(y + vy / 50);
        x = parseInt(x + vx / 50);

        boundingBoxCheck();

        sphere.style.top = y + "px";
        sphere.style.left = x + "px";

    }, 25);

    setInterval(function(){
        if(_send) {
            jsonFetchApp.webSocket.send(JSON.stringify({ type: 'accelerometer', coords: [ax, ay] }))
        }
    }, 1000)

    jsonFetchApp.$on('websocketData', function(d){
        let v = {};
        try {
            v = JSON.parse(d.data);
        } catch (e){};

        if(v.type == 'accelerometer') {
            ax = v.coords[0] * 5;
            ay = v.coords[1] * 5;
        }
    })

}


function boundingBoxCheck(){
    if (x<0) { x = 0; vx = -vx; }
    if (y<0) { y = 0; vy = -vy; }
    if (x>document.documentElement.clientWidth-20) {
        x = document.documentElement.clientWidth-20; vx = -vx;
    }
    if (y>document.documentElement.clientHeight-20) {
        y = document.documentElement.clientHeight-20; vy = -vy;
    }

}
