'''
    Onionr - Private P2P Communication

    Process incoming requests to the client api server to validate they are legitimate
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
import hmac
from flask import Blueprint, request, abort
from onionrservices import httpheaders
# Be extremely mindful of this. These are endpoints available without a password
whitelist_endpoints = ('siteapi.site', 'www', 'staticfiles.onionrhome', 'staticfiles.homedata', 
'staticfiles.board', 'staticfiles.profiles', 
'staticfiles.profilesindex', 
'staticfiles.boardContent', 'staticfiles.sharedContent', 
'staticfiles.mail', 'staticfiles.mailindex', 'staticfiles.friends', 'staticfiles.friendsindex',
'staticfiles.clandestine', 'staticfiles.clandestineIndex')

class ClientAPISecurity:
    def __init__(self, client_api):
        client_api_security_bp = Blueprint('clientapisecurity', __name__)
        self.client_api_security_bp = client_api_security_bp
        self.client_api = client_api

        @client_api_security_bp.before_app_request
        def validate_request():
            '''Validate request has set password and is the correct hostname'''
            # For the purpose of preventing DNS rebinding attacks
            if request.host != '%s:%s' % (client_api.host, client_api.bindPort):
                abort(403)
            if request.endpoint in whitelist_endpoints:
                return
            try:
                if not hmac.compare_digest(request.headers['token'], client_api.clientToken):
                    if not hmac.compare_digest(request.form['token'], client_api.clientToken):
                        abort(403)
            except KeyError:
                if not hmac.compare_digest(request.form['token'], client_api.clientToken):
                    abort(403)

        @client_api_security_bp.after_app_request
        def after_req(resp):
            # Security headers
            resp = httpheaders.set_default_onionr_http_headers(resp)
            if request.endpoint == 'site':
                resp.headers['Content-Security-Policy'] = "default-src 'none'; style-src data: 'unsafe-inline'; img-src data:"
            else:
                resp.headers['Content-Security-Policy'] = "default-src 'none'; script-src 'self'; object-src 'none'; style-src 'self'; img-src 'self'; media-src 'none'; frame-src 'none'; font-src 'none'; connect-src 'self'"
            return resp