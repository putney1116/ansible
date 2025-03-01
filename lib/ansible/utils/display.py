# (c) 2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# FIXME: copied mostly from old code, needs py3 improvements
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import textwrap
import os
import random
import subprocess
import sys
import time
from multiprocessing import Lock

from ansible import constants as C
from ansible.errors import AnsibleError
from ansible.utils.color import stringc
from ansible.utils.unicode import to_bytes

class Display:

    def __init__(self, verbosity=0):

        self.verbosity = verbosity

        # list of all deprecation messages to prevent duplicate display
        self._deprecations = {}
        self._warns        = {}
        self._errors       = {}

        self.cowsay = None
        self.noncow = os.getenv("ANSIBLE_COW_SELECTION",None)
        self.set_cowsay_info()
        #self.debug_lock = Lock()

    def set_cowsay_info(self):

        if not C.ANSIBLE_NOCOWS:
            if os.path.exists("/usr/bin/cowsay"):
                self.cowsay = "/usr/bin/cowsay"
            elif os.path.exists("/usr/games/cowsay"):
                self.cowsay = "/usr/games/cowsay"
            elif os.path.exists("/usr/local/bin/cowsay"):
                # BSD path for cowsay
                self.cowsay = "/usr/local/bin/cowsay"
            elif os.path.exists("/opt/local/bin/cowsay"):
                # MacPorts path for cowsay
                self.cowsay = "/opt/local/bin/cowsay"
    
            if self.cowsay and self.noncow == 'random':
                cmd = subprocess.Popen([self.cowsay, "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (out, err) = cmd.communicate()
                cows = out.split()
                cows.append(False)
                self.noncow = random.choice(cows)
    
    def display(self, msg, color=None, stderr=False, screen_only=False, log_only=False):
        msg2 = msg
        if color:
            msg2 = stringc(msg, color)
        if not log_only:
            b_msg2 = to_bytes(msg2)
            if not stderr:
                print(b_msg2)
            else:
                print(b_msg2, file=sys.stderr)
        if C.DEFAULT_LOG_PATH != '':
            while msg.startswith("\n"):
                msg = msg.replace("\n","")
            b_msg = to_bytes(msg)
            # FIXME: logger stuff needs to be implemented
            #if not screen_only:
            #    if color == 'red':
            #        logger.error(b_msg)
            #    else:
            #        logger.info(b_msg)

    def vv(self, msg, host=None):
        return self.verbose(msg, host=host, caplevel=1)

    def vvv(self, msg, host=None):
        return self.verbose(msg, host=host, caplevel=2)

    def vvvv(self, msg, host=None):
        return self.verbose(msg, host=host, caplevel=3)

    def vvvvv(self, msg, host=None):
        return self.verbose(msg, host=host, caplevel=4)

    def vvvvvv(self, msg, host=None):
        return self.verbose(msg, host=host, caplevel=5)

    def debug(self, msg):
        if C.DEFAULT_DEBUG:
            # FIXME: enable when display is inherited to all
            #self.debug_lock.acquire()
            self.display("%6d %0.5f: %s" % (os.getpid(), time.time(), msg), color='dark gray')
            sys.stdout.flush()
            #self.debug_lock.release()

    def verbose(self, msg, host=None, caplevel=2):
        # FIXME: this needs to be implemented
        #msg = utils.sanitize_output(msg)
        if self.verbosity > caplevel:
            if host is None:
                self.display(msg, color='blue')
            else:
                self.display("<%s> %s" % (host, msg), color='blue', screen_only=True)

    def deprecated(self, msg, version=None, removed=False):
        ''' used to print out a deprecation message.'''

        if not removed and not C.DEPRECATION_WARNINGS:
            return

        if not removed:
            if version:
                new_msg = "\n[DEPRECATION WARNING]: %s. This feature will be removed in version %s." % (msg, version)
            else:
                new_msg = "\n[DEPRECATION WARNING]: %s. This feature will be removed in a future release." % (msg)
            new_msg = new_msg + " Deprecation warnings can be disabled by setting deprecation_warnings=False in ansible.cfg.\n\n"
        else:
            raise AnsibleError("[DEPRECATED]: %s.  Please update your playbooks." % msg)

        wrapped = textwrap.wrap(new_msg, 79)
        new_msg = "\n".join(wrapped) + "\n"

        if new_msg not in self._deprecations:
            self.display(new_msg, color='purple', stderr=True)
            self._deprecations[new_msg] = 1

    def warning(self, msg):
        new_msg = "\n[WARNING]: %s" % msg
        wrapped = textwrap.wrap(new_msg, 79)
        new_msg = "\n".join(wrapped) + "\n"
        if new_msg not in self._warns:
            self.display(new_msg, color='bright purple', stderr=True)
            self._warns[new_msg] = 1

    def system_warning(self, msg):
        if C.SYSTEM_WARNINGS:
            self.warning(msg)

    def banner(self, msg, color=None):
        '''
        Prints a header-looking line with stars taking up to 80 columns
        of width (3 columns, minimum)
        '''
        if self.cowsay:
            try:
                self.banner_cowsay(msg)
                return
            except OSError:
                # somebody cleverly deleted cowsay or something during the PB run.  heh.
                pass

        msg = msg.strip()
        star_len = (80 - len(msg))
        if star_len < 0:
            star_len = 3
        stars = "*" * star_len
        self.display("\n%s %s" % (msg, stars), color=color)

    def banner_cowsay(self, msg, color=None):
        if ": [" in msg:
            msg = msg.replace("[","")
            if msg.endswith("]"):
                msg = msg[:-1]
        runcmd = [self.cowsay,"-W", "60"]
        if self.noncow:
            runcmd.append('-f')
            runcmd.append(self.noncow)
        runcmd.append(msg)
        cmd = subprocess.Popen(runcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = cmd.communicate()
        self.display("%s\n" % out, color=color)

    def error(self, msg, wrap_text=True):
        if wrap_text:
            new_msg = "\n[ERROR]: %s" % msg
            wrapped = textwrap.wrap(new_msg, 79)
            new_msg = "\n".join(wrapped) + "\n"
        else:
            new_msg = msg
        if new_msg not in self._errors:
            self.display(new_msg, color='red', stderr=True)
            self._errors[new_msg] = 1

