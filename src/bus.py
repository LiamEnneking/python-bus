# -*- python -*-
'''
MIT/X Consortium License

Copyright © 2015  Mattias Andrée <maandree@member.fsf.org>

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
'''


class Bus:
    '''
    Message broadcasting interprocess communication
    '''
    
    
    RDONLY = 1
    '''
    Open the bus for reading only
    '''

    WRONLY = 0
    '''
    Open the bus for writing only
    '''
    
    RDWR = 0
    '''
    Open the bus for both reading and writing only
    '''
    
    EXCL = 2
    '''
    Fail to create bus if its file already exists
    '''
    
    INTR = 4
    '''
    Fail if interrupted
    '''
    
    NOWAIT = 1
    '''
    Function shall fail with `os.errno.EAGAIN`
    if the it would block and this flag is used
    '''
    
    
    def __init__(self, pathname : str = None):
        '''
        Constructor
        
        @param  pathname:str  The pathname of the bus, `None` if `create` should select a random pathname
        '''
        self.pathname = pathname
        self.bus = None
    
    
    def __del__(self):
        '''
        Destructor
        '''
        self.close()
    
    
    def create(self, flags : int = 0) -> str:
        '''
        Create the bus
        
        @param   flags:or_flag  `Bus.EXCL` (if the pathname is not `None`) to fail if the file
                                already exists, otherwise if the file exists, nothing will happen;
                                `Bus.INTR` to fail if interrupted
        @return  :str           The pathname of the bus
        '''
        from native_bus import bus_create_wrapped
        (self.pathname, e) = bus_create_wrapped(self.pathname, flags)
        if self.pathname is None:
            raise self.__oserror(e)
        return self.pathname
    
    
    def unlink(self):
        '''
        Remove the bus
        '''
        from native_bus import bus_unlink_wrapped
        (r, e) = bus_unlink_wrapped(self.pathname)
        if r == -1:
            raise self.__oserror(e)
    
    
    def open(self, flags : int = 0):
        '''
        Open an existing bus
        
        @param  flags:int  `Bus.RDONLY`, `Bus.WRONLY` or `Bus.RDWR`, the value must not be negative
        '''
        from native_bus import bus_close_wrapped, bus_allocate, bus_open_wrapped
        if self.bus is not None:
            (r, e) = bus_close_wrapped(self.bus)
            if r == -1:
                raise self.__oserror(e)
        else:
            (self.bus, e) = bus_allocate()
            if self.bus == 0:
                raise self.__oserror(e)
        (r, e) = bus_open_wrapped(self.bus, self.pathname, flags)
        if r == -1:
            raise self.__oserror(e)
    
    
    def close(self):
        '''
        Close the bus
        '''
        try:
            from native_bus import bus_close_wrapped, bus_deallocate
        except:
            return
        if self.bus is not None:
            (r, e) = bus_close_wrapped(self.bus)
            if r == -1:
                raise self.__oserror(e)
            bus_deallocate(self.bus)
            self.bus = None
    
    
    def write(self, message : str, flags : int = 0):
        '''
        Broadcast a message a bus
        
        @param  message:str  The message to write, may not be longer than 2047 bytes
                             after UTF-8 encoding
        @param  flags:int    `Bus.NOWAIT` if the function shall fail with `os.errno.EAGAIN`
                             if there is another process attempting to broadcast on the bus
        '''
        from native_bus import bus_write_wrapped
        (r, e) = bus_write_wrapped(self.bus, message, flags)
        if r == -1:
            raise self.__oserror(e)
    
    
    def read(self, callback : callable, user_data = None):
        '''
        Listen (in a loop, forever) for new message on a bus
        
        @param   callback  Function to call when a message is received, the
                           input parameters will be the read message and
                           `user_data` from the function's [`Bus.read`] parameter
                           with the same name. The message must have been parsed
                           or copied when `callback` returns as it may be over
                           overridden after that time. `callback` should
                           return either of the the values:
                             0:  stop listening
                             1:  continue listening
                             -1:  an error has occurred
                           However, the function [`Bus.read`] will invoke
                           `callback` with `message` set to `None` one time
                           directly after it has started listening on the bus.
                           This is to the the program now it can safely continue
                           with any action that requires that the programs is
                           listening on the bus.
                           NB! The received message will not be decoded from UTF-8
        @param  user_data  See description of `callback`
        '''
        from native_bus import bus_read_wrapped
        if bus_read_wrapped(self.bus, callback, user_data) == -1:
            raise self.__oserror()
    
    
    def poll_start(self):
        '''
        Announce that the thread is listening on the bus.
        This is required so the will does not miss any
        messages due to race conditions. Additionally,
        not calling this function will cause the bus the
        misbehave, is `Bus.poll` is written to expect
        this function to have been called.
        '''
        from native_bus import bus_poll_start_wrapped
        (r, e) = bus_poll_start_wrapped(self.bus)
        if r == -1:
            raise self.__oserror(e)
    
    
    def poll_stop(self):
        '''
        Announce that the thread has stopped listening on the bus.
        This is required so that the thread does not cause others
        to wait indefinitely.
        '''
        from native_bus import bus_poll_stop_wrapped
        (r, e) = bus_poll_stop_wrapped(self.bus)
        if r == -1:
            raise self.__oserror(e)
    
    
    def poll(self, flags : int = 0) -> bytes:
        '''
        Wait for a message to be broadcasted on the bus.
        The caller should make a copy of the received message,
        without freeing the original copy, and parse it in a
        separate thread. When the new thread has started be
        started, the caller of this function should then
        either call `Bus.poll` again or `Bus.poll_stop`.
        
        @param   flags:int  `Bus.NOWAIT` if the bus should fail with `os.errno.EAGAIN`
                            if there isn't already a message available on the bus
        @return  :bytes     The received message
                            NB! The received message will not be decoded from UTF-8
        '''
        from native_bus import bus_poll_wrapped
        (message, e) = bus_poll_wrapped(self.bus, flags)
        if message is None:
            raise self.__oserror(e)
        return message
    
    
    def chown(self, owner = None, group = None):
        '''
        Change the ownership of a bus
        
        `os.stat` can be used of the bus's associated file to get the bus's ownership
        
        @param  owner:int|str?      The user ID or username of the bus's new owner,
                                    if `None`, keep current
        @param  group:int|str|...?  The group ID or groupname of the bus's new group,
                                    if `None`, keep current, `...` to use the owner's group
        '''
        from native_bus import bus_chown_wrapped
        if (owner is None) or (group is None):
            from os import stat
            attr = stat(self.pathname)
            if owner is None:  owner = attr.st_uid
            if group is None:  group = attr.st_gid
        if isinstance(owner, str):
            import pwd
            owner = pwd.getpwnam(owner).pw_uid
        if isinstance(group, str):
            import grp
            group = grp.getgrnam(group).gr_gid
        elif group is ...:
            import pwd
            group = pwd.getpwuid(owner).pw_gid
        (r, e) = bus_chown_wrapped(self.pathname, owner, group)
        if r == -1:
            raise self.__oserror(e)
    
    
    def chmod(self, mode : int, mask : int = None):
        '''
        Change the permissions for a bus
        
        `os.stat` can be used of the bus's associated file to get the bus's permissions
        
        @param  mode:int   The permissions of the bus, any permission for a user implies
                           full permissions for that user, except only the owner may
                           edit the bus's associated file
        @param  mask:int?  Bits to clear before setting the bits in `mode`, if `None`,
                           all bits are cleared
        '''
        from native_bus import bus_chmod_wrapped
        if mask is not None:
            from os import stat
            current = stat(self.pathname).st_mode
            if current & 0o700:  current |= 0o700
            if current &  0o70:  current |=  0o70
            if current &   0o7:  current |=   0o7
            if mask & 0o700:  mask |= 0o700
            if mask &  0o70:  mask |=  0o70
            if mask &   0o7:  mask |=   0o7
            current &= ~mask
            mode |= current
        (r, e) = bus_chmod_wrapped(self.pathname, mode)
        if r == -1:
            raise self.__oserror(e)
    
    
    def __oserror(self, err : int):
        '''
        Create an OSError
        
        @param   err:int   The value of errno
        @return  :OSError  The OS error
        '''
        import os
        err = OSError(err, os.strerror(err))
        if err.errno == os.errno.ENOENT:
            err.filename = self.pathname
        return err

