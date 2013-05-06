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

function AddresseException(message) {
    this.message = message;
    this.data = arg(arguments, 1, null);
    this.caption = arg(arguments, 2, this.message);
    this.name = "AddressesMistchException";

    this.toString = function(){
        return this.name + ':' + this.caption;
    }
}

methods = {
    isocket: {
        start_connect_timer: function(){
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
                        self.stop_connect_timer()
                    }
                }, 1000)
            }
        },

        stop_connect_timer:function(){
            window.clearInterval(this.t);
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
                if(cf2 == null && cf2 == name) {
                    console.log("Found channel hook for '" + channel + "' '" + name +"'")
                    socket.eventHook(channel, ev);
                    
                    // Call single  message  hook.
                    // cf1(ev, ev.__event);
                } else {
                    if(name == cf1) cf2(ev.data, ev);
                }
            });

            return this;
        },
        setup: function(){
            var address = arg(arguments, 0, '127.0.0.1');
            var ports   = arg(arguments, 1, null);
            var listType = arg(arguments, 2, null);
            var conType = arg(arguments, 3, null);

            // setup('127.0.0.1:8001')
            // setup('127.0.0.1:8001', 'broadcast')
            if(this.connection.isSetup()) {
                this.connection.empty()
            } 
            // sort other object.
            
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

            debugger;

            if(conType == null) {
                conType = 'broadcast';
            }
            
            this.connection.addresses = a;
            this.connection.ports = p;
            this.connection.connectionType = conType;
            //  ports is conType
            if(conType === false) {
                conType = 'mix'
                this.connect(this.connection.list(listType), listType, conType)
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
                            _list.push({
                                'ip': a,
                                'port': p
                            })
                        };
                    } else if(listType == 'flat') {
                    
                        if (this.addresses.length == this.ports.length) {
                    
                            _list.push({
                                'ip': a,
                                'port': this.ports[i]
                            })
                        } else if(this.addresses.ip && this.addresses.port) {

                            _list.push({
                                'ip': this.address.ip,
                                'port': this.address.port
                            })
                        } else {
                            var s ='IP and Port Array are not the same length for "flat" enumeration.'
                            var d = {
                                'addresses': this.addresses,
                                'ports': this.ports,
                                'listType': listType
                            }

                            throw new AddresseException(s, d);
                        }
                    } 
                };

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
            }
        },
        connect: function(){
            /*
            Receives object list
            default is elements setup through connection.setup()
            Data passed will be implemented through the connection.setup()
            method.
            */
            var connections = arg(arguments, 0, null);

            // mix or overflow
            var listType = arg(arguments, 0, this.connection.listType);

            // Broadcast or overflow
            var connectionType = arg(arguments, 3, this.connection.connectionType);
             // Connect to every 
            if(!connections) {
                connections = this.connection.list(listType)
            } else {
                debugger;
                // connections = this.setup(connections, listType, connectionType, false)
            }
            
            if(connectionType == 'broadcast') {
                // Connect to all.
                for(var connection in connections) {
                    debugger
                }
            }
        },
        _connect: function(){
            
            var u    = arguments[0];                 // url
            var c    = arguments[1] || function(){}; // callback
            var self = this;

            var handler = function(name, data) {
                switch(name) {
                    case 'open':
                        console.log("iSocket Connected");
                        self.stop_connect_timer()
                        break;
                    case 'close':
                        console.log("iSocket closed");
                        self.__socket = null;
                        self.start_connect_timer()
                        break;
                    case 'message':
                        console.log("iSocket message", data);
                        break;
                    case 'error':
                        console.log("iSocket error");
                        self.start_connect_timer()

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

            console.log("Event hook added to channel", name);
            this.__data.hooks[name].push(func);

            return this;
        }
    },
}

pocket = methods
pocket.socket = methods.isocket