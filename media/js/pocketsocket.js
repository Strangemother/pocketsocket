function arg(_a, ia, def, returnArray) {
    var v = null

    // if ia is an array, find the
    // first correct definition
    if (ia.constructor  == Array) {
        for(var i=0; i<ia.length; i++) {
            if(_a[ia[i]] || _a[ia[i]] === false ){
                v = _a[ia[i]];
                break;
            }
        }
    }
    else {
        if(_a[ia] || _a[ia] === false ) v = _a[ia];
    }

    if( (v == null) && (def != undefined) ) {
        v = def
    }

    if(returnArray){
        return [v, ia[i]]
    }
    else
    {
        return v
    }
}

methods = {
    isocket: {
        start_timer: function(){
            // reconnect
            var self = this;

            if(self._connectAttempts > 5) {
                window.clearInterval(self.t)
                return false;
            }
            if(!self.t){

                self.t = window.setInterval(function(){
                    if(!self._connectAttempts) {
                        self._connectAttempts = 0;
                    }
                    self._connectAttempts += 1;

                    if(!self.__socket) {
                        self.signal('connect', self._connectAttempts)
                    } else {
                        self.stop_timer()
                    }
                }, 1000)
            }
        },

        stop_timer:function(){
            window.clearInterval(self.t);
        },

        signal: function(channel, eventName) {

            // send a signal to the server.
            var self    = this;
            var id      = null;
            var val     = arg(arguments, 2, undefined);
            var sendStr = channel + '.' +  eventName;

            if(val && (!val instanceof Function)) {
                sendStr += '.' + val
            }

            // if val is function, special hook to use with ID.
            console.log('Signal called');

            if(!this.__socket) {
                var c = this.connect('ws://127.0.0.1:8001', function(name, ev){
                    if(name == 'open') {
                        // add pre hooks
                        for(var h in methods.websocket.__data.prehooks) {
                            self.on.call(self, methods.websocket.__data.prehooks[h])
                        }
                        id = this.send_json(sendStr, val || {});
                    }
                })
                // console.log( c )
            } else {
                id = this.__socket.send_json(sendStr, val || {});
            }

            if(val instanceof Function) {
                // Message with the same ID has been returned.
                this.on(id, function(data, ev){
                    // call ID Hook
                    val(data, ev)
                })
            }

        },
        on: function(){
            // two methods to call
            
            // on('socket', function(data, event))
            //  // Channel in data object.
            
            // on('socket', 'name', function(data, event))
            //  // Data is the object sent from the signal.
            console.log("On called")

            var channel  = arg(arguments, 0, null);
            var cf1      = arg(arguments, 1, null);
            var cf2      = arg(arguments, 2, null);
            var callfunc = cf2;
            var socket   = this.__socket;

            if(!socket) {
                // store hooks for later.
                var _d = methods.websocket.__data;
                if(!_d.hasOwnProperty('prehooks') ) {  _d.prehooks = []; };
                _d.prehooks.push([channel, cf1, cf2]);
                return this
            }

            socket.eventHook(channel, function(name, ev) {
                if(cf2 == null) {
                    socket.eventHook(channel, cf1);
                    // Call single  message  hook.
                    cf1(ev, ev.__event);
                } else {
                    if(name == cf1) cf2(name, ev);
                }
            });

            return this;
        },
        connect: function(){
            
            var u    = arguments[0];                 // url
            var c    = arguments[1] || function(){}; // callback
            var self = this;

            console.log("Connect")
            var handler = function(name, data) {
                switch(name) {
                    case 'open':
                        console.log("iSocket Connected");
                        self.stop_timer()
                        break;
                    case 'close':
                        console.log("iSocket closed");
                        self.__socket = null;
                        self.start_timer()
                        break;
                    case 'message':
                        // console.log("iSocket message", data);
                        break;
                    case 'error':
                        console.log("iSocket error");
                        self.start_timer()

                        break;
                }
                c.call(this, name, data)
            }

            this.__socket = methods.websocket.eventHook('socket', handler).connect(u)

            return this.__socket
        }

    },
    websocket: {
        __data: {},
        getActiveSocket: function(){
            // return an active websocket.
            for(var socket in this.__data.sockets) {
                if(this.__data.sockets[socket].readyState == 1) {

                    return this.__data.sockets[socket];
                };
            }
            return false;
        },
        isConnected: function(){
            // 'Is the websocket connected'
            // returns true/false
            return (this.getActiveSocket())? true: false;
        },
        connect: function(url){
            // returns connected socket,
            if(!this.__data.sockets) {
                this.__data.sockets = [];
            }

            var w  = new WebSocket(url);
            this.__data.sockets.push(w);
            var self = this;
            w.onopen = function(e) {
                self.__callHook('socket', 'open', e)
            };
            w.onclose = function(evt) {
                self.__callHook('socket', 'close', evt)
            };
            w.onmessage = function(ev) {
                var json = null;

                try {
                    var json = JSON.parse(ev.data)
                } catch(e) {
                    json = false;
                }
                
                console.log("json:", json)

                if(!json) {
                    self.__callHook('socket', 'message', ev)
                    return
                }

                json.__event = ev;

                //  detect and apply a message
                if(json.hasOwnProperty('socket') ){

                    self.__callHook('socket', json.socket, json);

                } else if(json.hasOwnProperty('message')) {
                    // sent from pocketsocket
                    var channel = json.message.split('.')[0];
                    var eventName = json.message.split('.')[1];
                    var data = json.data;
                    
                    json.__channel = channel;
                    json.__eventName = eventName;
                    json.__event = ev;

                    self.__callHook('socket', 'message', json);
                } else {
                    self.__callHook('socket', 'message', ev);
                }


            };
            w.onerror = function(evt) {
                self.__callHook('socket', 'error', evt)
            };
            // add listener
            //  on listener handle, call all sub hooks.

            return this;
        },
        send_json: function(){
            var message = arg(arguments, 0, null)
            var data = arg(arguments, 1, {})            
            // send a message
            // returns the unique id of the message
            var o = {
                id: Math.random().toString(32),
                message: message,
                data: data
            };

            var json = JSON.stringify(o);
            this.send(json);
            return o.id;
        },
        send: function(d){
            // Send content to the active socket.
            var ws = this.getActiveSocket()
            if(ws) {
                ws.send(d);
            }

        },
        __callHook: function(channel, eventName, eventData){
            // call all function hooking channel.
            // eventName and eventData are passed to the called function.
            // console.log(channel, eventName, eventData);
            if(this.__data.hooks.hasOwnProperty(channel)) {
                for(var hookMethod in this.__data.hooks[channel]) {
                    var func = this.__data.hooks[channel][hookMethod];
                    if(func) {
                        func.call(this, eventName, eventData);
                    }
                }
            }

            if( eventData.messageId in methods.websocket.__data.hooks){
                var ef = methods.websocket.__data.hooks[eventData.messageId]
                for(var func in ef) {

                    ef[func](eventData.data, eventData)
                }
                methods.websocket.__data.hooks[eventData.messageId] = null;
                delete methods.websocket.__data.hooks[eventData.messageId]
            }
        },

        eventHook: function(name, func) {
            // Pass a listener hook and a function to receive a signal
            // when called
            // add func to name stack object caller
            if(!this.__data.hooks) {
                this.__data.hooks = {};
            }

            if(!this.__data.hooks[name]) {
                this.__data.hooks[name] = [];
            }

            this.__data.hooks[name].push(func);

            return this;
        }
    },
}

pocket = methods
pocket.socket = methods.isocket