import flatex
import http.server
import urllib
import requests
import webbrowser
import re
import colorama
import art
import time
import json


with open('config.json', 'r') as f:
    config = json.loads(f.read())


class HTTPServerHandler(http.server.BaseHTTPRequestHandler):
    '''
    Grabs authorization code from OAuth 2 callback URI
    '''

    def __init__(self, request, address, server, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        super().__init__(request, address, server)

    def do_GET(self):
        TOKEN_ENDPOINT = 'https://oauth.accounting.sage.com/token'
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        if 'code' in self.path:
            authorization_code = re.findall(
                r'(?<==)(.*)(?=&)', urllib.parse.unquote(self.path))[0]
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            r = requests.post(TOKEN_ENDPOINT, data=data)
            self.server.access_token = r.json()['access_token']
            self.wfile.write(bytes(
                'You are logged in. You may now close this window and return to the flatex-import script.', 'utf-8'))


def get_access_token():
    '''
    Exchanges authorization code for access token
    '''
    AUTHORIZATION_ENDPOINT = 'https://www.sageone.com/oauth2/auth/central?filter=apiv3.1&response_type=code&client_id={}&redirect_uri={}&scope=full_access'.format(
        config['client_id'], config['redirect_uri'])
    webbrowser.open_new(AUTHORIZATION_ENDPOINT)
    httpServer = http.server.HTTPServer(('localhost', 8080), lambda request, address, server: HTTPServerHandler(
        request, address, server, config['client_id'], config['client_secret'], config['redirect_uri']))
    httpServer.handle_request()
    return httpServer.access_token


def flatex_import(access_token):
    '''
    Imports flatex deposit statement to Sage Business Cloud Accounting
    '''
    print('{}[*] Please enter the filepath of the flatex deposit statement you want to import:{}'.format(
        colorama.Fore.YELLOW, colorama.Style.RESET_ALL))
    filepath = input()
    statement = flatex.DepositStatement()
    statement.parse_pdf(filepath)
    print('{}[*] The following transactions will be imported:{}'.format(
        colorama.Fore.YELLOW, colorama.Style.RESET_ALL))
    statement.show_overview()
    print('{}[*] Continue? [y/N]:{}'.format(colorama.Fore.YELLOW,
          colorama.Style.RESET_ALL))
    choice = input().lower()
    if choice != "y":
        exit()
    statement.create_sage_journals(access_token, config['skr04_account_names']['1820'], config['skr04_account_names']['0900'],
                                   config['skr04_account_names']['4900'], config['skr04_account_names']['6900'], config['skr04_account_names']['7020'])
    exit()


if __name__ == '__main__':
    print(art.text2art("flatex-import"))
    print('{}[*] Please continue the login in the web browser.{}'.format(
        colorama.Fore.YELLOW, colorama.Style.RESET_ALL))
    time.sleep(2)
    access_token = get_access_token()
    flatex_import(access_token)
