#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import shutil
import sys
from codecs import open
from collections import namedtuple
from tempfile import NamedTemporaryFile
from time import time
import configparser


from autojump_utils import create_dir
from autojump_utils import is_osx
from autojump_utils import is_python3
from autojump_utils import move_file
from autojump_utils import unico


if sys.version_info[0] == 3:
    ifilter = filter
    imap = map
else:
    from itertools import ifilter  # noqa
    from itertools import imap  # noqa


BACKUP_THRESHOLD = 24 * 60 * 60
Entry = namedtuple('Entry', ['name', 'command'])


def dictify(entries):
    """
    Converts a list of entries into a dictionary where
        key = name
        value = command
    """
    result = {}
    for entry in entries:
        result[entry.name] = entry.command
    return result


def entriefy(data):
    """Converts a dictionary into an iterator of entries."""
    convert = lambda tup: Entry(*tup)
    if is_python3():
        return map(convert, data.items())
    return imap(convert, data.iteritems())


def load(config):
    """Returns a dictonary (key=name, value=command) loaded from data file."""
    xdg_aj_home = os.path.join(
        os.path.expanduser('~'),
        '.local',
        'share',
        'autojump')

    if is_osx() and os.path.exists(xdg_aj_home):
        migrate_osx_xdg_data(config)

    if not os.path.exists(config['data_path']):
        return {}

    cfg_parser = configparser.ConfigParser()
    cfg_parser.read(config['data_path'])
 
    try:
        return dict(cfg_parser.items("ALIAS"))
    except (IOError):
        return load_backup(config)
 

def load_backup(config):
    if os.path.exists(config['backup_path']):
        move_file(config['backup_path'], config['data_path'])
        return load(config)
    return {}


def migrate_osx_xdg_data(config):
    """
    Older versions incorrectly used Linux XDG_DATA_HOME paths on OS X. This
    migrates autojump files from ~/.local/share/autojump to ~/Library/autojump
    """
    assert is_osx(), 'This function should only be run on OS X.'

    xdg_data_home = os.path.join(os.path.expanduser('~'), '.local', 'share')
    xdg_aj_home = os.path.join(xdg_data_home, 'autojump')
    data_path = os.path.join(xdg_aj_home, 'autojump.txt')
    backup_path = os.path.join(xdg_aj_home, 'autojump.txt.bak')

    if os.path.exists(data_path):
        move_file(data_path, config['data_path'])
    if os.path.exists(backup_path):
        move_file(backup_path, config['backup_path'])

    # cleanup
    shutil.rmtree(xdg_aj_home)
    if len(os.listdir(xdg_data_home)) == 0:
        shutil.rmtree(xdg_data_home)


def save(config, data):
    """Save data and create backup, creating a new data file if necessary."""
    create_dir(os.path.dirname(config['data_path']))

    # atomically save by writing to temporary file and moving to destination
    try:
        temp = NamedTemporaryFile(delete=False)
        # Windows cannot reuse the same open file name
        temp.close()

        cfg_parser = configparser.ConfigParser()
        cfg_parser['ALIAS'] = data

        with open(temp.name, 'w', encoding='utf-8', errors='replace') as f:
            cfg_parser.write(f)

    except IOError as ex:
        print('Error saving AliasBot data (disk full?)' % ex, file=sys.stderr)
        sys.exit(1)

    # move temp_file -> autojump.txt
    move_file(temp.name, config['data_path'])

    # create backup file if it doesn't exist or is older than BACKUP_THRESHOLD
    if not os.path.exists(config['backup_path']) or \
            (time() - os.path.getmtime(config['backup_path']) > BACKUP_THRESHOLD):  # noqa
        shutil.copy(config['data_path'], config['backup_path'])
