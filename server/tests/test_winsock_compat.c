#include "../src/pocketsocket_winsock_compat.h"

#undef far
#undef near

#pragma comment(lib, "ws2_32.lib")

int main(void) {
    fd_set sockets;
    FD_ZERO(&sockets);
    if (sockets.fd_count != 0) return 1;
    FD_SET((SOCKET)7, &sockets);
    FD_SET((SOCKET)9, &sockets);
    if (sockets.fd_count != 2) return 2;
    if (!FD_ISSET((SOCKET)7, &sockets)) return 3;
    if (!FD_ISSET((SOCKET)9, &sockets)) return 4;
    FD_CLR((SOCKET)7, &sockets);
    if (FD_ISSET((SOCKET)7, &sockets)) return 5;
    if (!FD_ISSET((SOCKET)9, &sockets)) return 6;
    FD_ZERO(&sockets);
    if (FD_ISSET((SOCKET)9, &sockets)) return 7;
    return 0;
}