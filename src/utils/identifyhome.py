'''
    Onionr - Private P2P Communication

    Identify a data directory for Onionr
'''
'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
import os, platform

def identify_home():

    path = os.environ.get('ONIONR_HOME', None)

    if not os.getcwd().endswith('src') and path is not None:
        path = 'src/' + path

    if path is None:
        system = platform.system()
        if system == 'Linux':
            path = os.path.expanduser('~') + '/.local/share/onionr/'
        elif system == 'Windows':
            path = os.path.expanduser('~') + '\\AppData\\Local\\onionr\\'
        elif system == 'Darwin':
            path = os.path.expanduser('~' + '/Library/Application Support/onionr/')
        else:
            path = 'data/'
    else:
        path = os.path.abspath(path)
    if not path.endswith('/'):
        path += '/'

    return path