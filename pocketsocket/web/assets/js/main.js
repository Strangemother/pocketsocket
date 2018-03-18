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
    }

    , mounted() {
        this.connect()
    }

    , methods: {

        connect() {
            let p = this.address
            let ws = new WebSocket(p);
            ws.onmessage = this.socketMessage;
            ws.onopen = this.socketOpen;
            this.webSocket = ws;
        }

        , socketMessage(d){
            this.$emit('websocketData', d)
            //console.log(d);
            this.socketMessages.push({
                type: 'in'
                , data: d.data
            })

        }

        , socketOpen(d){
            console.log('open', d);
            this.connected = true
        }

        , sendMessage(){
            this.webSocket.send(this.message)
            this.socketMessages.push({
                type: 'out'
                , data: this.message
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
