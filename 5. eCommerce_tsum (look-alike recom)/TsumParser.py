import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import time
import os


class TsumMenCosmeticParser:
    _header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:82.0) Gecko/20100101 Firefox/82.0',
    }

    def __init__(self, start_url):
        self.start_url = start_url
        self._url = urlparse(start_url)

    def _get_soup(self, url: str, params=None):
        response = requests.get(url, headers=self._header, params=params)
        return BeautifulSoup(response.text, 'lxml')

    def parse(self):
        page = 1
        while self.start_url:
            params = {'page': page}
            soup = self._get_soup(self.start_url, params)
            catalog = soup.find('div', attrs={'class': "product-list__products"})
            products = catalog.findChildren('a', attrs={'class': 'product__info'})

            if len(products) == 0:
                break
            else:
                page += 1

            for product in products:
                # to save connection and don't dedos the tsum server make some pause
                time.sleep(0.1)
                product_url = f'{self._url.scheme}://{self._url.hostname}{product.attrs.get("href")}'
                product_soup = self._get_soup(product_url)
                product_data = self.parse_product_page(product_soup, product_url)
                self.save_to_json_file(product_data)

    def parse_product_page(self, product_soup, url):

        # A bit hardcode to extract product description from json-structure
        product_soup_for_json = product_soup.find_all('script')[4].text
        product_soup_for_json = product_soup_for_json.replace('defineDeviceOrientation()', '"defineDeviceOrientation()"')
        product_soup_for_json = product_soup_for_json.replace('dataLayerOnServer = ', '')
        product_description = json.loads(product_soup_for_json)

        # json-structure description
        product_description_template = {
            'name': 'name',
            'id': 'id',
            'product_id': 'dimension42',
            'price': 'price',
            'brand': 'brand',
            'color': 'dimension65',
            'category': 'category',
            'category_id': 'categoryId',
            'availability': 'dimension68',
            'year': 'dimension59',
        }

        # information from html page
        product = {'product_url': url,
                   'img_url': None,
                   'description': None,
                   'country': None,
                   'design_country': None,
                   'weight': None,
                   'volume': None,
                   }

        # auxiliary dict for information extraction in cycle below
        names_dict = {'Страна дизайна': 'design_country',
                      'Страна производства': 'country',
                      'Вес': 'weight',
                      'Объем': 'volume',
                      }

        # picture could be empty
        try:
            product['img_url'] = product_soup.find('img', attrs={'class': 'slider-item__image'}).attrs.get('src')
        except Exception:
            product['img_url'] = None

        # description could be empty
        try:
            product['description'] = product_soup.find('div', attrs={'class': 'item__text'}).text
        except Exception:
            product['description'] = None

        # data parse from html product page
        for i in range(len(product_soup.find_all('li', attrs={'class': 'list__item'}))):
            rus_param = product_soup.find_all('li', attrs={'class': 'list__item'})[i].text.strip().split(': ')
            if rus_param[0] in names_dict.keys():
                product[names_dict[rus_param[0]]] = rus_param[1]

        # data parse from json-structure
        for key, value in product_description_template.items():
            try:
                product[key] = product_description[0]['ecommerce']['detail']['products'][0][value]
            except Exception:
                product[key] = None

        return product

    def save_to_json_file(self, product_data: dict):
        os.makedirs('products', exist_ok=True)
        with open(f'products/{product_data["id"]}.json', 'w', encoding='UTF-8') as json_file:
            json.dump(product_data, json_file, ensure_ascii=False)

        if product_data['img_url'] is not None:
            with open(f'products/{product_data["id"]}.jpg', 'wb') as picture:
                picture.write(requests.get(product_data['img_url']).content)


if __name__ == '__main__':
    url = 'https://www.tsum.ru/catalog/kosmetika-18393/'
    parser = TsumMenCosmeticParser(url)
    parser.parse()
