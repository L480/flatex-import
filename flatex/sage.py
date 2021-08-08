import requests
import json
import colorama


def create_journal(access_token, payload):
    '''
    Creates journals through the Sage API.
    '''
    r = requests.post('https://api.accounting.sage.com/v3.1/journals',
                      data=json.dumps(payload), headers={'Authorization': 'Bearer {}'.format(access_token), 'Content-Type': 'application/json'})
    if r.status_code < 200 or r.status_code > 299:
        raise Exception(r.json())
    else:
        print("{}[✔] Created journal '{}'.{}".format(colorama.Fore.GREEN,
              payload['journal']['reference'], colorama.Style.RESET_ALL))


def get_ledger_account_ids(access_token):
    '''
    Gets all Sage ledger account IDs from the Sage API.
    '''
    data = {}
    total_items = 1
    page = 1
    while len(data) < total_items:
        r = requests.get('https://api.accounting.sage.com/v3.1/ledger_accounts?items_per_page=200&page={}'.format(
            page), headers={'Authorization': 'Bearer {}'.format(access_token), 'Content-Type': 'application/json'})
        if r.status_code < 200 or r.status_code > 299:
            raise Exception(r.json())
        else:
            for item in json.loads(r.text)['$items']:
                data[item['displayed_as']] = item['id']
            total_items = json.loads(r.text)['$total']
            page += 1
    return data
