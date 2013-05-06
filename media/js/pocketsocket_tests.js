/*
Jasmine tests for JS API
 */

describe('pocketsocket', function(){
    var ps = pocket.socket;

    describe('can be setup with a string', function(){
        beforeEach(function() {
            ps.setup('127.0.0.1:8001');
        });
        
        it('should be setup', function(){
            
            expect(ps.connection.isSetup()).toBeTruthy();
        })

        it('should have address list length of 1', function(){
            expect(ps.connection.list().length).toEqual(1);
        }) 
    })


    describe('can be setup with a address, port', function(){
        var address = '127.0.0.1';
        var port = 8001
        // Connect to a single address
        beforeEach(function() {
            ps.setup(address, port);
        });

        it('should be setup', function(){

        })

        it('should have address list length of 1', function(){
             var flat = ps.connection.list('flat');
            console.log(ps.connection.addresses, ps.connection.ports, flat);
            expect(ps.connection.list().length).toEqual(1);
        }) 
    })


    describe('can be set up from double array set', function(){
        // double muliplexing
        var addresses = ['192.168.0.55', '127.0.0.1'];
        var ports     = [8001, 8009];

        beforeEach(function() {
            ps.setup(addresses, ports, 'broadcast');
        });
        
        it('should be set up', function(){
            expect(ps.connection.isSetup()).toBeTruthy();
        })

        it('should have an flat address list length of 2', function(){
            var flat = ps.connection.list('flat');
            console.log(ps.connection.addresses, ps.connection.ports, flat);
            expect(flat.length).toEqual(2);
        }) 
        
        it('should mix enumerate with the 4 combinations', function(){
            expect( ps.connection.list('mix').length ).toEqual(4);
        })

        // 192.168.0.55:8001
        // 192.168.0.55:8009
        // 127.0.0.1:8001
        // 127.0.0.1:8009

    })

    describe('can be setup with dictionary', function() {
        var addressPair = {
            'local': ['120.0.0.1', 8001],
            'dev': ['192.168.0.55', 8009]
        };
        
        beforeEach(function() {
            ps.setup(addressPair);
        });

        it('should be set up', function(){
            expect(ps.connection.isSetup()).toBeTruthy();
        })

        it('should have an flat address list length of 2', function(){
            var flat = ps.connection.list('flat');
            console.log(ps.connection.addresses, ps.connection.ports, flat);
            expect(flat.length).toEqual(2);
        }) 
        
        it('should mix enumerate with the 4 combinations', function(){
            expect( ps.connection.list('mix').length ).toEqual(4);
        })
    })
    /*

    // pairs



    // Connect to double multiplex
    ps.setup(addresses, ports);

    // Broadcast - Open all connections.
    // Message is sent to all live connections.
    ps.setup(addresses, ports, 'broadcast');
    //     M --> 192.168.0.55:8001
    //     M --> 192.168.0.55:8009
    //     M --> 127.0.0.1:8001
    //     M --> 127.0.0.1:8009

    // Overflow - Open the first available connection.
    // Message is sent through an open connection, 
    //  on failure - open a new connection and retry.
    //  The process will will loop forever.
    // E.g - Failure until node three succeeds
    ps.setup(addresses, ports, 'overflow');
    
    */
})