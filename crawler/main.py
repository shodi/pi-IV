import requests
import grequests
from bs4 import BeautifulSoup

def building_society_type(x):
    fii_type, sector = map(str.strip, x.split(':'))
    return {'type': fii_type.upper(), 'sector': sector}

def number_format(str_number):
    return str_number.replace('.', '').replace(',', '.')

def format_document(doc):
    return doc.replace('.', '').replace('-', '').replace('/', '')

def build_admin_info(soup_admin):
    admin = {
        'name': soup_admin.find('span', class_='administrator-name').get_text(),
        'cnpj': format_document(
            soup_admin.find('span', class_='administrator-doc').get_text()),
    }
    # Para as informações no padrão key-value
    for admin_info in soup_admin\
        .find('div', class_='bottom-content')\
        .find_all('div', class_='item'):
        key = admin_info.find('span', class_='title').get_text().lower()
        if key == 'email':
            continue
        if key == 'telefone':
            key = 'phone'
        value = admin_info.find('span', class_='value').get_text()
        admin[key] = value
    return admin

def stock_detailed_info(soup):
    soup_detail = soup.find('div', id='informations--basic')
    stock_info = {
        'price': float(soup.find('div', id='informations--indexes')\
            .find_all('div', class_='item')[-1]\
            .find('span', class_='value')\
            .get_text().replace('R$', '').replace('.', '').replace(',', '.'))
    }
    formatters = {
        'Nome no Pregão': lambda x: {'reverse_auction_name': x},
        'Tipo do FII': building_society_type,
        'Tipo ANBIMA': lambda x: {'anbima_type': x},
        'Registro CVM': lambda x: {'CVM_created_at': x},
        'Número de Cotas': lambda x: {'quota_quantity': int(number_format(x))},
        'Número de Cotistas': lambda x: {'associates_quantity': int(number_format(x))},
        'CNPJ': lambda x: {'cnpj': format_document(x)}
    }
    for detail in soup_detail.find_all('div', class_='item'):
        try:
            key = detail.find('span', class_='title').get_text()
            value = detail.find('span', class_='value').get_text()
            stock_info = {**stock_info, **formatters[key](value)}
        except:
            pass
    return stock_info

def response_handler_factory(stock):
    def detail_response_handler(details_request):
        if details_request.status_code != 200:
            return
        soup = BeautifulSoup(details_request.text, 'html.parser')
        stock['admin'] = build_admin_info(soup.find('div', id='informations--admin'))
        stock = {**stock, **stock_detailed_info(soup)}
    return detail_response_handler

def main():
    building_society = requests.get('https://fiis.com.br/lista-de-fundos-imobiliarios/')
    soup = BeautifulSoup(building_society.text, 'html.parser')
    async_request_list = []
    for html_stock in soup.find_all('div', class_='item'):
        stock = {
            'ticker': html_stock.find('span', class_='ticker').get_text(),
            'name': html_stock.find('span', class_='name').get_text()
        }
        detail_url = html_stock.find('a').get('href')
        async_request_list.append(grequests.get(detail_url, hooks = {'response': response_handler_factory(stock)}))
    grequests.map(async_request_list)

if __name__ == '__main__':
    main()