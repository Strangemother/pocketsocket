#ifndef POCKETSOCKET_WINSOCK_COMPAT_H
#define POCKETSOCKET_WINSOCK_COMPAT_H

#include <winsock2.h>

static __inline void pocketsocket_fd_set(SOCKET socket, fd_set *set) {
    FD_SET(socket, set);
}

static __inline void pocketsocket_fd_clr(SOCKET socket, fd_set *set) {
    FD_CLR(socket, set);
}

static __inline void pocketsocket_fd_zero(fd_set *set) {
    FD_ZERO(set);
}

static __inline int pocketsocket_fd_isset(SOCKET socket, fd_set *set) {
    return FD_ISSET(socket, set);
}

#undef FD_SET
#undef FD_CLR
#undef FD_ZERO
#undef FD_ISSET
#define FD_SET(socket, set) pocketsocket_fd_set((socket), (set))
#define FD_CLR(socket, set) pocketsocket_fd_clr((socket), (set))
#define FD_ZERO(set) pocketsocket_fd_zero((set))
#define FD_ISSET(socket, set) pocketsocket_fd_isset((socket), (set))

#endif