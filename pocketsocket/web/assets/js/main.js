var cleanData = []


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
