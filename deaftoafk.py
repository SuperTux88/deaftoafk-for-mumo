#!/usr/bin/env python
# -*- coding: utf-8
# Last edited 2011-07-23
# Version 0.0.3

# Copyright (C) 2011 Stefan Hacker <dd0t@users.sourceforge.net>
# Copyright (C) 2011 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# Antirec is based on the scripts onjoin.py, idlemove.py and seen.py
# (made by dd0t) from the Mumble Moderator project , available at
# http://gitorious.org/mumble-scripts/mumo
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:

# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# `AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#
# deaftoafk.py
# This module moves self deafened users into the afk channel and moves them back
# into their previous channel when they undeaf themselfes.
#

from mumo_module import (commaSeperatedIntegers,
                         MumoModule)
import pickle
import re

class deaftoafk(MumoModule):
    default_config = {'deaftoafk':(
                                ('servers', commaSeperatedIntegers, []),
                                ),
                                lambda x: re.match('(all)|(server_\d+)', x):(                                
                                ('idlechannel', int, 0),
                                ('state_before_registered', str, '/tmp/deaftoafk.sbreg_'),
                                ('state_before_unregistered', str, '/tmp/deaftoafk.sbunreg_')
                                )
                    }
    
    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        
    def getStatebefore(self, userid, serverid):
	try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all
	if (userid==-1): #User not registered
            filename=scfg.state_before_unregistered
	else: #User is registered
	    filename=scfg.state_before_registered

	try:
	    filehandle = open(filename+str(serverid), 'rb')
	    statebefore=pickle.load(filehandle)
	    filehandle.close()
	except:
	    statebefore={}
	return statebefore
  
    def writeStatebefore(self, userid, value, serverid):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % int(serverid))
        except AttributeError:
            scfg = self.cfg().all

	if (userid==-1): #User not registered
            filename=scfg.state_before_unregistered
        else: #User is registered
            filename=scfg.state_before_registered

	filehandle = open(filename+str(serverid), 'wb')
	pickle.dump(value, filehandle)
	filehandle.close()
     
    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")
        
        servers = self.cfg().deaftoafk.servers
        if not servers:
            servers = manager.SERVERS_ALL
            
        manager.subscribeServerCallbacks(self, servers)
    
    def disconnected(self): pass
    
    #
    #--- Server callback functions
    #
    
    def userTextMessage(self, server, user, message, current=None): pass
    def userConnected(self, server, state, context = None):
	channel_before_afk=self.getStatebefore(state.userid, server.id())
	#If user is registered and in afk list and not deaf: move back to previous channel and remove user from afk list.
	if (state.userid>=1) and (state.userid in channel_before_afk) and (state.deaf==False):
	    state.channel=channel_before_afk[state.userid]
	    server.setState(state)
	    del channel_before_afk[state.userid]
	    self.writeStatebefore(state.userid, channel_before_afk, server.id())

    def userDisconnected(self, server, state, context = None): 
	channel_before_afk=self.getStatebefore(state.userid, server.id())
	#Only remove from afk list if not registered
	if (state.session in channel_before_afk):
	    del channel_before_afk[state.session]
	    self.writeStatebefore(state.userid, channel_before_afk, server.id())
	    self.log().debug("Removed session %s (%s) from idle list because unregistered." % (state.session, state.name))
	    
    def userStateChanged(self, server, state, context = None):
        """Wer sich staub stellt, wird in AFK verschoben"""
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all
       
	channel_before_afk=self.getStatebefore(state.userid, server.id())

	if (state.userid==-1):
	    tosave=state.session
	else:
	    tosave=state.userid

        if (state.selfDeaf==True) and (tosave not in channel_before_afk):
  	    channel_before_afk[tosave]=state.channel
	
	    self.log().debug("Moved user %s from channelid %s into AFK." % (state.name, state.channel)) 

	    state.channel=scfg.idlechannel
	    server.setState(state)
  	    self.writeStatebefore(state.userid, channel_before_afk, server.id())

	if (state.selfDeaf==False) and (tosave in channel_before_afk):
	    self.log().debug("Moving user %s back into channelid %s." % (state.name, channel_before_afk[tosave]))
   	    state.channel = channel_before_afk[tosave]
	    server.setState(state)
            del channel_before_afk[tosave]

	    self.writeStatebefore(state.userid, channel_before_afk, server.id())

    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass     
