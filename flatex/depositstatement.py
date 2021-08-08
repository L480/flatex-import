from . import sage
import pdfminer.high_level
import pdfminer.layout
import re
import datetime
import random
import pandas
import colorama
import tabulate


class DepositStatement:
    '''
    Processes flatex PDF deposit statements.
    '''

    def __init__(self):
        self.sell_orders_profit_overview = {
            'Referenz': [],
            'Datum': [],
            'Bank (Soll)': [],
            'Erträge (Haben)': [],
            'Anlagevermögen (Haben)': []
        }
        self.sell_orders_loss_overview = {
            'Referenz': [],
            'Datum': [],
            'Anlagevermögen (Haben)': [],
            'Verluste (Soll)': [],
            'Bank (Soll)': []
        }
        self.buy_orders_overview = {
            'Referenz': [],
            'Datum': [],
            'Bank (Haben)': [],
            'Anlagevermögen (Soll)': []
        }
        self.dividends_overview = {
            'Referenz': [],
            'Datum': [],
            'Dividende (Haben)': [],
            'Bank (Soll)': []
        }
        self.__sell_orders = {}
        self.__buy_orders = {}
        self.__dividends = {}
        self.__sage_sell_profit = {}
        self.__sage_sell_loss = {}
        self.__sage_buy = {}
        self.__sage_dividends = {}

    def parse_pdf(self, filepath):
        '''
        Parses the flatex deposit statement.

        Supported documents:
        - Sammelabrechnung (Wertpapierkauf/-verkauf)
        - Dividendengutschrift für ausländische Wertpapiere
        - Ertragsmitteilung - ausschüttender/teilthesaurierender Fonds
        '''
        EUR_REGEX = '(-?(?:\d+\.)?\d+,\d+ EUR)'
        ST_REGEX = '((?:\d+\.)?\d+,\d+ St\.)'
        ISIN_REGEX = '(?<=\().+?(?=\/)'
        DATE_REGEX = '[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9][0-9][0-9]'
        for page_layout in pdfminer.high_level.extract_pages(filepath):
            for element in page_layout:
                if isinstance(element, pdfminer.layout.LTTextBoxHorizontal):
                    text = str(element.get_text())
                    eur = re.findall(r'{}'.format(EUR_REGEX), text)
                    st = re.findall(r'{}'.format(ST_REGEX), text)

                    # Sammelabrechnung (Wertpapierkauf/-verkauf)
                    if 'Verkauf' in text or 'Kauf' in text:
                        isin = re.findall(r'{}'.format(ISIN_REGEX), text)[0]
                        schlusstag = re.findall(
                            r'{}'.format(DATE_REGEX), text)[0]
                        schlusstag = datetime.datetime.strptime(
                            schlusstag, '%d.%m.%Y')
                        schlusstag = '{}-{}-{}'.format(schlusstag.year,
                                                       schlusstag.month, schlusstag.day)
                        ausgefuehrt = float(st[1].replace(
                            ' St.', '').replace(',', '.'))
                        kurs = float(eur[0].replace(' EUR', '').replace(
                            '.', '').replace(',', '.'))
                        gewinn_verlust = float(eur[4].replace(
                            ' EUR', '').replace('.', '').replace(',', '.'))
                        provision = float(eur[2].replace(
                            ' EUR', '').replace('.', '').replace(',', '.'))
                        fremde_spesen = float(eur[3].replace(
                            ' EUR', '').replace('.', '').replace(',', '.'))
                        bemessungsgrundlage = float(eur[5].replace(
                            ' EUR', '').replace('.', '').replace(',', '.'))
                        endbetrag = float(eur[7].replace(
                            ' EUR', '').replace('.', '').replace(',', '.'))
                        if 'Verkauf' in text:
                            self.__sell_orders[isin if isin not in self.__sell_orders else '{}_{}'.format(isin, random.randint(3000, 9999))] = {
                                'ausgefuehrt': ausgefuehrt,
                                'kurs': kurs,
                                'gewinn_verlust': gewinn_verlust,
                                'schlusstag': schlusstag,
                                'provision': provision,
                                'fremde_spesen': fremde_spesen,
                                'bemessungsgrundlage': bemessungsgrundlage,
                                'endbetrag': endbetrag
                            }
                        else:
                            self.__buy_orders[isin if isin not in self.__buy_orders else '{}_{}'.format(isin, random.randint(3000, 9999))] = {
                                'ausgefuehrt': ausgefuehrt,
                                'kurs': kurs,
                                'gewinn_verlust': gewinn_verlust,
                                'schlusstag': schlusstag,
                                'provision': provision,
                                'fremde_spesen': fremde_spesen,
                                'bemessungsgrundlage': bemessungsgrundlage,
                                'endbetrag': endbetrag
                            }

                    # Dividendengutschrift für ausländische Wertpapiere
                    # Ertragsmitteilung - ausschüttender/teilthesaurierender Fonds
                    if 'Extag' in text:
                        isin = re.findall(r'{}'.format(ISIN_REGEX), text)[0]
                        extag = re.findall(r'{}'.format(DATE_REGEX), text)[0]
                        extag = datetime.datetime.strptime(extag, '%d.%m.%Y')
                        extag = '{}-{}-{}'.format(extag.year,
                                                  extag.month, extag.day)
                    if 'Endbetrag' in text and 'auf' not in text:
                        if not eur:
                            continue
                        endbetrag = float(eur[0].replace(
                            ' EUR', '').replace('.', '').replace(',', '.'))
                        self.__dividends[isin if isin not in self.__dividends else '{}_{}'.format(isin, random.randint(3000, 9999))] = {
                            'extag': extag,
                            'endbetrag': endbetrag
                        }
        self.__process_orders()

    def __process_orders(self):
        '''
        Processes data of the flatex deposit statement.
        '''
        for stock, data in self.__sell_orders.items():
            # Sell orders with profit
            if data['gewinn_verlust'] >= 0:
                self.__sage_sell_profit[stock] = {
                    'referenz': 'Verkauf {}x {}'.format(int(data['ausgefuehrt']), stock),
                    'datum': data['schlusstag'],
                    'bank_soll': round(data['endbetrag'], 2),
                    'ertraege_haben': round(data['bemessungsgrundlage'], 2),
                    'anlagevermoegen_haben': round(data['endbetrag'] - data['bemessungsgrundlage'], 2)
                }
                self.sell_orders_profit_overview['Referenz'].append(
                    self.__sage_sell_profit[stock]['referenz'])
                self.sell_orders_profit_overview['Datum'].append(
                    self.__sage_sell_profit[stock]['datum'])
                self.sell_orders_profit_overview['Bank (Soll)'].append(
                    self.__sage_sell_profit[stock]['bank_soll'])
                self.sell_orders_profit_overview['Erträge (Haben)'].append(
                    self.__sage_sell_profit[stock]['ertraege_haben'])
                self.sell_orders_profit_overview['Anlagevermögen (Haben)'].append(
                    self.__sage_sell_profit[stock]['anlagevermoegen_haben'])
            # Sell orders with loss
            else:
                data['gewinn_verlust'] = abs(data['gewinn_verlust'])
                data['bemessungsgrundlage'] = abs(data['bemessungsgrundlage'])
                self.__sage_sell_loss[stock] = {
                    'referenz': 'Verkauf {}x {}'.format(int(data['ausgefuehrt']), stock),
                    'datum': data['schlusstag'],
                    'anlagevermoegen_haben': round(data['endbetrag'] + data['bemessungsgrundlage'], 2),
                    'verluste_soll': round(data['bemessungsgrundlage'], 2),
                    'bank_soll': round(data['endbetrag'], 2)
                }
                self.sell_orders_loss_overview['Referenz'].append(
                    self.__sage_sell_loss[stock]['referenz'])
                self.sell_orders_loss_overview['Datum'].append(
                    self.__sage_sell_loss[stock]['datum'])
                self.sell_orders_loss_overview['Anlagevermögen (Haben)'].append(
                    self.__sage_sell_loss[stock]['anlagevermoegen_haben'])
                self.sell_orders_loss_overview['Verluste (Soll)'].append(
                    self.__sage_sell_loss[stock]['verluste_soll'])
                self.sell_orders_loss_overview['Bank (Soll)'].append(
                    self.__sage_sell_loss[stock]['bank_soll'])

        # Buy orders
        for stock, data in self.__buy_orders.items():
            data['endbetrag'] = abs(data['endbetrag'])
            self.__sage_buy[stock] = {
                'referenz': 'Kauf {}x {}'.format(int(data['ausgefuehrt']), stock),
                'datum': data['schlusstag'],
                'bank_haben': round(data['endbetrag'], 2),
                'anlagevermoegen_soll': round(data['endbetrag'], 2)
            }
            self.buy_orders_overview['Referenz'].append(
                self.__sage_buy[stock]['referenz'])
            self.buy_orders_overview['Datum'].append(
                self.__sage_buy[stock]['datum'])
            self.buy_orders_overview['Bank (Haben)'].append(
                self.__sage_buy[stock]['bank_haben'])
            self.buy_orders_overview['Anlagevermögen (Soll)'].append(
                self.__sage_buy[stock]['anlagevermoegen_soll'])

        # Dividends
        for stock, data in self.__dividends.items():
            self.__sage_dividends[stock] = {
                'referenz': 'Dividende {}'.format(stock),
                'datum': data['extag'],
                'dividende_haben': round(data['endbetrag'], 2),
                'bank_soll': round(data['endbetrag'], 2)
            }
            self.dividends_overview['Referenz'].append(
                self.__sage_dividends[stock]['referenz'])
            self.dividends_overview['Datum'].append(
                self.__sage_dividends[stock]['datum'])
            self.dividends_overview['Dividende (Haben)'].append(
                self.__sage_dividends[stock]['dividende_haben'])
            self.dividends_overview['Bank (Soll)'].append(
                self.__sage_dividends[stock]['bank_soll'])

        self.sell_orders_profit_overview = pandas.DataFrame(self.sell_orders_profit_overview, columns=[
                                                            header for header in self.sell_orders_profit_overview])
        self.sell_orders_loss_overview = pandas.DataFrame(self.sell_orders_loss_overview, columns=[
                                                          header for header in self.sell_orders_loss_overview])
        self.buy_orders_overview = pandas.DataFrame(self.buy_orders_overview, columns=[
                                                    header for header in self.buy_orders_overview])
        self.dividends_overview = pandas.DataFrame(self.dividends_overview, columns=[
                                                   header for header in self.dividends_overview])

    def show_overview(self):
        '''
        Prints overview of all transactions in flatex deposit statement to console.
        '''
        TABLEFMT = 'fancy_grid'
        if not self.sell_orders_profit_overview.empty:
            print('{}Sales with profit:{}'.format(
                colorama.Fore.GREEN, colorama.Style.RESET_ALL))
            print(tabulate.tabulate(self.sell_orders_profit_overview, headers=[
                  header for header in self.sell_orders_profit_overview], tablefmt=TABLEFMT))

        if not self.sell_orders_loss_overview.empty:
            print('{}Sales with loss:{}'.format(
                colorama.Fore.RED, colorama.Style.RESET_ALL))
            print(tabulate.tabulate(self.sell_orders_loss_overview, headers=[
                  header for header in self.sell_orders_loss_overview], tablefmt=TABLEFMT))

        if not self.buy_orders_overview.empty:
            print('{}Purchases:{}'.format(
                colorama.Fore.BLUE, colorama.Style.RESET_ALL))
            print(tabulate.tabulate(self.buy_orders_overview, headers=[
                  header for header in self.buy_orders_overview], tablefmt=TABLEFMT))

        if not self.dividends_overview.empty:
            print('{}Dividends:{}'.format(
                colorama.Fore.MAGENTA, colorama.Style.RESET_ALL))
            print(tabulate.tabulate(self.dividends_overview, headers=[
                  header for header in self.dividends_overview], tablefmt=TABLEFMT))

    def create_sage_journals(self, access_token, skr04_1800_account_name, skr04_0900_account_name, skr04_4900_account_name, skr04_6900_account_name, skr04_7020_account_name):
        '''
        Creates journals in Sage Business Cloud Accounting for all transactions in flatex deposit statement.
        '''
        ledger_account_ids = sage.get_ledger_account_ids(access_token)
        # Sell orders with profit
        for stock, data in self.__sage_sell_profit.items():
            payload = {
                'journal': {
                    'date': data['datum'],
                    'reference': data['referenz'],
                    'total': data['bank_soll'],
                    'journal_lines': [
                        {
                            'credit': 0.0,
                            'debit': data['bank_soll'],
                            'ledger_account_id': ledger_account_ids[skr04_1800_account_name]
                        },
                        {
                            'credit': data['ertraege_haben'],
                            'debit': 0.0,
                            'ledger_account_id': ledger_account_ids[skr04_4900_account_name]
                        },
                        {
                            'credit': data['anlagevermoegen_haben'],
                            'debit': 0.0,
                            'ledger_account_id': ledger_account_ids[skr04_0900_account_name]
                        }
                    ]
                }
            }
            sage.create_journal(access_token, payload)

        # Sell orders with loss
        for stock, data in self.__sage_sell_loss.items():
            payload = {
                'journal': {
                    'date': data['datum'],
                    'reference': data['referenz'],
                    'total': data['bank_soll'],
                    'journal_lines': [
                        {
                            'credit': data['anlagevermoegen_haben'],
                            'debit': 0.0,
                            'ledger_account_id': ledger_account_ids[skr04_0900_account_name]
                        },
                        {
                            'credit': 0.0,
                            'debit': data['verluste_soll'],
                            'ledger_account_id': ledger_account_ids[skr04_6900_account_name]
                        },
                        {
                            'credit': 0.0,
                            'debit': data['bank_soll'],
                            'ledger_account_id': ledger_account_ids[skr04_1800_account_name]
                        }
                    ]
                }
            }
            sage.create_journal(access_token, payload)

        # Buy orders
        for stock, data in self.__sage_buy.items():
            payload = {
                'journal': {
                    'date': data['datum'],
                    'reference': data['referenz'],
                    'total': data['bank_haben'],
                    'journal_lines': [
                        {
                            'credit': data['bank_haben'],
                            'debit': 0.0,
                            'ledger_account_id': ledger_account_ids[skr04_1800_account_name]
                        },
                        {
                            'credit': 0.0,
                            'debit': data['anlagevermoegen_soll'],
                            'ledger_account_id': ledger_account_ids[skr04_0900_account_name]
                        }
                    ]
                }
            }
            sage.create_journal(access_token, payload)

        # Dividends
        for stock, data in self.__sage_dividends.items():
            payload = {
                'journal': {
                    'date': data['datum'],
                    'reference': data['referenz'],
                    'total': data['bank_soll'],
                    'journal_lines': [
                        {
                            'credit': data['dividende_haben'],
                            'debit': 0.0,
                            'ledger_account_id': ledger_account_ids[skr04_7020_account_name]
                        },
                        {
                            'credit': 0.0,
                            'debit': data['bank_soll'],
                            'ledger_account_id': ledger_account_ids[skr04_1800_account_name]
                        }
                    ]
                }
            }
            sage.create_journal(access_token, payload)
