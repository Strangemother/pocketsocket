/*
Jasmine tests for JS API
 */
Object.prototype.equals = function(x)
{
  var p;
  for(p in this) {
      if(typeof(x[p])=='undefined') {return false;}
  }

  for(p in this) {
      if (this[p]) {
          switch(typeof(this[p])) {
              case 'object':
                  if (!this[p].equals(x[p])) { return false; } break;
              case 'function':
                  if (typeof(x[p])=='undefined' ||
                      (p != 'equals' && this[p].toString() != x[p].toString()))
                      return false;
                  break;
              default:
                  if (this[p] != x[p]) { return false; }
          }
      } else {
          if (x[p])
              return false;
      }
  }

  for(p in x) {
      if(typeof(this[p])=='undefined') {return false;}
  }

  return true;
}

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

        it('should mix enumerate with many combinations', function(){
            var _expected = ["a:1", "a:2", "a:3", "a:4", "a:5", 
                            "b:1", "b:2", "b:3", "b:4", "b:5", 
                            "c:1", "c:2", "c:3", "c:4", "c:5", 
                            "d:1", "d:2", "d:3", "d:4", "d:5", 
                            "e:1", "e:2", "e:3", "e:4", "e:5", 
                            "f:1", "f:2", "f:3", "f:4", "f:5", 
                            "g:1", "g:2", "g:3", "g:4", "g:5"]
            var reta = pocket.socket.setup(
                ['a', 'b', 'c', 'd','e', 'f', 'g'],
                ['1', '2', '3', '4', '5']
            ).list('mix').toArray()

            expect(reta.equals(_expected)).toBeTruthy()

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

    describe('can broadcast', function(){
        
        beforeEach(function() {
            pocket.socket.setup(['127.0.0.1', '43.137.157.170'], [8001], 'mix', 'broadcast');
        });

        it('should render 2 addresses', function(){
            // Retrieve a mix list
            var mix = pocket.socket.connection.list('mix').toArray()
            // pocket.socket.connection.list('mix').toString()
            expect(mix.length).toEqual(2)
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