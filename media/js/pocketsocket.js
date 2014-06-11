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

function AddressException(message) {
    this.message = message;
    this.data = arg(arguments, 1, null);
    this.caption = arg(arguments, 2, this.message);
    this.name = "AddressException";

    this.toString = function(){
        return this.name + ':' + this.caption;
    }
}



methods = {
    retryLimit: 5,
    isocket: {
        start_connect_timer: function(){
            var socket  = arg(arguments, 0, null)
            var self    = this;

            if(!this.retryTimers)         this.retryTimers         = [];
            if(!this.retryTimers[socket]) this.retryTimers[socket] = {};
            console.log('retryTimer created')
            var rts = this.retryTimers[socket];
            rts.socket = socket;
            if(rts._connectAttempts > (this.retryLimit)) {
                stop_connect_timer(socket)
                console.log("socket fail after too many retry attempts", socket)
                return false;
            }

            if(!rts.timer){
                rts.timer = window.setInterval(function(){
                    if(!rts._connectAttempts) rts._connectAttempts = 0;
                    rts._connectAttempts += 1;

                    if(!socket || socket.readyState == 3) {
                        debugger

                        self.signal('socket', 'reconnect', rts)
                    } else {
                        self.stop_connect_timer(socket)
                    }

                }, 1000)
            }
        },
        send: function(m, v){
            /*
            sendToAll proxy
             */
            var s = this.sendToAll(m, v);
            return s;
        },
        stop_connect_timer:function(){
            var socket = arg(arguments, 0, null);
            if(this.retryTimers && this.retryTimers[socket])
                window.clearInterval(this.retryTimers[socket].timer);
        },
        sendTo: function(socket, str, val){
            /*
            Send a str to a socket

             */
            if(socket) {

                if( socket.connected ) {
                    var sent = socket.sendJson(str, val || {});
                    console.log('Message', str.length, sent)
                    return sent;
                } else {
                    console.log('Not Connected', socket)
                }

            } else {
                throw new AddressException('Socket does not exist', name);
            }

        },
        sendToAll: function(str, val){
            /*
            send message  to all connected.
            If in broadcast, all open sockets will be used.
            If the socket (or any broadcast socket) is disconnected,
            reconnect will be initiated and a queued message will be sent later
            */
            var str = arg(arguments, 0, null);
            if(!str) return false;

            var val = arg(arguments, 1, {});


            var _sents = []
            for(var socketName in this.__sockets) {
                var socket = this.__sockets[socketName];
                if(socket instanceof WebSocket) {
                    _sents.push(this.sendTo(socket, str, val) );
                }
            }

            return _sents;
        },
        signal: function(channel, eventName) {
            /*
            Signal is passed to method to be pushed into the
            websocket streams. This should be successful for broadcast and
            overflow.

            If the connection does not exist, a new connection will be
            created based on connection setup.

             */
            // send a signal to the server.
            var self    = this;
            var id      = null;
            var val     = arg(arguments, 2, undefined);
            var socketName = arg(arguments, 3, null);
            var sendStr = channel + '.' +  eventName;

            if(val && (!val instanceof Function)) {
                sendStr += '.' + val
            }

            // if val is function, special hook to use with ID.

            if(socketName == null){
                // send on every available socket.

                // check socket exist.

                if(this.connection.connectionType == 'broadcast') {
                    // Connect to every dead connection using the
                    // reconnect method on a socket.
                    // send all.
                    this.sendToAll(sendStr, val || {});
                }
                // if not connected, connect.

            } else {
                // if socket name exists/
                // send
                // if dead:
                //  reconnect, send later.
                this.sendTo(socketName, sendStr, val || {})
            }

            /*
            var c = this.connect('ws://127.0.0.1:8001', function(name, ev){
                if(name == 'open') {
                    // add pre hooks
                    for(var h in methods.webSocket.__data.prehooks) {
                        self.on.call(self, methods.webSocket.__data.prehooks[h])
                    }
                    id = this.send_json(sendStr, val || {});
                }
            })
             */

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

            var channel  = arg(arguments, 0, null);
            var cf1      = arg(arguments, 1, null);
            var cf2      = arg(arguments, 2, null);

            var callfunc = cf2;
            var socket   = this.__socket;
            var _d = methods.webSocket.__data;

            channels = [channel]

            if(typeof(cf1)  == 'string' && cf2 instanceof Function)  {
                channels.push(channel + '.' + cf1);
            }

            methods.webSocket.eventHook(channels, function(e, name, data){
                 if(cf1 instanceof Function && (!cf2)) {
                    cf1(e,name, data);
                } else if(typeof(cf1)  == 'string' && cf2 instanceof Function) {
                    if(name == cf1) {
                        console.log("Found channel hook for '" + channel + "' '" + name +"'")
                        cf2(e, data);
                    }
                }

            })

            /*

            if(!socket) {
                // store hooks for later.
                if(!_d.hasOwnProperty('prehooks') ) {  _d.prehooks = []; };
                _d.prehooks.push([channel, cf1, cf2]);
                return this
            }

            socket.eventHook(channel, function(name, ev) {
                if(cf2 == null && cf2 == name) {
                    socket.eventHook(channel, ev);

                    // Call single  message  hook.
                    // cf1(ev, ev.__event);
                } else {
                    if(name == cf1) cf2(ev.data, ev);
                }
            });
             */

            return this;
        },
        convertForConnect: function() {
            /*
            Pass data object to be parsed as connection data.
            Returned will be a pocket.socket ready object of connection.
            The returned Array can be used for setup() and connect()
             */
            var address = arg(arguments, 0, '127.0.0.1');
            var ports   = arg(arguments, 1, null);
            var a, p;

            if(address instanceof Array) {
                // List of ips, should have list of ports
                // [ '127.0.0.1', '127.0.0.2' ]
                a = address


            } else if(typeof(address) == 'string') {

                if(address.indexOf(':') > -1)  {
                    a = [ address.split(':')[0] ];
                    p = [ address.split(':')[1] ];
                } else {
                    a = [address];
                }
            } else if(typeof(address) == 'object') {
                var _a = [],
                    _p = [];

                for(var name in address) {
                    // Named pair
                    // Add ports to array, add addresses to array
                    _a.push(address[name][0] || address[name].ip);
                    _p.push(address[name][1] || address[name].port);
                }

                a = _a;
                p = _p;
            }

            if(ports instanceof Array) {
                if(!p) {
                    p = ports;
                } else {
                    // swap p to
                    p = ports.push(p);
                }
            } else if(typeof(ports) == 'string' && conType != null) {
                if(p) {
                    p.push(ports)
                } else {
                    p = [ports]
                }
            } else if(parseInt(ports)) {
                // type or argument mismatch
                p = [ports];
            }

            returnObject = {
                'addresses': a,
                'ports': p
            }

            return returnObject;
        },
        setup: function(){
            var address = arg(arguments, 0, '127.0.0.1');
            var ports   = arg(arguments, 1, null);
            var listType = arg(arguments, 2, null);
            var conType = arg(arguments, 3, null);

            // setup('127.0.0.1:8001')
            // setup('127.0.0.1:8001', 'broadcast')
            this.connection.empty()
            // sort other object.

            var connectionObject = this.convertForConnect(address, ports)
            var a = connectionObject.addresses;
            var p = connectionObject.ports;

            if(conType == null) {
                conType = 'broadcast';
            }

            this.connection.addresses = a;
            this.connection.ports = p;
            this.connection.connectionType = conType;
            this.connection.listType = listType
            //  ports is conType
            if(conType === false) {
                conType = 'mix'
                this.connect(this.connection.list(listType), listType, conType)
            }

            if(this.connection.isSetup()) {
                this.connection.connect = this.connect
            }

            return this.connection;
        },
        connection: {
            // Receive the next address from a created list.
            isSetup: function(){
                /* Has the library been setup and has at least one connection */
                if(this.addresses
                    && (this.addresses instanceof Array)
                    && this.addresses.length > 0) {
                        return true;
                };

                return false;
            },
            addToList: function(list, ip, port, name) {
                // Crate a connection element to be enumerated and
                // used for connections
                var o = {};
                if(ip && port) {
                    o.ip = ip;
                    o.port = port;
                    o.name = name || '';

                    o.toString = function(){
                        return this.ip + ':' + this.port;
                    }
                    list.push(o);
                }

                return o;
            },
            list: function(){
                var listType = arg(arguments, 0, this.listType || 'mix')
                /* Build the complete list of all connection types.
                As this is never exists. - Instead, the index counter
                used to provide the next permutation of the next() counter
                is reset and the lists are enumerated until all
                possible outcomes are created.
                If listType is  'mix'
                                'flat'
                Returned is an Array of objects
                [
                    {
                        ip: '127.0.0.1',
                        port: 8001
                    }
                ]
                */
                var _list =  [];
                for (var i = 0; i < this.addresses.length; i++) {
                    var a = this.addresses[i];
                    if(listType == 'mix') {
                        for (var j = 0; j < this.ports.length; j++) {
                            var p = this.ports[j];
                            this.addToList(_list, a, p)
                        };
                    } else if(listType == 'flat') {
                        if (this.addresses.length == this.ports.length) {
                            if(a && this.ports[i]) {
                                this.addToList(_list, a, this.ports[i])
                            }
                        } else if(this.addresses.ip && this.addresses.port) {

                            if(this.addresses.ip && this.addresses.port) {
                                this.addToList(_list, this.address.ip,
                                    this.address.port);
                            }
                        } else {
                            var s ='IP and Port Array are not the same length for "flat" enumeration.'
                            var d = {
                                'addresses': this.addresses,
                                'ports': this.ports,
                                'listType': listType
                            }

                            throw new AddressException(s, d);
                        }
                    }
                };
                _list.toArray = function(){
                    // Tidy output for flat view :)
                    // ['ip:port', ip:port]
                    var ra = [];
                    for (var i = 0; i < this.length; i++) {
                        ra.push( this[i].ip + ':' + this[i].port);
                    };
                    return ra;
                }

                return _list;
            },

            getNextOrFirst: function(list, index) {
                var l = (list instanceof Function)? list.call(this, index): list[0];

                if(l) {
                    var n = (list instanceof Function)? list.call(this, index+1): list[index+1];
                    if(n)
                        return [l, index+1];
                    else {
                        return [l, 0];
                    }

                } else {
                    return (list instanceof Function)? list.call(this, 0): list[0];
                    // return [l[0], 0]
                }
            },
            getPort: function(index) {
                /* Get a connection based on index or key/value pair key
                */
                if (this.ports[index])
                    return this.ports[index];
                return null;
            },
            getIp: function(index) {
                /* Get a connection based on index or key/value pair key
                */
                if (this.addresses && this.addresses[index])
                    return this.addresses[index];
                return null;
            },
            empty: function() {
                /* Remove all ip's and port's.
                Does not close the live connection. */
                this.ips = [];
                this.ports = [];
                this.addresses = [];
                return true;
            },
            on: function() {
                var v = pocket.socket.on.apply(this, arguments);
                 return v;
            }
        },
        connect: function(){
            /*
            Receives object list
            default is elements setup through connection.setup()
            Data passed will be implemented through the connection.setup()
            method.
            */
           debugger;
            var connections = arg(arguments, 0, null);

            if(typeof(connections) == 'string' &&
                arg(arguments,1, null) instanceof Function) {

            }
            // mix or overflow
            var listType = arg(arguments, 0, (this.connection)? this.connection.listType: this.listType);

            // Broadcast or overflow
            var connectionType = arg(arguments, 3, (this.connection)? this.connection.connectionType: this.connectionType);
             // Connect to every
            if(!connections) {
                connections = (this.connection)? this.connection.list(listType): this.list(listType)
            } else {
                throw new AddressException('Missing connections')
                // connections = this.setup(connections, listType, connectionType, false)
            }

            // check extra undefined connection
            //
            if(connectionType == 'broadcast') {
                // Connect to all.
                var open = [],
                    connected = [];

                // Create connections.
                connections.forEach(function(e,i,a){
                    // debugger;
                    pocket.socket.makeSocket(e, function(name, data){
                        if(name == 'open') {
                            open.push(data);
                            if(open.length == 2) {
                                pocket.socket.signal('socket', 'broadcast-all-connected', data.name)
                            }
                        }
                    })
                })
            }
        },
        makeSocket: function(){

            var u    = arguments[0];                 // url
            var c    = arguments[1] || function(){}; // callback
            var self = this;
            if(!self.__sockets) self.__sockets = {};

            var handler = function(name, data) {
                switch(name) {
                    case 'open':
                        //console.log("iSocket Connected");
                        self.stop_connect_timer(self.__sockets[u])
                        break;
                    case 'close':
                        //console.log("iSocket closed");
                        self.start_connect_timer(self.__sockets[u])
                        break;
                    case 'message':
                        //console.log("iSocket message", data);
                        break;
                    case 'error':
                        console.log("iSocket error");
                        self.start_connect_timer(self.__sockets[u])

                        break;
                }
                c.call(this, name, {
                    name: u,
                    socket: self.__sockets[u],
                    data: data
                })
            }

            this.__sockets[u] = methods.webSocket.eventHook('socket', handler).connect(u)

            return this.__sockets[u]
        }

    },
    webSocket: {
        __data: {},
        getActiveSocket: function(){
            // return an active webSocket.
            for(var socket in this.__data.sockets) {
                if(this.__data.sockets[socket].readyState == 1) {

                    return this.__data.sockets[socket];
                };
            }
            return false;
        },
        isConnected: function(){
            // 'Is the webSocket connected'
            // returns true/false
            return (this.getActiveSocket())? true: false;
        },
        socketString: function(url){
            // pass a url entity to be converted to a string for use
            // with the webSocket
            var _url = url;
            var secure = arg(arguments, 1, false);

            if(url.hasOwnProperty('ip') && url.hasOwnProperty('port')) {
                /*
                connect({
                    ip: '127.0.0.1',
                    port: 8001
                })
                 */
                _url = url.ip + ':' + url.port;

            } else if(url instanceof Array && url.length >= 2) {
                /*
                connect(['127.0.0.1', 8001])
                 */
                _url = url[0] + ':' + url[1];
            } else if(url instanceof Function) {
                /*
                connect(function(){
                    return '12.0.0.1:8001'
                })
                 */
                _url = url(this)
            }

            if(typeof(_url) == 'string') {
                var sli = _url.slice(0, 3);
                if(sli != 'ws:' && sli != 'wss') {
                    if(secure) {
                        return 'wss://' + _url;
                    }
                    return 'ws://' + _url;
                }
            } else {
                console.warn("Error with url", url, _url)
            }

            return _url
        },
        AugmentedWebSocket: function() {
            // new AugementedWebSocket(url)
            var uri = arg(arguments, 0, null);
            var socket = new WebSocket(uri)

            var reconnect = function reconnect() {
                socket.close()

                pocket.socket.websocket.close(socket)
                // reapply reconnect function
                socket = this.connect(uri, function(){
                    console.log("Socket reconnected", socket)
                })

            }

            var sendJson = function sendJson(message, data){
                return pocket.webSocket.sendJson(socket, message, data);
            }

            socket.uri = uri
            socket.connected = false;
            socket.sendJson = sendJson;
            socket.reconnect = reconnect;

            return socket
        },
        connect: function(){
            var uri = arg(arguments, 0, null);
            var success = arg(arguments, 1, function(){});
            var self = this;

            if(!uri) {
                // Should pick up first default.
                throw new AddressException('Cannot connect without URI')
            }
            // returns connected socket,
            if(!this.__data.sockets) {
                this.__data.sockets = [];
            }

            var _uri = this.socketString(uri);

            // Send out a connecting signal
            this.__callHook('socket', 'connecting', [uri, _uri]);

            // ws-URI = "ws:" "//" host [ ":" port ] path [ "?" query ]
            // wss-URI = "wss:" "//" host [ ":" port ] path [ "?" query ]
            var w  = new this.AugmentedWebSocket(_uri);

            this.__data.sockets.push(w);
            w.onopen = function(e) {
                success(e)
                // From AugmentedWebSocket
                w.connected=true;
                self.__callHook('socket', 'open', {
                    socket: w,
                    data: e,
                })
            };
            w.onclose = function(evt) {
                w.connected=false;
                self.__callHook('socket', 'close', evt)
            };
            w.onmessage = function(ev) {
                var json = null;

                try {
                    var json = JSON.parse(ev.data)
                } catch(e) {
                    json = false;
                }

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

                    self.__callHook(channel, eventName, json);
                } else {
                    self.__callHook('socket', 'message', ev);
                }


            };
            w.onerror = function(evt) {
                self.__callHook('socket', 'error', evt)
            };
            // add listener
            //  on listener handle, call all sub hooks.

            return w;
        },
        sendJson: function(){
            var socket = arg(arguments, 0, null)
            var message = arg(arguments, 1, null)
            var data = arg(arguments, 2, {})
            // send a message
            // returns the unique id of the message
            var o = {
                id: Math.random().toString(32),
                message: message,
                data: data
            };

            var json = JSON.stringify(o);

            if(socket) {
                socket.send(json);
                return o.id;
            } else {
                return false;
            }

        },
        close: function(socket){
            return socket.close()
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
            if(this.__data.hooks.hasOwnProperty(channel)) {

                for(var hookMethod in this.__data.hooks[channel]) {
                    var func = this.__data.hooks[channel][hookMethod];
                    if(func) {
                        func.call(this, eventName, eventData);
                    }
                }

            }

            for(var _eventName in this.__data.hooks) {
                if(_eventName == eventData.message) {

                    for (var i = 0; i < this.__data.hooks[_eventName].length; i++) {
                        var func = this.__data.hooks[_eventName][i];
                        if(func) {
                            func.call(this, _eventName, eventData);
                        }
                    };
                }
            }

            if( eventData.messageId in methods.webSocket.__data.hooks){
                var ef = methods.webSocket.__data.hooks[eventData.messageId]
                for(var func in ef) {

                    ef[func](eventData.data, eventData)
                }
                methods.webSocket.__data.hooks[eventData.messageId] = null;
                delete methods.webSocket.__data.hooks[eventData.messageId]
            }
        },

        eventHook: function(name, func) {
            // Pass a listener hook and a function to receive a signal
            // when called
            // add func to name stack object caller
            if(!(name instanceof Array) ) {
                name = [name]
            }

            for (var i = 0; i < name.length; i++) {
                var _name = name[i]

                if(!this.__data.hooks) {
                    this.__data.hooks = {};
                }

                if(!this.__data.hooks[_name]) {
                    this.__data.hooks[_name] = [];
                }

                this.__data.hooks[_name].push(func);

                return this;
            };
        }
    },
}



pocket = methods
pocket.socket = methods.isocket